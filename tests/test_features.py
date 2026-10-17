import json
import unittest
from datetime import datetime, timedelta, timezone

import data
import features
from tests.test_data import match, NOW


class FeatureTests(unittest.TestCase):
    def populated(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        rows = [match(i + 1, f'2024-01-{i+1:02}T15:00:00Z', ht=(1, 0)) for i in range(12)]
        rows.append(match(99, '2024-01-31T15:00:00Z'))
        data.ingest_snapshot(db, json.dumps(rows).encode(),
                             {'source': 'OpenLigaDB', 'season': 2023, 'observed_at': NOW.isoformat()})
        return db

    def test_smoothed_baseline_has_no_invented_empty_history_value(self):
        self.assertIsNone(features.league_baseline([]))
        self.assertEqual(features.league_baseline([{'target': 1}, {'target': 0}]), 0.5)

    def test_reconstructed_features_use_prior_matches_and_counts(self):
        db = self.populated()
        row = features.build_features(db, 99, '2024-01-31T14:00:00Z', 'retrospective')
        self.assertEqual(row['state'], 'eligible')
        self.assertEqual(row['history_counts']['home'], 12)
        self.assertEqual(row['history_counts']['away'], 12)
        self.assertAlmostEqual(row['baseline'], 13 / 14)
        # Twelve scored goals + ten prior matches at league mean 0.5.
        self.assertAlmostEqual(row['values'][0], 17 / 22)
        self.assertAlmostEqual(row['values'][1], 5 / 22)
        self.assertNotIn(99, row['contributing_ids'])
        self.assertEqual(row['availability_mode'], 'retrospective_reconstruction')

    def test_prospective_rejects_records_first_observed_after_cutoff(self):
        row = features.build_features(self.populated(), 99, '2024-01-31T14:00:00Z', 'prospective')
        self.assertEqual(row['state'], 'abstained')
        self.assertEqual(row['reason'], 'fixture_not_observed')

    def test_lag_blocks_same_day_and_simultaneous_results(self):
        db = self.populated()
        row = features.build_features(db, 99, '2024-01-12T15:00:00Z', 'retrospective')
        self.assertNotIn(12, row['contributing_ids'])
        self.assertIn(11, row['contributing_ids'])
        delayed = features.build_features(db, 99, '2024-01-12T15:00:00Z', 'retrospective', lag_hours=48)
        self.assertNotIn(11, delayed['contributing_ids'])

    def test_new_team_abstains_and_cannot_borrow_another_team_history(self):
        db = self.populated()
        data.ingest_snapshot(db, json.dumps([match(100, '2024-02-01T15:00:00Z', home=3)]).encode(),
                             {'source': 'OpenLigaDB', 'season': 2023, 'observed_at': NOW.isoformat()})
        row = features.build_features(db, 100, '2024-02-01T14:00:00Z', 'retrospective')
        self.assertEqual(row['state'], 'abstained')
        self.assertEqual(row['reason'], 'insufficient_team_history')
        self.assertEqual(row['history_counts']['home'], 0)

    def test_unknown_mode_and_negative_lag_rejected(self):
        for mode, lag in [('wrong', 24), ('retrospective', -1)]:
            with self.assertRaises(ValueError):
                features.build_features(self.populated(), 99, NOW, mode, lag_hours=lag)
