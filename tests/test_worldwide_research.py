import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from tests.test_worldwide_store import NOW
from worldwide_store import connect_worldwide
import worldwide_research as research


def finished(mid, days=2, competition='fd:1', **changes):
    return dict(dict(event_id=f'fd:{mid}',provider='fd',competition_id=competition,season_id=2026,
        home_id='fd:1',away_id='fd:2',kickoff=(NOW-timedelta(days=days)).isoformat(),observed_at=NOW.isoformat(),
        snapshot_hash='source-hash',status='FINISHED',classification='senior_real',quality='structurally_valid',
        ht_home=1,ht_away=0,ft_home=1,ft_away=0,target=1),**changes)


class ResearchTests(unittest.TestCase):
    def test_api_history_uses_requested_seasons_end_date_not_current_catalog(self):
        competition=dict(id=71,name='Serie A',country='Brazil',region='South America',classification='senior_real')
        fixture=dict(fixture=dict(id=123,date='2024-10-01T12:00:00Z',status=dict(short='FT')),
            league=dict(id=71,season=2024),teams=dict(home=dict(id=1,name='Home'),away=dict(id=2,name='Away')),
            score=dict(halftime=dict(home=0,away=0),fulltime=dict(home=1,away=0)))
        def response(provider,path,params,token,now,db):
            if path=='/leagues':
                return dict(response=[dict(league=dict(id=71),seasons=[dict(year=2024,end='2024-12-31')])],paging=dict(total=1)),dict(state='ready',source_url='https://v3.football.api-sports.io/leagues',observed_at=NOW.isoformat())
            return dict(response=[fixture]),dict(state='ready',source_url='https://v3.football.api-sports.io/fixtures',observed_at=NOW.isoformat())
        with tempfile.TemporaryDirectory() as folder:
            db=connect_worldwide(Path(folder)/'w.sqlite')
            try:
                with patch('worldwide_research.read_json',side_effect=response):
                    result=research.import_history(db,'api_football',competition,['2024'],'secret',NOW)
                self.assertEqual(result['state'],'ready')
                self.assertTrue(research.league_rows(db,'api_football:71',NOW,'observed')[0]['season_complete'])
            finally:db.close()

    def test_outer_choices_are_sealed_before_outer_evaluation(self):
        protocol=json.loads((research.ROOT/'config/worldwide-protocol.json').read_text())
        rows=[finished(i,days=i+2,season_year=2024 if i<15 else 2025,season_complete=True) for i in range(1,30)]
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'run'
            def evaluate(all_rows,eligible,year,alpha,calibration):
                if year==2025:self.assertTrue((target/'selection.json').exists())
                predictions=[dict(event_id=f'fd:{i}',match_id=i,kickoff=rows[i]['kickoff'],
                    target=i%2,p=.6,baseline=.55) for i in range(10)]
                return dict(predictions=predictions,complete=True,folds=[],expected_count=10)
            with patch('worldwide_research._evaluate_period',side_effect=evaluate):
                report=research.evaluate_league(rows,protocol,target)
            self.assertEqual(report['selection']['alpha'],1.0)
            self.assertEqual(report['selection']['calibration'],'identity')
            self.assertEqual(len(report['predictions']),10)
            self.assertFalse(report['operational_release'])

    def test_frozen_protocol_archive_and_release_cannot_be_overridden(self):
        protocol=json.loads((Path(research.ROOT)/'config/worldwide-protocol.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'run'
            report=research.evaluate_league([finished(1)],protocol,target)
            self.assertFalse(report['operational_release'])
            self.assertEqual(report['state'],'insufficient_history')
            self.assertTrue((target/'effective-inputs.json').exists())
            with self.assertRaises(FileExistsError):research.evaluate_league([finished(1)],protocol,target)
            with self.assertRaises(ValueError):research.evaluate_league([],dict(protocol,lag_hours=0),Path(folder)/'invalid')
        self.assertFalse(research.assess_evidence(dict(operational_release=True,prospective_validation=True))['released'])

    def test_league_split_has_five_year_total_bound_and_label_lag(self):
        start=NOW.replace(year=2026,month=1,day=1,hour=0)
        rows=[dict(kickoff=(start-timedelta(days=d)).isoformat(),event_id=str(d)) for d in (0,1,20,800,1200,1900,2500)]
        train,cal=research.split_league(rows,start)
        self.assertTrue(all(start-timedelta(days=5*366)<=research.utc(r['kickoff']) for r in train+cal))
        self.assertTrue(all(research.utc(r['kickoff'])+timedelta(hours=24)<start-timedelta(hours=1) for r in cal))
        self.assertFalse(any(r['event_id']=='2500' for r in train+cal))

    def test_scoped_mapping_and_deterministic_history(self):
        rows=[finished(i,days=i+2) for i in range(1,15)]
        result,mapping=research.count_inputs(rows,{},NOW)
        self.assertEqual(result[0]['match_id'],mapping['event:'+result[0]['event_id']])
        self.assertEqual(research.count_inputs(rows,mapping,NOW)[1],mapping)
        self.assertTrue(all(type(r['home_id']) is int for r in result))
        with self.assertRaises(ValueError):research.count_inputs(rows+[finished(99,competition='other:1')],{},NOW)

    def test_future_inputs_unknown_labels_and_scores_are_not_training(self):
        rows=[finished(1,observed_at=(NOW+timedelta(hours=1)).isoformat()),finished(2,target=None),
              finished(3,days=0),finished(4,days=6*366)]
        self.assertEqual(research.count_inputs(rows,{},NOW,mode='observed')[0],[])
        with self.assertRaises(ValueError):research.count_inputs([finished(2,ht_home=0,target=1)],{},NOW)

    def test_missing_history_key_does_not_import_fabricated_data(self):
        with tempfile.TemporaryDirectory() as folder:
            db=connect_worldwide(Path(folder)/'w.sqlite')
            try:
                report=research.import_history(db,'football_data',dict(id=1),['2025'],None,NOW)
                self.assertEqual(report['state'],'missing_key')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
            finally:db.close()


if __name__=='__main__':unittest.main()
