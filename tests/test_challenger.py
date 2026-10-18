import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from data import ROOT

if importlib.util.find_spec('challenger'):
    import challenger
else:
    challenger = None


def predictions(count=4):
    return [{'match_id': i, 'target': i % 2, 'p': 0.5, 'baseline': 0.5,
             'kickoff': f'2025-09-{i+1:02d}T15:00:00+00:00',
             'cutoff': f'2025-09-{i+1:02d}T14:00:00+00:00'} for i in range(count)]


class ChallengerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(challenger, 'Separate exploratory evaluator must exist')
        self.protocol = json.loads((ROOT/'config/challenger-v2.json').read_text())

    def test_protocol_rejects_unimplemented_or_release_claiming_changes(self):
        challenger.validate_protocol(self.protocol)
        for key, value in [('forecast_lead_minutes',30),('lag_hours',48),('operational_release',True),('alpha_grid',[0.2])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                challenger.validate_protocol(dict(self.protocol, **{key:value}))

    def test_sigmoid_failure_does_not_discard_valid_identity_candidate(self):
        from unittest.mock import patch
        from sklearn.exceptions import ConvergenceWarning
        from tests.test_poisson_model import count_rows
        rows=(count_rows('2018-01-01',1100)+count_rows('2022-08-01',600,10000)
              +count_rows('2024-08-05',1,20000))
        rows=[dict(r,home='Home',away='Away',season=2024,baseline=0.5) for r in rows]
        with patch('poisson_model.LogisticRegression.fit',side_effect=ConvergenceWarning('calibrator did not converge')):
            candidates,expected,folds=challenger.evaluate_season(rows,2024,['1.0:identity','1.0:sigmoid'])
        self.assertEqual(len(expected),1)
        self.assertEqual(len(candidates['1.0:identity']),1)
        self.assertEqual(candidates['1.0:sigmoid'],[])
        self.assertTrue(folds[0]['failures'])

    def test_complete_cohort_required_and_ties_prefer_shrinkage_then_identity(self):
        rows=predictions()
        expected={r['match_id'] for r in rows}
        chosen, losses, rejected=challenger.select_candidate(
            {'0.01:sigmoid':rows,'1.0:identity':rows,'0.1:identity':rows[:-1]}, expected)
        self.assertEqual(chosen,'1.0:identity')
        self.assertIn('0.1:identity',rejected)
        self.assertEqual(set(losses),{'0.01:sigmoid','1.0:identity'})
        with self.assertRaises(ValueError):
            challenger.select_candidate({'1.0:identity':rows[:-1]},expected)

    def test_comparator_checks_identity_time_label_and_baseline(self):
        rows=predictions()
        report=challenger.compare_frozen(rows, rows)
        self.assertEqual(report['shared_count'],4)
        self.assertFalse(report['operational_release'])
        for key,value in [('target',7),('cutoff','2025-01-01T00:00:00Z'),('baseline',0.7)]:
            bad=[dict(r) for r in rows];bad[0][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):
                challenger.compare_frozen(rows,bad)

    def test_existing_run_is_never_overwritten_or_completed_from_partial_state(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); sentinel=folder/'run-state.json';sentinel.write_text('previous')
            with self.assertRaises(FileExistsError):
                challenger.run_experiment(None,self.protocol,folder,[])
            self.assertEqual(sentinel.read_text(),'previous')

    def test_summary_cannot_certify_a_retrospective_challenger(self):
        result=challenger.exploratory_summary(predictions(4))
        self.assertEqual(result['release_state'],'retrospective_exploratory')
        self.assertFalse(result['operational_release'])
        self.assertNotIn('retrospective_metric_gate',result)

    def test_outer_plan_uses_only_preceding_inner_season(self):
        schedule=challenger.nested_schedule(self.protocol)
        self.assertEqual(schedule,[(2023,2024),(2024,2025)])
        self.assertTrue(all(inner<outer for inner,outer in schedule))
