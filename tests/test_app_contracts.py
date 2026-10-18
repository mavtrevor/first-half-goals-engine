import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import streamlit as st
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_challenger_is_explicitly_exploratory_and_never_validated_forecast(self):
        folder = Path(self.temp.name)/'reports/poisson-v2-exploratory'
        folder.mkdir(parents=True)
        (folder/'report.json').write_text(json.dumps({'state':'retrospective_exploratory',
            'operational_release':False, 'pooled_outer':{'count':12,'log_loss':0.54,
                'baseline':{'log_loss':0.55},'log_loss_difference_95ci':[-0.01,0.02]}, 'selections':[],
            'v1_common_cohort':{'shared_count':2,
                'challenger':{'count':2,'log_loss':0.53,'brier':0.17,'auc':0.58},
                'original_v1':{'count':2,'log_loss':0.54,'brier':0.18,'auc':0.51},
                'challenger_minus_v1_weekly_95ci':[-0.0118,-0.0001],
                'challenger_minus_v1_fortnightly_95ci':[-0.0133,0.0004]}}))
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any('already inspected' in str(w.value) for w in app.warning))
        self.assertEqual(next(m for m in app.metric if m.label == 'Validated forecasts').value,'0')
        self.assertEqual(next(m for m in app.metric if m.label == 'Exploratory challenger matches').value,'12')
        self.assertTrue(any('includes zero' in str(x.value) for x in app.markdown))
        self.assertTrue(any('sensitive to block length' in str(x.value) for x in app.markdown))

    def setUp(self):
        st.cache_data.clear()
        network = patch('live.fetch_season', side_effect=OSError('Test source unavailable'))
        network.start()
        self.addCleanup(network.stop)
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
        self.assertTrue(any('Retrospective research' in str(x.value) for x in app.info))
        self.assertEqual([t.label for t in app.tabs], ['Fixtures', 'Data audit', 'Backtest', 'Manual records', 'Readiness'])
        verified = next(m for m in app.metric if m.label == 'Validated forecasts')
        self.assertEqual(verified.value, '0')

    def test_empty_manual_forms_cannot_create_booking_or_observation(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(any(b.label == 'Generate code' for b in app.button))
        self.assertTrue(any('could not be checked' in str(w.value) for w in app.error))

    def test_live_fixtures_show_with_no_local_database_and_no_fabricated_probability(self):
        now = datetime.now(timezone.utc)
        fixture = {'match_id':123,'home_id':1,'away_id':2,'home':'Home FC','away':'Away FC',
                   'kickoff':(now+timedelta(days=2)).isoformat(),'finished':False,
                   'target':None,'snapshot_hash':'abc','quality':'fixture_only'}
        with patch('live.fetch_season', return_value={'matches':[fixture],
                   'observed_at':now.isoformat(),'source_url':'https://api.openligadb.de/getmatchdata/bl1/2026'}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(next(m for m in app.metric if m.label == 'Upcoming games').value,'1')
        self.assertEqual(app.dataframe[0].value.iloc[0]['Home'], 'Home FC')
        self.assertEqual(app.dataframe[0].value.iloc[0]['Probability'], 'Not validated')
        self.assertEqual(app.dataframe[0].value.iloc[0]['Home FH goals / games'], 'No HT results')
        self.assertFalse(any(b.label == 'Save human observation' for b in app.button))
        self.assertEqual(next(m for m in app.metric if m.label == 'Validated forecasts').value,'0')
