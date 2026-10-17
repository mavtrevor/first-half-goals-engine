"""Score-only features with explicit reconstructed versus observed availability."""
from datetime import timedelta

from data import latest_matches, utc

FEATURE_NAMES = ('home_scored', 'home_conceded', 'away_scored', 'away_conceded',
                 'home_nonzero', 'away_nonzero', 'home_venue_scored', 'home_venue_conceded',
                 'away_venue_scored', 'away_venue_conceded', 'home_history', 'away_history')


def league_baseline(history):
    valid = [r['target'] for r in history if r.get('target') in (0, 1)]
    return (sum(valid) + 1) / (len(valid) + 2) if valid else None


def build_features(db, match_id, cutoff, mode, lag_hours=24, smoothing=10, records=None):
    cutoff = utc(cutoff)
    if mode not in ('retrospective', 'prospective') or lag_hours < 0 or smoothing <= 0:
        raise ValueError('Invalid availability mode, lag or smoothing')
    rows = records if records is not None else latest_matches(db, cutoff if mode == 'prospective' else None)
    if mode == 'prospective':
        rows = [r for r in rows if utc(r['observed_at']) <= cutoff]
    fixture = next((r for r in rows if r['match_id'] == match_id), None)
    out = {'match_id': match_id, 'cutoff': cutoff.isoformat(), 'state': 'abstained',
           'availability_mode': 'retrospective_reconstruction' if mode == 'retrospective' else 'observed',
           'contributing_ids': [], 'input_hashes': [], 'values': None, 'baseline': None}
    if fixture is None or fixture['quality'] == 'quarantined':
        return dict(out, reason='fixture_not_observed')
    boundary = cutoff - timedelta(hours=lag_hours) if mode == 'retrospective' else cutoff
    oldest = cutoff - timedelta(days=5 * 366)
    history = sorted((r for r in rows if r.get('target') in (0, 1) and r['match_id'] != match_id
                      and r.get('competition') == 'bl1' and oldest <= utc(r['kickoff']) <= boundary
                      and utc(r['kickoff']) < cutoff), key=lambda r: (r['kickoff'], r['match_id']))
    if mode == 'prospective':
        history = [r for r in history if utc(r['observed_at']) <= cutoff]
    hid, aid = fixture['home_id'], fixture['away_id']
    home = [r for r in history if hid in (r['home_id'], r['away_id'])][-20:]
    away = [r for r in history if aid in (r['home_id'], r['away_id'])][-20:]
    out.update(baseline=league_baseline(history), contributing_ids=[r['match_id'] for r in history],
               input_hashes=sorted({r['snapshot_hash'] for r in history}),
               history_counts={'home': len(home), 'away': len(away)},
               home=fixture['home'], away=fixture['away'], kickoff=fixture['kickoff'],
               season=fixture['season'], target=fixture.get('target'),
               fixture_hash=fixture['snapshot_hash'])
    if len(home) < 10 or len(away) < 10:
        return dict(out, reason='insufficient_team_history')
    league_home = sum(r['ht_home'] for r in history) / len(history)
    league_away = sum(r['ht_away'] for r in history) / len(history)
    league_team = (league_home + league_away) / 2

    def rate(games, team, conceded=False, prior=league_team, minimum=0):
        if len(games) < minimum:
            return prior
        total = sum(r['ht_away'] if (r['home_id'] == team) == conceded else r['ht_home'] for r in games)
        return (total + smoothing * prior) / (len(games) + smoothing)

    def nonzero(games):
        return (sum(r['target'] for r in games) + smoothing * out['baseline']) / (len(games) + smoothing)

    hv = [r for r in history if r['home_id'] == hid][-20:]
    av = [r for r in history if r['away_id'] == aid][-20:]
    values = [rate(home, hid), rate(home, hid, True), rate(away, aid), rate(away, aid, True),
              nonzero(home), nonzero(away),
              rate(hv, hid, prior=league_home, minimum=5), rate(hv, hid, True, prior=league_away, minimum=5),
              rate(av, aid, prior=league_away, minimum=5), rate(av, aid, True, prior=league_home, minimum=5),
              len(home), len(away)]
    return dict(out, state='eligible', reason=None, values=values, feature_names=FEATURE_NAMES)
