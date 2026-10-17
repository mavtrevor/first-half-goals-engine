import unittest
from datetime import datetime, timezone

import backtest
from tests.test_model import sample_rows


class BacktestTests(unittest.TestCase):
    def test_provenance_preserves_effective_labels_and_code(self):
        import json
        import tempfile
        from pathlib import Path
        import data
        from tests.test_data import match, NOW
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        data.ingest_snapshot(db, json.dumps([match()]).encode(),
            {'source': 'OpenLigaDB', 'season': 2023, 'observed_at': NOW.isoformat()})
        with tempfile.TemporaryDirectory() as folder:
            backtest.archive_inputs(db, Path(folder), {'name': 'test'})
            root = Path(folder)
            manifest = json.loads((root/'run-manifest.json').read_text())
            self.assertIn('data.py', manifest['code_sha256'])
            self.assertEqual(json.loads((root/'effective-inputs.json').read_text())[0]['target'], 0)
            self.assertTrue(manifest['effective_inputs_sha256'])
            self.assertEqual(len(manifest['snapshots']), 1)

    def test_label_split_honors_48_hour_lag(self):
        row = {'match_id': 1, 'kickoff': '2024-07-30T20:00:00Z'}
        start = datetime(2024, 8, 1, tzinfo=timezone.utc)
        self.assertEqual(len(backtest.split_month([row], start, lag_hours=24)[1]), 1)
        self.assertEqual(backtest.split_month([row], start, lag_hours=48)[1], [])

    def test_runner_rejects_misleading_protocol_before_using_database(self):
        import json
        from data import ROOT
        protocol = json.loads((ROOT/'config/evaluation-protocol.json').read_text())
        protocol['forecast_lead_minutes'] = 30
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            backtest.walk_forward(None, protocol)

    def test_calendar_folds_do_not_depend_on_input_order(self):
        rows = (sample_rows('2018-01-01', 240) + sample_rows('2022-08-01', 500, 1000)
                + sample_rows('2024-08-01', 30, 3000))
        first = backtest.split_month(rows, datetime(2024, 8, 1, tzinfo=timezone.utc))
        second = backtest.split_month(list(reversed(rows)), datetime(2024, 8, 1, tzinfo=timezone.utc))
        self.assertEqual([[r['match_id'] for r in s] for s in first],
                         [[r['match_id'] for r in s] for s in second])
        train, cal, test = first
        self.assertEqual(len(test), 30)
        self.assertTrue(set(r['match_id'] for r in train).isdisjoint(r['match_id'] for r in cal))
        self.assertTrue(set(r['match_id'] for r in cal).isdisjoint(r['match_id'] for r in test))

    def test_bootstrap_and_release_do_not_certify_tiny_samples(self):
        rows = [{'kickoff': '2024-08-01T15:00:00+00:00', 'target': 1, 'p': 0.7, 'baseline': 0.6}]
        report = backtest.summarize(rows)
        self.assertEqual(report['release_state'], 'research')
        self.assertIsNone(report['log_loss_difference_95ci'])
        self.assertEqual(report['count'], 1)

    def test_test_cutoff_cannot_be_in_calibration_or_training(self):
        rows = sample_rows('2024-08-01', 2, 9000)
        train, cal, test = backtest.split_month(rows, datetime(2024, 8, 1, tzinfo=timezone.utc))
        self.assertEqual(train, [])
        self.assertEqual(cal, [])
        self.assertEqual(len(test), 2)
