import os
import tempfile
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous = os.environ.get('FH_ENGINE_DATA_DIR')
        os.environ['FH_ENGINE_DATA_DIR'] = self.temp.name
        def restore():
            if previous is None: os.environ.pop('FH_ENGINE_DATA_DIR', None)
            else: os.environ['FH_ENGINE_DATA_DIR'] = previous
        self.addCleanup(restore)

    def test_empty_app_shows_offline_scope_without_probabilities(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        text = '\n'.join(str(x.value) for x in app.info)
        self.assertIn('No fixtures', text)
        self.assertIn('No backtest', text)
        self.assertEqual([t.label for t in app.tabs], ['Fixtures', 'Data audit', 'Backtest', 'Manual records', 'Readiness'])
        verified = next(m for m in app.metric if m.label == 'Validated forecasts')
        self.assertEqual(verified.value, '0')

    def test_empty_manual_forms_cannot_create_booking_or_observation(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(any(b.label == 'Generate code' for b in app.button))
        self.assertTrue(any('Live retrieval is disabled' in str(w.value) for w in app.warning))
