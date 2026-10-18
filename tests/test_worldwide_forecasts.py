import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from tests.test_worldwide import event
from tests.test_worldwide_store import NOW
from worldwide_store import connect_worldwide
import worldwide_forecasts as forecasts


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=connect_worldwide(Path(self.temp.name)/'w.sqlite');self.addCleanup(self.db.close)
        self.fixture=event(hours=1,home_id='fd:1',away_id='fd:2',snapshot_hash='hash')

    def test_no_backdated_forecast_or_public_release_boolean(self):
        row=forecasts.record_shadow(self.db,event(hours=2),None,{},NOW)
        self.assertIsNone(row['calibrated_p'])
        self.assertEqual(row['reason'],'outside_forecast_window')
        self.assertIsNone(forecasts.public_estimate(dict(calibrated_p=.99,state='shadow'),dict(released=True),NOW)['probability'])

    def test_source_time_history_mapping_and_immutable_record(self):
        pair=dict(model_id='model')
        inputs=dict(event_id=self.fixture['event_id'],match_id=1,home_id=2,away_id=3,
            cutoff=NOW.isoformat(),kickoff=self.fixture['kickoff'],fixture_hash='hash',
            source_home_id='fd:1',source_away_id='fd:2',home_history=10,away_history=10,
            maximum_observed_at=NOW.isoformat(),input_hashes=['one'])
        with patch('worldwide_forecasts.predict_counts',return_value=dict(raw_p=.7,calibrated_p=.71,model_id='model',unseen_teams=[])):
            row=forecasts.record_shadow(self.db,self.fixture,pair,inputs,NOW)
            again=forecasts.record_shadow(self.db,self.fixture,None,{},NOW+timedelta(minutes=1))
        self.assertEqual(row,again)
        self.assertEqual(row['calibrated_p'],.71)
        self.assertIsNone(forecasts.public_estimate(row,dict(released=True),NOW)['probability'])
        changed=dict(self.fixture,event_id='fd:2')
        late=forecasts.record_shadow(self.db,changed,pair,dict(inputs,maximum_observed_at=(NOW+timedelta(minutes=2)).isoformat()),NOW)
        self.assertIsNone(late['calibrated_p'])

    def test_settlements_append_revisions_do_not_change_shadow(self):
        row=forecasts.record_shadow(self.db,self.fixture,None,{},NOW)
        result=dict(self.fixture,status='FINISHED',ht_home=0,ht_away=0,ft_home=1,ft_away=0,
                    target=0,observed_at=(NOW+timedelta(hours=3)).isoformat())
        forecasts.settle_shadow(self.db,self.fixture,result,NOW+timedelta(hours=3))
        forecasts.settle_shadow(self.db,self.fixture,dict(result,ht_home=1,target=1),NOW+timedelta(hours=4))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM settlements').fetchone()[0],2)
        self.assertEqual(json.loads(self.db.execute('SELECT record FROM shadows').fetchone()[0]),row)


if __name__=='__main__':unittest.main()
