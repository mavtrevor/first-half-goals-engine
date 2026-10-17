"""Human-entered observations only. This module never contacts an operator."""
import hashlib
import json
import math
import re
from datetime import timedelta

from data import ROOT, positive_id, utc

MARKET = {'country': 'NG', 'period': '1H', 'statistic': 'goals', 'scope': 'match_total',
          'line': 0.5, 'side': 'over'}
LEG_KEYS = ('match_id', 'country', 'period', 'statistic', 'scope', 'line', 'side')


def record_observation(db, observation, now):
    now = utc(now)
    if any(observation.get(k) != v for k, v in MARKET.items()):
        raise ValueError('Only SportyBet Nigeria first-half match-total Over 0.5 goals is admitted')
    odds = observation.get('odds')
    if type(odds) not in (int, float) or not math.isfinite(odds) or odds <= 1:
        raise ValueError('Decimal odds must be finite and greater than one')
    if observation.get('event_type') != 'real_senior_football' or observation.get('market_status') not in ('active', 'suspended', 'unavailable'):
        raise ValueError('A real pre-match senior football event and valid status are required')
    observed = utc(observation['observed_at'])
    if observed > now:
        raise ValueError('Observation time cannot be in the future')
    for key in ('home', 'away', 'event_id', 'fixture_hash', 'evidence_note'):
        value = observation.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 1000:
            raise ValueError(f'{key} is required and must be bounded text')
    if observation.get('human_identity_confirmed') is not True:
        raise ValueError('A human must confirm exact fixture identity')
    saved = {k: observation[k] for k in (*MARKET, 'home', 'away', 'event_id', 'fixture_hash',
                                        'market_status', 'event_type', 'evidence_note', 'human_identity_confirmed')}
    saved.update(match_id=positive_id(observation.get('match_id')), operator='SportyBet',
                 odds=float(odds), observed_at=observed.isoformat(), entered_at=now.isoformat(),
                 expires_at=(observed+timedelta(minutes=5)).isoformat(),
                 kickoff=utc(observation['kickoff']).isoformat(), verifier_type='human',
                 rules_verified=False, rules_version=None, evidence_type='human_note',
                 readiness='blocked_pending_release_gates')
    with db:
        saved['id'] = db.execute('INSERT INTO observations(match_id,entered_at,record) VALUES(?,?,?)',
                                 (saved['match_id'], now.isoformat(), json.dumps(saved, allow_nan=False))).lastrowid
    return saved


def observation_state(observation, fixture, now):
    now = utc(now)
    if (observation['match_id'] != fixture['match_id'] or observation['fixture_hash'] != fixture['snapshot_hash']
        or observation['home'] != fixture['home'] or observation['away'] != fixture['away']
        or utc(observation['kickoff']) != utc(fixture['kickoff'])):
        return 'mismatch'
    if now >= utc(observation['expires_at']) or now < utc(observation['observed_at']):
        return 'stale'
    if fixture.get('finished') or now >= utc(fixture['kickoff'])-timedelta(minutes=5):
        return 'pre_match_locked'
    if observation['market_status'] != 'active':
        return 'unavailable'
    policy = json.loads((ROOT/'config/source-policy.json').read_text(encoding='utf-8'))
    if not policy['nigeria_rules_verified'] or not observation.get('rules_verified'):
        return 'rules_unverified'
    if not fixture.get('kickoff_confirmed') or not policy['current_fixture_checks_passed']:
        return 'fixture_unverified'
    return 'human_observed'


def record_booking(db, booking, now):
    now = utc(now)
    code = booking.get('code', '')
    if booking.get('country') != 'NG' or not isinstance(code, str) or not re.fullmatch(r'[A-Za-z0-9]{4,32}', code):
        raise ValueError('Enter a Nigeria code copied from the official UI')
    manifest = booking.get('selection_manifest')
    if not isinstance(manifest, list) or not 1 <= len(manifest) <= 50:
        raise ValueError('A selection manifest with 1 to 50 legs is required')
    for leg in manifest:
        positive_id(leg.get('match_id'))
        if set(leg) != set(LEG_KEYS) or any(leg.get(k) != v for k, v in MARKET.items()):
            raise ValueError('Booking manifest must identify the exact admitted market')
    if len({leg['match_id'] for leg in manifest}) != len(manifest):
        raise ValueError('Duplicate match selections are not admitted')
    manifest = json.loads(json.dumps(manifest, allow_nan=False))
    state, reloaded = 'pasted_unverified', None
    if booking.get('human_reloaded') is True:
        reloaded = utc(booking['reloaded_at'])
        if reloaded > now:
            raise ValueError('Reload time cannot be in the future')
        state = 'human_reload_matched' if booking.get('reloaded_manifest') == manifest else 'mismatch'
    expiry = booking.get('expiry_if_displayed')
    if expiry is not None:
        expiry = utc(expiry)
        if expiry <= now:
            state = 'expired_or_unloadable'
    saved = {'code': code, 'country': 'NG', 'origin': 'manual_official_UI',
             'entered_at': now.isoformat(), 'reloaded_at': reloaded.isoformat() if reloaded else None,
             'expiry_if_displayed': expiry.isoformat() if expiry else None,
             'selection_manifest': manifest,
             'manifest_hash': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
             'code_state': state, 'current_odds_verified': False,
             'readiness': 'blocked_pending_release_gates'}
    with db:
        saved['id'] = db.execute('INSERT INTO bookings(entered_at,record) VALUES(?,?)',
                                 (now.isoformat(), json.dumps(saved))).lastrowid
    return saved
