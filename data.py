"""Offline, append-only Bundesliga snapshots. No network client is enabled."""
import copy
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def utc(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('A timezone-aware timestamp is required')
    return result.astimezone(timezone.utc)


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout = 5000')
    db.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
    return db


def positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError('A positive integer identity is required')
    return value


def score(result):
    values = [result.get('pointsTeam1'), result.get('pointsTeam2')]
    if any(type(v) is not int or v < 0 for v in values):
        raise ValueError('Scores must be nonnegative integers')
    return values


def normalize_match(raw, observed_at):
    now = utc(observed_at)
    if raw.get('leagueShortcut') != 'bl1':
        raise ValueError('Only Bundesliga bl1 is admitted')
    mid = positive_id(raw.get('matchID'))
    season = positive_id(raw.get('leagueSeason'))
    if not 1990 <= season <= now.year:
        raise ValueError('Invalid season')
    kickoff = utc(raw['matchDateTimeUTC'])
    home, away = raw['team1'], raw['team2']
    hid, aid = positive_id(home.get('teamId')), positive_id(away.get('teamId'))
    if hid == aid:
        raise ValueError('Home and away identities must differ')
    if any(not isinstance(t.get('teamName'), str) or not 1 <= len(t['teamName'].strip()) <= 150 for t in (home, away)):
        raise ValueError('Missing or invalid team name')
    finished = raw.get('matchIsFinished')
    if type(finished) is not bool:
        raise ValueError('Completion flag must be boolean')
    if finished and kickoff >= now:
        raise ValueError('A future fixture cannot be finished')
    slots = {}
    for result in raw.get('matchResults', []):
        kind = result.get('resultTypeKind')
        if kind not in ('HalfTime', 'After90Minutes') or kind in slots:
            raise ValueError('Unknown or duplicate result semantics')
        slots[kind] = score(result)
    ht, ft = slots.get('HalfTime'), slots.get('After90Minutes')
    if ht is not None and ft is not None and any(h > f for h, f in zip(ht, ft)):
        raise ValueError('Half-time score exceeds regular-time score')
    usable = finished and ht is not None and ft is not None
    return {'match_id': mid, 'season': season, 'competition': 'bl1',
            'home_id': hid, 'away_id': aid, 'home': home['teamName'], 'away': away['teamName'],
            'kickoff': kickoff.isoformat(), 'observed_at': now.isoformat(),
            'finished': finished, 'kickoff_confirmed': False,
            'ht_home': ht[0] if usable else None, 'ht_away': ht[1] if usable else None,
            'ft_home': ft[0] if finished and ft else None, 'ft_away': ft[1] if finished and ft else None,
            'target': int(sum(ht) > 0) if usable else None,
            'quality': 'structurally_valid' if usable else ('missing_score' if finished else 'fixture_only')}


def resolve_result(raw_match, override, snapshot_hash):
    result = copy.deepcopy(raw_match)
    if override is None:
        return result
    if override.get('source_match_id') != raw_match.get('matchID'):
        raise ValueError('Correction identity mismatch')
    if not snapshot_hash or override.get('original_snapshot_sha256', '').lower() != snapshot_hash.lower():
        raise ValueError('Correction snapshot mismatch; review the upstream revision')
    slots = [r for r in result.get('matchResults', []) if r.get('resultTypeKind') == 'HalfTime']
    if len(slots) != 1 or '-'.join(map(str, score(slots[0]))) != override.get('original_ht'):
        raise ValueError('Correction original score mismatch')
    corrected = override.get('corrected_ht', '').split('-')
    if len(corrected) != 2 or any(not v.isdecimal() for v in corrected) or not override.get('authority_url', '').startswith('https://'):
        raise ValueError('Invalid correction evidence')
    slots[0]['pointsTeam1'], slots[0]['pointsTeam2'] = map(int, corrected)
    return result


def ingest_snapshot(db, payload, metadata, corrections=None):
    if metadata.get('source') != 'OpenLigaDB' or len(payload) > 20_000_000:
        raise ValueError('Unsupported source or oversized snapshot')
    digest = hashlib.sha256(payload).hexdigest()
    previous = db.execute('SELECT id FROM snapshots WHERE digest=?', (digest,)).fetchone()
    if previous:
        stored = [json.loads(r[0]) for r in db.execute(
            'SELECT record FROM matches WHERE snapshot_id=?', (previous[0],))]
        applied = {r['match_id']: r['correction'] for r in stored if 'correction' in r}
        requested = {c['source_match_id']: c for c in (corrections or [])}
        if applied != requested or len(requested) != len(corrections or []):
            raise ValueError('Changed correction provenance requires a separately reviewed normalization version')
        return previous[0]
    observed = utc(metadata['observed_at']).isoformat()
    records = json.loads(payload.decode('utf-8-sig'))
    if not isinstance(records, list) or not records:
        raise ValueError('Expected a non-empty season snapshot')
    ids = [positive_id(r.get('matchID')) for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate match identities in snapshot')
    corrections = {c['source_match_id']: c for c in (corrections or [])}
    normalized = []
    for raw in records:
        if raw.get('leagueSeason') != metadata['season']:
            raise ValueError('Snapshot season mismatch')
        try:
            effective = resolve_result(raw, corrections.get(raw['matchID']), digest)
            row = normalize_match(effective, observed)
            if raw['matchID'] in corrections:
                row['correction'] = corrections[raw['matchID']]
        except (ValueError, KeyError, TypeError) as exc:
            row = {'match_id': raw['matchID'], 'season': metadata['season'], 'quality': 'quarantined',
                   'target': None, 'observed_at': observed, 'reason': str(exc)}
        row['snapshot_hash'] = digest
        normalized.append(row)
    with db:
        sid = db.execute('INSERT INTO snapshots(source,season,digest,observed_at,metadata,payload) VALUES(?,?,?,?,?,?)',
                         ('OpenLigaDB', metadata['season'], digest, observed, json.dumps(metadata), payload)).lastrowid
        db.executemany('INSERT INTO matches(snapshot_id,match_id,season,observed_at,record) VALUES(?,?,?,?,?)',
                       [(sid, r['match_id'], r['season'], observed, json.dumps(r)) for r in normalized])
    return sid


def latest_matches(db, as_of=None):
    limit = utc(as_of).isoformat() if as_of else '9999'
    rows = db.execute('''SELECT record FROM (
      SELECT record, ROW_NUMBER() OVER(PARTITION BY match_id ORDER BY observed_at DESC,id DESC) AS rank
      FROM matches WHERE observed_at<=?) WHERE rank=1''', (limit,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def refresh_bundesliga(db, season, now):
    raise PermissionError('Live retrieval is disabled: effective API access conditions remain unverified')
