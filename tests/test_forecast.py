import json
import unittest
from datetime import timedelta

import data
import forecast
from tests.test_data import match, NOW


class ForecastTests(unittest.TestCase):
    def test_pending_release_gate_means_null_forecast_never_guessed_probability(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        raw = match(7, (NOW+timedelta(hours=1)).isoformat())
        raw['matchIsFinished'] = False
        data.ingest_snapshot(db, json.dumps([raw]).encode(),
                             {'source': 'OpenLigaDB', 'season': 2023, 'observed_at': NOW.isoformat()})
        saved = forecast.record_forecast(db, 7, NOW)
        self.assertIsNone(saved['calibrated_p'])
        self.assertEqual(saved['state'], 'abstained')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0], 1)

    def test_unknown_fixture_cannot_receive_a_probability(self):
        db = data.connect(':memory:')
        self.addCleanup(db.close)
        saved = forecast.record_forecast(db, 999, NOW)
        self.assertEqual(saved['reason'], 'unknown_fixture')
