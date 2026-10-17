import unittest
import evaluation


class EvaluationTests(unittest.TestCase):
    def test_paper_returns_require_known_settlement(self):
        self.assertAlmostEqual(evaluation.paper_return(1.25, 'win'), 0.25)
        self.assertEqual(evaluation.paper_return(1.25, 'loss'), -1)
        self.assertEqual(evaluation.paper_return(1.25, 'void'), 0)
        self.assertIsNone(evaluation.paper_return(1.25, 'pending'))
        with self.assertRaises(ValueError): evaluation.paper_return(float('nan'), 'win')

    def test_only_fixed_window_decisions_can_enter_paper_ledger(self):
        self.assertTrue(evaluation.in_decision_window('2026-10-17T14:00:00Z', '2026-10-17T15:00:00Z'))
        self.assertFalse(evaluation.in_decision_window('2026-10-17T14:10:00Z', '2026-10-17T15:00:00Z'))
        self.assertFalse(evaluation.in_decision_window('2026-10-17T16:00:00Z', '2026-10-17T15:00:00Z'))
