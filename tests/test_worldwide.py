import unittest
from datetime import timedelta
from unittest.mock import patch
from tests.test_worldwide_store import NOW
import worldwide


def event(mid='fd:1',hours=2,**changes):
    return dict(dict(event_id=mid,provider='fd',competition_id='fd:1',country='Brazil',region='South America',
                competition='Serie A',home='Home',away='Away',kickoff=(NOW+timedelta(hours=hours)).isoformat(),
                status='SCHEDULED',classification='senior_real',probability=None,probability_state='unavailable',
                observed_at=NOW.isoformat()),**changes)


class WorldwideTests(unittest.TestCase):
    def test_today_tomorrow_status_freshness_and_unknown_classification(self):
        rows=[event(),event('fd:2',24),event('fd:3',status='POSTPONED'),
              event('fd:4',classification='unknown'),event('fd:5',observed_at=(NOW-timedelta(hours=1)).isoformat())]
        feed=dict(state='ready',events=rows)
        self.assertEqual([x['event_id'] for x in worldwide.select_fixtures([feed],NOW,'Today',[],[])],['fd:1'])
        self.assertEqual([x['event_id'] for x in worldwide.select_fixtures([feed],NOW,'Tomorrow',[],[])],['fd:2'])

    def test_scope_and_deduplication(self):
        rows=[event(),event(),event('other:1',competition_id='other:1',region='Europe')]
        self.assertEqual(len(worldwide.select_fixtures([dict(state='ready',events=rows)],NOW,'Today',[],[])),2)
        self.assertEqual(len(worldwide.select_fixtures([dict(state='ready',events=rows)],NOW,'Today',['South America'],[])),1)

    def test_top20_never_pads_or_includes_unreleased_and_groups_days(self):
        rows=[event(f'fd:{i}',probability=.7+i*.001,probability_state='released') for i in range(7)]
        rows+=[event('fd:99',probability=.99)]
        selected=worldwide.rank_estimates(rows,20)
        self.assertEqual(len(selected),7)
        self.assertEqual(selected[0]['event_id'],'fd:6')
        self.assertEqual(worldwide.rank_estimates([event()],20),[])

    def test_missing_keys_do_not_request_network(self):
        with patch('worldwide.catalog',return_value=dict(state='missing_key',competitions=[])) as cat:
            feeds=worldwide.collect_feeds({},NOW,NOW.date(),NOW.date(),None)
        self.assertEqual(len(feeds),2)
        self.assertTrue(all(f['state']=='missing_key' for f in feeds))


if __name__=='__main__': unittest.main()
