import io
import json
import unittest
from datetime import timedelta
from unittest.mock import patch

from tests.test_data import NOW, match
import live


class Response(io.BytesIO):
    def geturl(self):
        return 'https://api.openligadb.de/getmatchdata/bl1/2026'


class LiveTests(unittest.TestCase):
    def fixture(self):
        row = match(kickoff=(NOW+timedelta(hours=2)).isoformat())
        row.update(leagueSeason=2026, matchIsFinished=False, matchResults=[])
        return row

    def test_documented_read_only_endpoint_and_bounded_response(self):
        response = Response(json.dumps([self.fixture()]).encode())
        with patch('live.urlopen', return_value=response) as request:
            result = live.fetch_season(2026, NOW)
        self.assertEqual(result['matches'][0]['match_id'], 1)
        self.assertEqual(result['observed_at'], NOW.isoformat())
        self.assertEqual(request.call_args.args[0].full_url,
                         'https://api.openligadb.de/getmatchdata/bl1/2026')
        self.assertEqual(request.call_args.kwargs['timeout'], 15)
        self.assertIn('snapshot_hash', result['matches'][0])
        with patch('live.urlopen', return_value=Response(b' ' * (live.MAX_BYTES+1))):
            with self.assertRaises(ValueError): live.fetch_season(2026, NOW)

    def test_invalid_response_never_becomes_live_fixture(self):
        row = self.fixture()
        cases = [[], {}, [None], [dict(row, team1=None)], [row, row], [dict(row, leagueSeason=2025)],
                 [dict(row, matchDateTimeUTC='2026-10-17T12:00:00')]]
        for payload in cases:
            with self.subTest(payload=payload), patch('live.urlopen', return_value=Response(json.dumps(payload).encode())):
                with self.assertRaises(ValueError): live.fetch_season(2026, NOW)

    def test_future_only_filter_and_counts_exclude_missing_and_future_scores(self):
        future = live.normalize_match(self.fixture(), NOW)
        past = live.normalize_match(match(mid=2, kickoff=(NOW-timedelta(days=1)).isoformat(), ht=(1,0)), NOW)
        unknown = dict(past, match_id=3, target=None)
        self.assertEqual(live.upcoming_matches([future, past], NOW, 7), [future])
        self.assertEqual(live.recent_halves([future, past, unknown], 1, NOW), '1 / 1')
        self.assertEqual(live.recent_halves([], 1, NOW), 'No HT results')

    def test_nigeria_day_boundary_and_season_rollover(self):
        self.assertEqual(live.season_for(NOW.replace(month=7)), 2026)
        self.assertEqual(live.season_for(NOW.replace(month=6)), 2025)
        now = NOW.replace(hour=22, minute=0)
        row = live.normalize_match(dict(self.fixture(), matchDateTimeUTC=now.replace(hour=23,minute=30).isoformat()), NOW)
        self.assertEqual(live.upcoming_matches([row], now, 'Today'), [])
        self.assertEqual(live.upcoming_matches([row], now, 'Tomorrow'), [row])


if __name__ == '__main__': unittest.main()
