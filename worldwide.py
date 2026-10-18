"""Worldwide fixture discovery; no forecast release is implied by a feed."""
import math
from datetime import timedelta, timezone

from data import utc
from providers import catalog, fixtures

WAT=timezone(timedelta(hours=1))


def collect_feeds(tokens, now, start, end, db):
    feeds=[]
    for provider,secret in [('football_data','FOOTBALL_DATA_TOKEN'),('api_football','API_FOOTBALL_KEY')]:
        key=tokens.get(secret)
        inventory=catalog(provider,key,now,db)
        if inventory['state']!='ready':
            feeds.append(dict(provider=provider,state=inventory['state'],events=[],complete=False,reason=inventory['state']))
            continue
        competitions=inventory['competitions']
        reviewed=[c for c in competitions if c['classification']=='senior_real']
        if not reviewed:
            feeds.append(dict(provider=provider,state='classification_pending',events=[],complete=False,
                reason='Competition identities need review',catalog_count=len(competitions)))
            continue
        selected=fixtures(provider,key,start,end,reviewed,now,db)
        for feed in selected:
            feed['catalog_count']=len(competitions)
        feeds.extend(selected)
    return feeds


def bundesliga_feed(feed):
    events=[]
    for row in feed['matches']:
        event=dict(row,event_id=f'openligadb:{row["match_id"]}',provider='openligadb',source_event_id=row['match_id'],
            competition_id='openligadb:bl1',season_id=row['season'],country='Germany',region='Europe',competition='Bundesliga',
            home_id=f'openligadb:{row["home_id"]}',away_id=f'openligadb:{row["away_id"]}',
            status='FINISHED' if row['finished'] else 'SCHEDULED',classification='senior_real',
            observed_at=feed['observed_at'],source_url=feed['source_url'])
        events.append(event)
    return dict(provider='openligadb',state='ready',complete=True,events=events,observed_at=feed['observed_at'])


def select_fixtures(feeds, now, window, regions, competitions):
    now=utc(now);today=now.astimezone(WAT).date()
    rows={}
    for feed in feeds:
        if feed.get('state')!='ready':continue
        for row in feed['events']:
            kickoff=utc(row['kickoff'])
            if row.get('classification')!='senior_real' or row['status'] not in ('SCHEDULED','TIMED') or kickoff<=now:continue
            age=now-utc(row['observed_at'])
            if age<timedelta(0) or age>timedelta(minutes=10):continue
            if row['competition_id']=='football_data:2002' and any(f.get('state')=='ready' and f.get('provider')=='openligadb' for f in feeds):continue
            if regions and row['region'] not in regions:continue
            if competitions and row['competition_id'] not in competitions:continue
            day=kickoff.astimezone(WAT).date()
            if window in ('Today','Tomorrow'):
                if day!=today+timedelta(days=window=='Tomorrow'):continue
            elif not today<=day<=today+timedelta(days=6):continue
            result=dict(row,probability=None,probability_state='unavailable',probability_reason='league_model_unvalidated',
                        model_id=None,sample_sizes={},generated_at=None)
            rows[row['event_id']]=result
    return sorted(rows.values(),key=lambda r:(r['kickoff'],r['event_id']))


def rank_estimates(rows, limit):
    if limit not in (None,20,50):raise ValueError('Unsupported selection limit')
    eligible=[r for r in rows if r.get('probability_state')=='released'
              and type(r.get('probability')) in (int,float) and math.isfinite(r['probability']) and 0<=r['probability']<=1]
    days={}
    for row in eligible:
        days.setdefault(utc(row['kickoff']).astimezone(WAT).date(),{})[row['event_id']]=row
    result=[]
    for day,group in sorted(days.items()):
        ordered=sorted(group.values(),key=lambda r:(-r['probability'],r['kickoff'],r['event_id']))
        result.extend(ordered if limit is None else ordered[:limit])
    return result
