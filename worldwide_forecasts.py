"""Immutable private shadow forecasts; no public probability release yet."""
import hashlib
import json
from datetime import timedelta

from data import utc
from poisson_model import predict_counts


def record_shadow(db, event, pair, inputs, now):
    now=utc(now);kickoff=utc(event['kickoff'])
    old=db.execute('SELECT record FROM shadows WHERE event_id=? AND kickoff=?',
                    (event['event_id'],event['kickoff'])).fetchone()
    if old:return json.loads(old[0])
    record=dict(event_id=event['event_id'],competition_id=event['competition_id'],kickoff=event['kickoff'],
        generated_at=now.isoformat(),state='abstained',raw_p=None,calibrated_p=None,
        fixture_hash=event.get('snapshot_hash'),model_id=pair.get('model_id') if pair else None,
        input_hashes=inputs.get('input_hashes',[]),operational_release=False)
    lead=(kickoff-now).total_seconds()/60
    if not 55<=lead<=65:
        return dict(record,reason='outside_forecast_window')
    reason='model_or_inputs_unavailable'
    if event.get('status') not in ('SCHEDULED','TIMED') or event.get('classification')!='senior_real':
        reason='fixture_ineligible'
    elif pair and inputs:
        try:
            if (inputs['event_id']!=event['event_id'] or inputs['kickoff']!=event['kickoff']
                or inputs['fixture_hash']!=event['snapshot_hash'] or utc(inputs['cutoff'])!=now
                or utc(inputs['maximum_observed_at'])>now or utc(event['observed_at'])>now
                or now-utc(event['observed_at'])>timedelta(minutes=10)
                or inputs['source_home_id']!=event['home_id'] or inputs['source_away_id']!=event['away_id']
                or inputs['home_history']<10 or inputs['away_history']<10 or not inputs['input_hashes']):
                raise ValueError('Ineligible observed forecast inputs')
            estimate=predict_counts(pair,inputs)
            if estimate['unseen_teams']:raise ValueError('Unseen team')
            if estimate['model_id']!=pair['model_id']:raise ValueError('Model lineage mismatch')
            record.update(state='shadow',raw_p=estimate['raw_p'],calibrated_p=estimate['calibrated_p'])
            reason='private_shadow_validation_pending'
        except (ValueError,KeyError,TypeError,ArithmeticError):
            reason='invalid_or_unavailable_observed_inputs'
    record['reason']=reason
    with db:
        db.execute('INSERT OR IGNORE INTO shadows VALUES(?,?,?,?)',
            (event['event_id'],event['kickoff'],now.isoformat(),json.dumps(record,allow_nan=False)))
    return json.loads(db.execute('SELECT record FROM shadows WHERE event_id=? AND kickoff=?',
                (event['event_id'],event['kickoff'])).fetchone()[0])


def settle_shadow(db, event, result, now):
    now=utc(now)
    if (event['event_id']!=result['event_id'] or event['kickoff']!=result['kickoff']
        or event['competition_id']!=result['competition_id'] or result.get('status')!='FINISHED'
        or utc(result['observed_at'])>now or utc(result['kickoff'])>=now):
        raise ValueError('Invalid shadow settlement identity/time')
    values=[result.get(k) for k in ('ht_home','ht_away','ft_home','ft_away')]
    if (any(type(v) is not int or v<0 for v in values) or values[0]>values[2] or values[1]>values[3]
        or type(result.get('target')) is not int or result['target']!=int(values[0]+values[1]>0)):
        raise ValueError('Explicit valid HT result required')
    if not db.execute('SELECT 1 FROM shadows WHERE event_id=? AND kickoff=?',(event['event_id'],event['kickoff'])).fetchone():
        raise ValueError('No original shadow record')
    payload=json.dumps(result,sort_keys=True,allow_nan=False)
    digest=hashlib.sha256(payload.encode()).hexdigest()
    with db:
        db.execute('INSERT OR IGNORE INTO settlements VALUES(?,?,?,?,?)',
            (event['event_id'],event['kickoff'],now.isoformat(),digest,payload))
    return dict(event_id=event['event_id'],state='observed_settlement',digest=digest)


def public_estimate(shadow, evidence, now):
    # No league has a preregistered prospective release report in this build.
    return dict(probability=None,probability_state='unavailable',
                probability_reason='prospective_confirmatory_protocol_and_evidence_pending',
                model_id=shadow.get('model_id'),generated_at=shadow.get('generated_at'))
