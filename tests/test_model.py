import copy
import unittest
from datetime import datetime, timedelta, timezone

import model


def sample_rows(start, count, offset=0):
    rows = []
    for i in range(count):
        kickoff = datetime.fromisoformat(start).replace(tzinfo=timezone.utc) + timedelta(days=i)
        y = i % 2
        rows.append({'match_id': offset+i, 'kickoff': kickoff.isoformat(),
                     'cutoff': (kickoff-timedelta(hours=1)).isoformat(),
                     'target': y, 'baseline': 0.5, 'values': [float(y)] * 12})
    return rows


class ModelTests(unittest.TestCase):
    def test_calibration_minimum_and_class_counts_fail_closed(self):
        train = sample_rows('2018-01-01', 240)
        for cal in (sample_rows('2020-01-01', 499, 1000),
                    [dict(r, target=1) for r in sample_rows('2020-01-01', 500, 1000)]):
            with self.assertRaises(ValueError): model.fit_pair(train, cal, {'C': 1, 'calibration': 'sigmoid'})

    def test_overlap_and_future_cutoff_rejected(self):
        train = sample_rows('2020-01-01', 240)
        cal = sample_rows('2020-04-01', 500, 1000)
        with self.assertRaises(ValueError): model.fit_pair(train, cal, {'C': 1, 'calibration': 'identity'})
        bad = sample_rows('2018-01-01', 240)
        bad[0]['cutoff'] = '2025-01-01T00:00:00Z'
        with self.assertRaises(ValueError): model.fit_pair(bad, sample_rows('2020-01-01', 500, 1000), {})

    def test_pair_predicts_finite_research_values_and_lineage_is_bound(self):
        pair = model.fit_pair(sample_rows('2018-01-01', 240), sample_rows('2020-01-01', 500, 1000),
                              {'C': 1, 'calibration': 'sigmoid'})
        p0 = model.predict_pair(pair, {'values': [0.] * 12})
        p1 = model.predict_pair(pair, {'values': [1.] * 12})
        self.assertTrue(0 < p0['calibrated_p'] < p1['calibrated_p'] < 1)
        self.assertEqual(p1['state'], 'research')
        broken = copy.copy(pair)
        broken['calibration_for'] = 'another-model'
        with self.assertRaises(ValueError): model.predict_pair(broken, {'values': [1.] * 12})
        with self.assertRaises(ValueError): model.predict_pair(pair, {'values': [float('nan')] * 12})

    def test_metrics_use_probabilities_not_hit_rate(self):
        result = model.metrics([0, 1], [0.25, 0.75])
        self.assertAlmostEqual(result['brier'], 0.0625)
        self.assertAlmostEqual(result['log_loss'], 0.28768207245)
        with self.assertRaises(ValueError): model.metrics([0, 1], [float('nan'), 0.5])
