import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from tests.test_worldwide_store import NOW
from worldwide_store import connect_worldwide
import providers


def fd_match():
    return dict(id=10, competition=dict(id=2013),season=dict(id=9),
        homeTeam=dict(id=1,name='Home'), awayTeam=dict(id=2,name='Away'),
        utcDate='2026-10-17T16:00:00Z',status='FINISHED',
        score=dict(duration='REGULAR',halfTime=dict(home=0,away=0),fullTime=dict(home=1,away=0)))


META = dict(id=2013,season_id=9,country='Brazil',region='South America',classification='senior_real',name='Serie A')


class Response(io.BytesIO):
    headers = {'X-RequestsAvailable':'8','X-RequestCounter-Reset':'60'}


class ProviderTests(unittest.TestCase):
    def test_real_football_data_quota_header_spelling(self):
        allowance=providers._allowance('football_data',{'X-Requests-Available':'9','X-RequestCounter-Reset':'60'},NOW)
        self.assertEqual(allowance['remaining'],9)
        self.assertEqual(allowance['minute_limit'],10)

    def test_http_access_and_quota_errors_never_echo_tokens(self):
        for code,state in [(401,'access_denied'),(403,'access_denied'),(429,'quota_exhausted')]:
            token='PRIVATE_TOKEN_'+str(code)
            error=HTTPError('https://api.football-data.org/v4/competitions',code,token,{'Retry-After':'600'},io.BytesIO(token.encode()))
            with patch('providers.OPENER.open',side_effect=error) as opening:
                result=providers.read_json('football_data','/competitions',{},token,NOW,self.db)
                repeat=providers.read_json('football_data','/competitions',{},token,NOW,self.db)
            self.assertEqual(result[1]['state'],state)
            self.assertEqual(result,repeat)
            self.assertEqual(opening.call_count,1)
            self.assertNotIn(token,json.dumps(result))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect_worldwide(Path(self.temp.name)/'w.sqlite')
        self.addCleanup(self.db.close)

    def test_missing_token_makes_no_request(self):
        with patch('providers.OPENER.open') as opening:
            self.assertEqual(providers.catalog('football_data',None,NOW,self.db)['state'],'missing_key')
        opening.assert_not_called()

    def test_null_and_explicit_zero_halves_and_bad_structures(self):
        raw=fd_match()
        self.assertEqual(providers.normalize_event('football_data',raw,NOW,META)['target'],0)
        raw['score']['halfTime']['home']=None
        self.assertIsNone(providers.normalize_event('football_data',raw,NOW,META)['target'])
        for mutation in ('bool','negative','naive','league','season','team'):
            raw=fd_match()
            if mutation=='bool':raw['score']['halfTime']['home']=True
            if mutation=='negative':raw['score']['halfTime']['home']=-1
            if mutation=='naive':raw['utcDate']='2026-10-17T16:00:00'
            if mutation=='league':raw['competition']['id']=9
            if mutation=='season':raw['season']['id']=1
            if mutation=='team':raw['homeTeam']=None
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                providers.normalize_event('football_data',raw,NOW,META)

    def test_response_errors_are_sanitized_and_failures_cached(self):
        for errors,state in [({'plan':'TOKEN_SECRET not allowed for season'},'season_unavailable'),
                             ({'token':'TOKEN_SECRET invalid'},'access_denied')]:
            with patch('providers.OPENER.open',return_value=Response(json.dumps(dict(errors=errors)).encode())):
                payload,meta=providers.read_json('api_football','/status',{},'TOKEN_SECRET',NOW,self.db)
            self.assertIsNone(payload)
            self.assertEqual(meta['state'],state)
            self.assertNotIn('TOKEN_SECRET',json.dumps(meta))
            # Different key fingerprint for the next independent case.
            self.db.execute('DELETE FROM api_cache');self.db.execute('DELETE FROM budgets');self.db.execute('DELETE FROM requests');self.db.commit()

    def test_fixed_hosts_no_redirects_and_valid_cache(self):
        with self.assertRaises(ValueError):
            providers.read_json('football_data','https://evil.test',{},'secret',NOW,self.db)
        response=Response(json.dumps(dict(competitions=[])).encode())
        with patch('providers.OPENER.open',return_value=response) as opening:
            one=providers.read_json('football_data','/competitions',{},'secret',NOW,self.db)
            two=providers.read_json('football_data','/competitions',{},'secret',NOW,self.db)
        self.assertEqual(one,two)
        self.assertEqual(opening.call_count,1)
        self.assertEqual(opening.call_args.kwargs['timeout'],15)
        self.assertIsNone(providers.NO_REDIRECT.redirect_request(None,None,302,'',{},'https://evil.test'))

    def test_partial_and_quarantined_fixtures_are_not_complete(self):
        response=dict(matches=[fd_match(),dict(fd_match(),id=11,homeTeam=None)])
        with patch('providers.read_json',return_value=(response,dict(state='ready',source_url='https://api.football-data.org/v4/matches'))):
            feed=providers.fixtures('football_data','secret',NOW.date(),NOW.date(),[META],NOW,self.db)[0]
        self.assertFalse(feed['complete'])
        self.assertEqual(len(feed['rejections']),1)
        self.assertEqual(len(feed['events']),1)

    def test_statuses_remain_explicit_not_all_unfinished_are_scheduled(self):
        for status in ('IN_PLAY','POSTPONED','CANCELLED','AWARDED','SUSPENDED'):
            self.assertEqual(providers.normalize_event('football_data',dict(fd_match(),status=status),NOW,META)['status'],status)


if __name__=='__main__': unittest.main()
