"""Documented OpenLigaDB read-only fixture feed, separate from frozen research."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

from data import normalize_match, utc

MAX_BYTES = 2_000_000
WAT = timezone(timedelta(hours=1))


def season_for(now):
    return utc(now).year - (utc(now).month < 7)


def fetch_season(season, now=None):
    now = utc(now or datetime.now(timezone.utc))
    if type(season) is not int or not 1990 <= season <= now.year:
        raise ValueError('Invalid season')
    url = f'https://api.openligadb.de/getmatchdata/bl1/{season}'
    request = Request(url, headers={'User-Agent': 'FirstHalfGoalsEngine/1.0 (+https://github.com/mavtrevor/first-half-goals-engine)',
                                    'Accept': 'application/json'})
    with urlopen(request, timeout=15) as response:
        if response.geturl() != url:
            raise ValueError('Unexpected data-source redirect')
        payload = response.read(MAX_BYTES+1)
    if len(payload) > MAX_BYTES:
        raise ValueError('Fixture response exceeds size limit')
    rows = json.loads(payload.decode('utf-8-sig'))
    if not isinstance(rows, list) or not 1 <= len(rows) <= 400:
        raise ValueError('Expected a Bundesliga season response')
    digest = hashlib.sha256(payload).hexdigest()
    matches = []
    for row in rows:
        if not isinstance(row, dict) or row.get('leagueSeason') != season:
            raise ValueError('Fixture season mismatch')
        try:
            match = normalize_match(row, now)
        except (AttributeError, KeyError, TypeError) as exc:
            raise ValueError('Malformed fixture structure') from exc
        match['snapshot_hash'] = digest
        matches.append(match)
    if len({r['match_id'] for r in matches}) != len(matches):
        raise ValueError('Duplicate fixture identities')
    return {'matches': matches, 'observed_at': now.isoformat(), 'source_url': url}


def upcoming_matches(matches, now, window):
    now = utc(now)
    today = now.astimezone(WAT).date()
    def admitted(row):
        kickoff = utc(row['kickoff'])
        if row['finished'] or kickoff <= now:
            return False
        if window in ('Today', 'Tomorrow'):
            return kickoff.astimezone(WAT).date() == today+timedelta(days=window == 'Tomorrow')
        return kickoff <= now+timedelta(days=int(window))
    return sorted([r for r in matches if admitted(r)], key=lambda r: r['kickoff'])


def recent_halves(matches, team_id, now):
    rows = sorted([r for r in matches if r.get('target') in (0, 1)
                   and r.get('finished') and utc(r['kickoff']) < utc(now)
                   and team_id in (r['home_id'], r['away_id'])], key=lambda r: r['kickoff'])[-10:]
    return f'{sum(r["target"] for r in rows)} / {len(rows)}' if rows else 'No HT results'
