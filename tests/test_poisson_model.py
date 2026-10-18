import copy
import importlib.util
import math
import unittest
from datetime import datetime, timedelta, timezone

import numpy as np

if importlib.util.find_spec('poisson_model'):
    import poisson_model
else:
    poisson_model = None


def count_rows(start, count, offset=0):
    rng = np.random.default_rng(82 + offset)
    first = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        h, a = map(int, rng.choice(np.arange(1, 7), 2, replace=False))
        hg = int(rng.poisson(1.5 if h == 1 else 0.25))
        ag = int(rng.poisson(0.8 if a == 1 else 0.2))
        kickoff = first + timedelta(days=i)
        rows.append({'match_id': offset+i+1, 'home_id': h, 'away_id': a,
                     'ht_home': hg, 'ht_away': ag, 'target': int(hg+ag > 0),
                     'kickoff': kickoff.isoformat(), 'cutoff': (kickoff-timedelta(hours=1)).isoformat(),
                     'snapshot_hash': 'test-snapshot'})
    return rows


class PoissonTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(poisson_model, 'The isolated count model must exist')
        self.train = count_rows('2018-01-01', 800)
        self.cal = count_rows('2021-01-01', 600, 10000)

    def fit(self, method='identity'):
        return poisson_model.fit_counts(self.train, self.cal, alpha=0.01, calibration=method)

    def fixture(self, home=1, away=2):
        return {'match_id': 90000, 'home_id': home, 'away_id': away,
                'kickoff': '2024-01-01T15:00:00Z', 'cutoff': '2024-01-01T14:00:00Z'}

    def test_count_probability_arithmetic_and_invalid_rates(self):
        self.assertAlmostEqual(poisson_model.probability_from_rates(0.7, 0.3), 1-math.exp(-1))
        for rate in (-1, float('nan'), float('inf'), True):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                poisson_model.probability_from_rates(rate, 0.2)

    def test_team_attack_effect_and_unknown_team_shrinkage(self):
        pair = self.fit()
        high = poisson_model.predict_counts(pair, self.fixture())
        low = poisson_model.predict_counts(pair, self.fixture(3, 2))
        unknown = poisson_model.predict_counts(pair, self.fixture(99, 98))
        self.assertGreater(high['raw_p'], low['raw_p'])
        self.assertEqual(unknown['unseen_teams'], [99, 98])
        self.assertAlmostEqual(unknown['lambda_home'], math.exp(pair['home'].intercept_))
        self.assertAlmostEqual(high['raw_p'], poisson_model.probability_from_rates(high['lambda_home'], high['lambda_away']))
        self.assertEqual(high['state'], 'retrospective_exploratory')
        self.assertFalse(high['operational_release'])

    def test_invalid_labels_counts_ids_and_calibration_support_fail_closed(self):
        for key, value in [('ht_home', -1), ('ht_home', True), ('ht_away', 0.5),
                           ('home_id', True), ('target', 7), ('cutoff', '2035-01-01T00:00:00Z')]:
            bad = copy.deepcopy(self.train)
            bad[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                poisson_model.fit_counts(bad, self.cal, alpha=0.01)
        with self.assertRaises(ValueError):
            poisson_model.fit_counts(self.train, self.cal[:499], alpha=0.01)
        all_positive = [dict(r, ht_home=1, ht_away=0, target=1) for r in self.cal]
        with self.assertRaises(ValueError):
            poisson_model.fit_counts(self.train, all_positive, alpha=0.01)

    def test_overlap_lag_and_prediction_chronology_rejected(self):
        overlapping = copy.deepcopy(self.cal)
        overlapping[0]['match_id'] = self.train[0]['match_id']
        with self.assertRaises(ValueError):
            poisson_model.fit_counts(self.train, overlapping, alpha=0.01)
        late = copy.deepcopy(self.train)
        late[-1].update(kickoff='2020-12-31T18:00:00Z', cutoff='2020-12-31T17:00:00Z')
        with self.assertRaises(ValueError):
            poisson_model.fit_counts(late, self.cal, alpha=0.01)
        pair = self.fit()
        with self.assertRaises(ValueError):
            poisson_model.predict_counts(pair, dict(self.fixture(), cutoff=self.cal[-1]['kickoff']))

    def test_calibration_lineage_and_nonfinite_inference_rejected(self):
        pair = self.fit('sigmoid')
        result = poisson_model.predict_counts(pair, self.fixture())
        self.assertTrue(0 < result['calibrated_p'] < 1)
        self.assertEqual(result['model_id'], pair['calibration_for'])
        pair['calibration_for'] = 'different-model'
        with self.assertRaises(ValueError):
            poisson_model.predict_counts(pair, self.fixture())
        pair = self.fit()
        pair['home'].intercept_ = float('nan')
        with self.assertRaises(ValueError):
            poisson_model.predict_counts(pair, self.fixture())

    def test_inference_requires_a_valid_fixture_identity(self):
        pair = self.fit()
        for mid in (None,True,0,-1):
            row = dict(self.fixture(),match_id=mid)
            if mid is None:
                row.pop('match_id')
            with self.subTest(mid=mid), self.assertRaises(ValueError):
                poisson_model.predict_counts(pair,row)
