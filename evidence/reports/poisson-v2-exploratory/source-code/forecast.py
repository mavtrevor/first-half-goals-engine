"""The operational forecast boundary stays closed during offline research."""
import json
from datetime import timedelta
from data import latest_matches, utc


def record_forecast(db, match_id, now):
    now = utc(now)
    fixture = next((r for r in latest_matches(db, now) if r['match_id'] == match_id), None)
    reason = 'validation_gates_pending'
    if not fixture or fixture['quality'] == 'quarantined':
        reason = 'unknown_fixture'
    elif fixture.get('finished') or utc(fixture['kickoff']) <= now+timedelta(minutes=5):
        reason = 'not_eligible_pre_match'
    elif not fixture['kickoff_confirmed']:
        reason = 'fixture_time_unconfirmed'
    saved = {'match_id': match_id, 'generated_at': now.isoformat(), 'state': 'abstained',
             'raw_p': None, 'calibrated_p': None, 'reason': reason,
             'fixture_hash': fixture.get('snapshot_hash') if fixture else None,
             'scope': 'offline_research_no_operational_model'}
    with db:
        saved['id'] = db.execute('INSERT INTO forecasts(match_id,generated_at,record) VALUES(?,?,?)',
                                 (match_id, now.isoformat(), json.dumps(saved))).lastrowid
    return saved
