import copy
import hashlib
import json
import sqlite3
import unittest
from datetime import datetime, timezone

import data


def match(mid=1, kickoff='2024-01-01T15:00:00Z', home=1, away=2, ht=(0, 0), ft=(1, 0)):
    return {'matchID': mid, 'leagueShortcut': 'bl1', 'leagueSeason': 2023,
            'matchDateTimeUTC': kickoff, 'matchIsFinished': True,
            'team1': {'teamId': home, 'teamName': f'Team {home}'},
            'team2': {'teamId': away, 'teamName': f'Team {away}'},
            'matchResults': [
                {'resultTypeKind': 'After90Minutes', 'pointsTeam1': ft[0], 'pointsTeam2': ft[1]},
                {'resultTypeKind': 'HalfTime', 'pointsTeam1': ht[0], 'pointsTeam2': ht[1]}]}


NOW = datetime(2026, 10, 17, 8, 20, tzinfo=timezone.utc)


class DataTests(unittest.TestCase):
    def test_score_semantics_ignore_array_order_and_zero_is_valid(self):
        raw = match()
        result = data.normalize_match(raw, NOW)
        raw['matchResults'].reverse()
        self.assertEqual(data.normalize_match(raw, NOW), result)
        self.assertEqual((result['ht_home'], result['ht_away'], result['target']), (0, 0, 0))

    def test_missing_half_time_stays_unknown_and_invalid_values_rejected(self):
        raw = match()
        raw['matchResults'] = raw['matchResults'][:1]
        self.assertIsNone(data.normalize_match(raw, NOW)['target'])
        for invalid in (-1, True, 0.5, '0'):
            with self.subTest(invalid=invalid):
                raw = match(ht=(invalid, 0))
                with self.assertRaises(ValueError):
                    data.normalize_match(raw, NOW)
        with self.assertRaises(ValueError):
            data.normalize_match(match(ht=(2, 0), ft=(1, 0)), NOW)

    def test_unknown_kind_duplicate_result_and_bad_identity_rejected(self):
        for change in ('unknown', 'duplicate', 'league', 'timezone', 'same_team'):
            raw = match()
            if change == 'unknown': raw['matchResults'][1]['resultTypeKind'] = 'Unknown'
            if change == 'duplicate': raw['matchResults'].append(copy.deepcopy(raw['matchResults'][1]))
            if change == 'league': raw['leagueShortcut'] = 'bl2'
            if change == 'timezone': raw['matchDateTimeUTC'] = '2024-01-01T15:00:00'
            if change == 'same_team': raw['team2'] = raw['team1']
            with self.subTest(change=change), self.assertRaises(ValueError):
                data.normalize_match(raw, NOW)

    def test_correction_requires_original_score_and_exact_snapshot_hash(self):
        raw = match(ht=(1, 0), ft=(8, 0))
        correction = {'source_match_id': 1, 'original_ht': '1-0', 'corrected_ht': '0-0',
                      'original_snapshot_sha256': 'ABC', 'authority_url': 'https://fcbayern.com/report'}
        corrected = data.resolve_result(raw, correction, 'ABC')
        self.assertEqual(corrected['matchResults'][1]['pointsTeam1'], 0)
        self.assertEqual(raw['matchResults'][1]['pointsTeam1'], 1)
        for digest in ('DEF', ''):
            with self.assertRaises(ValueError): data.resolve_result(raw, correction, digest)
        with self.assertRaises(ValueError): data.resolve_result(match(), correction, 'ABC')

    def test_ingest_idempotent_versioned_and_duplicate_transaction_rolls_back(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        payload = json.dumps([match()]).encode()
        meta = {'source': 'OpenLigaDB', 'observed_at': NOW.isoformat(), 'season': 2023}
        sid = data.ingest_snapshot(db, payload, meta)
        self.assertEqual(data.ingest_snapshot(db, payload, meta), sid)
        self.assertEqual(len(data.latest_matches(db)), 1)
        with self.assertRaises(ValueError):
            data.ingest_snapshot(db, json.dumps([match(2), match(2)]).encode(), meta)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0], 1)
        altered = match(ht=(1, 0))
        meta2 = dict(meta, observed_at='2026-10-18T08:20:00+00:00')
        data.ingest_snapshot(db, json.dumps([altered]).encode(), meta2)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM matches').fetchone()[0], 2)
        self.assertEqual(data.latest_matches(db)[0]['target'], 1)

    def test_quarantined_new_version_cannot_leave_old_valid_score_current(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        meta = {'source': 'OpenLigaDB', 'observed_at': NOW.isoformat(), 'season': 2023}
        data.ingest_snapshot(db, json.dumps([match()]).encode(), meta)
        bad = match(ht=(2, 0), ft=(1, 0))
        data.ingest_snapshot(db, json.dumps([bad]).encode(), dict(meta, observed_at='2026-10-18T08:20:00Z'))
        current = data.latest_matches(db)[0]
        self.assertEqual(current['quality'], 'quarantined')
        self.assertIsNone(current['target'])

    def test_same_bytes_with_changed_corrections_fail_explicitly(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        payload = json.dumps([match(ht=(1, 0))]).encode()
        meta = {'source': 'OpenLigaDB', 'observed_at': NOW.isoformat(), 'season': 2023}
        correction = {'source_match_id': 1, 'original_ht': '1-0', 'corrected_ht': '0-0',
                      'original_snapshot_sha256': hashlib.sha256(payload).hexdigest(),
                      'authority_url': 'https://fcbayern.com/report'}
        data.ingest_snapshot(db, payload, meta)
        with self.assertRaisesRegex(ValueError, 'correction'):
            data.ingest_snapshot(db, payload, meta, [correction])
        self.assertEqual(data.latest_matches(db)[0]['target'], 1)

    def test_live_refresh_fails_closed(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        with self.assertRaises(PermissionError):
            data.refresh_bundesliga(db, 2026, NOW)


if __name__ == '__main__': unittest.main()
