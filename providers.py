"""Documented read-only providers. Credentials never enter public feed records."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from data import ROOT, positive_id, utc
from worldwide_store import reserve_request, save_feed

CONFIG = json.loads((ROOT/'config/worldwide-sources.json').read_text())
HOSTS = {'football_data':'https://api.football-data.org/v4', 'api_football':'https://v3.football.api-sports.io'}
MAX_BYTES = 2_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


NO_REDIRECT = NoRedirect()
OPENER = build_opener(NO_REDIRECT)


def region(country):
    return next((name for name,countries in CONFIG['regions'].items() if country in countries),'Other / unreviewed')


def classify_api_league(raw):
    identity=str(raw['league']['id'])
    evidence=CONFIG.get('reviewed_identity_evidence',{}).get(identity,{})
    if (evidence.get('country')==raw['country']['name'] and evidence.get('name')==raw['league']['name']
        and raw['league'].get('type')=='League' and evidence.get('official_url','').startswith('https://')):
        return CONFIG['reviewed_api_football_competitions'].get(identity,'unknown')
    return 'unknown'


def _scope(provider, token):
    return provider+':'+hashlib.sha256(token.encode()).hexdigest()


def _error(state, url=''):
    return None, dict(state=state,source_url=url,reason=state,quota={})


def _allowance(provider, headers, now):
    headers={k.lower():v for k,v in headers.items()}
    try:
        if provider=='football_data':
            remaining=min(int(headers[k]) for k in ('x-requests-available-minute','x-requests-available','x-requestsavailable') if k in headers)
            reset=now+timedelta(seconds=max(1,int(headers['x-requestcounter-reset'])))
            limit,reserve=10,0
        else:
            remaining=int(headers['x-ratelimit-requests-remaining'])
            # Provider daily quota resets at UTC midnight; also respect its minute allowance.
            reset=(now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            limit=min(10,int(headers['x-ratelimit-remaining']))
            reserve=10
        if remaining<0 or limit<0: return {}
        return dict(remaining=remaining,reset_at=reset.isoformat(),observed_at=now.isoformat(),minute_limit=limit,reserve=reserve)
    except (KeyError,TypeError,ValueError):
        return {}


def read_json(provider, path, params, token, now, db):
    now=utc(now)
    allowed = r'/(competitions(?:/\d+(?:/matches)?)?|matches)' if provider=='football_data' else r'/(status|leagues|fixtures)'
    if provider not in HOSTS or not re.fullmatch(allowed,path):
        raise ValueError('Unsupported documented endpoint')
    if not token: return _error('missing_key')
    if not isinstance(token,str) or len(token)>512 or any(c.isspace() for c in token):
        return _error('access_denied')
    url=HOSTS[provider]+path+('?' + urlencode(sorted(params.items())) if params else '')
    scope=_scope(provider,token)
    key=hashlib.sha256((scope+url+':quota-headers-v3').encode()).hexdigest()
    db.execute('CREATE TABLE IF NOT EXISTS api_cache (key TEXT PRIMARY KEY, expires TEXT, record TEXT)')
    stored=db.execute('SELECT record FROM budgets WHERE provider=?',(scope,)).fetchone()
    allowance=json.loads(stored[0]) if stored else {}
    bootstrap=path==('/competitions' if provider=='football_data' else '/status')
    cached=db.execute('SELECT expires,record FROM api_cache WHERE key=?',(key,)).fetchone()
    if cached and utc(cached['expires'])>now:
        result=tuple(json.loads(cached['record']))
        if result[1]['state']!='ready' or not bootstrap or (allowance and utc(allowance['reset_at'])>now):
            return result
    def cache(result, seconds=300):
        with db:
            db.execute('INSERT OR REPLACE INTO api_cache VALUES(?,?,?)',
                (key,(now+timedelta(seconds=seconds)).isoformat(),json.dumps(result,allow_nan=False)))
        return result
    if allowance and allowance.get('minute_limit')==0 and utc(allowance['reset_at'])>now:
        return cache(_error('quota_exhausted',url),max(1,int((utc(allowance['reset_at'])-now).total_seconds())))
    if bootstrap:
        permit=reserve_request(db,scope+':handshake',now,dict(remaining=1,reset_at=(now+timedelta(minutes=1)).isoformat(),
                    observed_at=now.isoformat(),minute_limit=1,reserve=0))
    else:
        permit=reserve_request(db,scope,now,allowance)
    if not permit:
        result=_error('quota_exhausted' if allowance else 'quota_unknown',url)
        result[1]['quota']={k:allowance[k] for k in ('remaining','reset_at','reserve','minute_limit') if k in allowance}
        return cache(result)
    header='X-Auth-Token' if provider=='football_data' else 'x-apisports-key'
    request=Request(url,headers={header:token,'Accept':'application/json',
        'User-Agent':'FirstHalfGoalsEngine/2.0 (+https://github.com/mavtrevor/first-half-goals-engine)'})
    try:
        with OPENER.open(request,timeout=15) as response:
            quota=_allowance(provider,response.headers,now)
            quota_diagnostic={k.lower():int(v) if str(v).isdecimal() else 'non-numeric'
                for k,v in response.headers.items() if k.lower() in
                ('x-requests-available-minute','x-requests-available','x-requestsavailable','x-requestcounter-reset',
                 'x-ratelimit-requests-remaining','x-ratelimit-remaining')}
            payload=response.read(MAX_BYTES+1)
        if len(payload)>MAX_BYTES: return cache(_error('invalid_response',url))
        body=json.loads(payload.decode('utf-8-sig'))
        if not isinstance(body,dict): return cache(_error('invalid_response',url))
        if quota:
            # Atomic spending remains in reserve_request; a lower server balance wins.
            with db:
                db.execute('BEGIN IMMEDIATE')
                local=db.execute('SELECT record FROM budgets WHERE provider=?',(scope,)).fetchone()
                if local:
                    previous=json.loads(local[0])
                    if utc(previous['reset_at'])>now:
                        quota['remaining']=min(quota['remaining'],previous['remaining'])
                db.execute('INSERT OR REPLACE INTO budgets VALUES(?,?)',(scope,json.dumps(quota)))
        errors=body.get('errors')
        if errors:
            # Inspect for classification only. Never log/cache a provider's raw error text.
            words=json.dumps(errors).lower()
            state='season_unavailable' if 'season' in words or 'plan' in words else 'access_denied'
            return cache(_error(state,url))
        if bootstrap and provider=='api_football':
            subscription=body.get('response',{}).get('subscription',{})
            if subscription.get('plan')!='Free' or subscription.get('active') is not True:
                return cache(_error('access_denied',url))
            body={'response':{'subscription':{'plan':'Free','active':True}}}
        if not quota:
            return cache((None,dict(_error('quota_unknown',url)[1],quota_diagnostic=quota_diagnostic)))
        meta=dict(state='ready',source_url=url,quota=quota,reason='',observed_at=now.isoformat())
        duration=86400 if path.startswith(('/competitions','/leagues')) and not path.endswith('/matches') else 300
        if provider=='api_football' and path=='/status':
            duration=max(1,int((utc(quota['reset_at'])-now).total_seconds()))
        if params.get('status')=='FINISHED': duration=86400
        return cache((body,meta),duration)
    except HTTPError as exc:
        state={401:'access_denied',403:'access_denied',429:'quota_exhausted'}.get(exc.code,'source_unavailable')
        delay=300
        retry=exc.headers.get('Retry-After','') if exc.headers else ''
        try: delay=max(delay,int(retry))
        except ValueError:
            from email.utils import parsedate_to_datetime
            try: delay=max(delay,int((parsedate_to_datetime(retry)-now).total_seconds()))
            except (ValueError,TypeError): pass
        # Set a provider-wide cooldown: changing filters must not bypass an HTTP quota response.
        if exc.code==429:
            with db:
                db.execute('INSERT OR REPLACE INTO budgets VALUES(?,?)',(scope,json.dumps(dict(remaining=0,
                    reset_at=(now+timedelta(seconds=delay)).isoformat(),observed_at=now.isoformat(),minute_limit=0))))
        exc.close()
        return cache(_error(state,url),delay)
    except (OSError,ValueError,TypeError,AttributeError):
        return cache(_error('source_unavailable',url))


def catalog(provider, token, now, db):
    if provider=='api_football':
        _,status=read_json(provider,'/status',{},token,now,db)
        if status['state']!='ready': return dict(status,competitions=[])
    body,meta=read_json(provider,'/competitions' if provider=='football_data' else '/leagues',
                        {} if provider=='football_data' else {'current':'true'},token,now,db)
    if body is None: return dict(meta,competitions=[])
    competitions=[]
    try:
        for raw in body['competitions' if provider=='football_data' else 'response']:
            if provider=='football_data':
                if raw.get('code') not in CONFIG['football_data_codes']: continue
                sid=positive_id(raw['currentSeason']['id'])
                item=dict(id=positive_id(raw['id']),name=raw['name'],code=raw['code'],season_id=sid,
                    season_year=int(raw['currentSeason']['startDate'][:4]),country=raw['area']['name'],classification='senior_real')
            else:
                seasons=[s for s in raw['seasons'] if s.get('current') is True]
                if len(seasons)!=1: continue
                classification=classify_api_league(raw)
                item=dict(id=positive_id(raw['league']['id']),name=raw['league']['name'],code='',
                    season_id=positive_id(seasons[0]['year']),season_year=seasons[0]['year'],
                    country=raw['country']['name'],classification=classification,competition_type=raw['league']['type'],
                    season_start=seasons[0].get('start'),season_end=seasons[0].get('end'))
            item.update(provider=provider,region=region(item['country']))
            competitions.append(item)
        if provider=='api_football' and body.get('paging',{}).get('total',1)!=1:
            return dict(_error('invalid_response')[1],competitions=[])
        return dict(meta,competitions=competitions)
    except (ValueError,KeyError,TypeError,AttributeError):
        return dict(_error('invalid_response')[1],competitions=[])


def normalize_event(provider, raw, observed_at, metadata):
    try:
        if provider=='football_data':
            mid,cid,sid=raw['id'],raw['competition']['id'],raw['season']['id']
            home,away=raw['homeTeam'],raw['awayTeam']
            kickoff,status=raw['utcDate'],raw['status']
            score=raw['score']; ht=score.get('halfTime') or {}; ft=score.get('fullTime') or {}
            h,a,fh,fa=ht.get('home'),ht.get('away'),ft.get('home'),ft.get('away')
            duration=score.get('duration')
        else:
            mid,cid,sid=raw['fixture']['id'],raw['league']['id'],raw['league']['season']
            home,away=raw['teams']['home'],raw['teams']['away']
            kickoff=raw['fixture']['date']; code=raw['fixture']['status']['short']
            status={'NS':'SCHEDULED','TBD':'UNCONFIRMED','FT':'FINISHED','AET':'FINISHED',
                'PEN':'FINISHED','PST':'POSTPONED','CANC':'CANCELLED','ABD':'ABANDONED','AWD':'AWARDED','WO':'AWARDED'}.get(code,'IN_PLAY')
            ht=raw['score'].get('halftime') or {}; ft=raw['score'].get('fulltime') or {}
            h,a,fh,fa=ht.get('home'),ht.get('away'),ft.get('home'),ft.get('away')
            duration='REGULAR' if code=='FT' else code
        if cid!=metadata['id'] or sid!=metadata['season_id']: raise ValueError('Scope mismatch')
        for identity in (mid,cid,sid,home['id'],away['id']):positive_id(identity)
        if home['id']==away['id']:raise ValueError('Same team')
        for team in (home,away):
            if not isinstance(team['name'],str) or not 1<=len(team['name'].strip())<=150:raise ValueError('Invalid team')
        for number in (h,a,fh,fa):
            if number is not None and (type(number) is not int or number<0):raise ValueError('Invalid score')
        if all(v is not None for v in (h,a,fh,fa)) and (h>fh or a>fa):raise ValueError('Invalid halftime')
        kickoff=utc(kickoff)
        if status=='FINISHED' and kickoff>=utc(observed_at):raise ValueError('Future completed game')
        usable=status=='FINISHED' and duration=='REGULAR' and all(v is not None for v in (h,a,fh,fa))
        return dict(event_id=f'{provider}:{mid}',provider=provider,source_event_id=mid,
            competition_id=f'{provider}:{cid}',season_id=sid,country=metadata['country'],region=metadata['region'],
            competition=metadata['name'],home_id=f'{provider}:{home["id"]}',away_id=f'{provider}:{away["id"]}',
            home=home['name'],away=away['name'],kickoff=kickoff.isoformat(),status=status,
            ht_home=h if usable else None,ht_away=a if usable else None,ft_home=fh,ft_away=fa,
            target=int(h+a>0) if usable else None,observed_at=utc(observed_at).isoformat(),
            classification=metadata['classification'],quality='structurally_valid' if usable else 'fixture_only')
    except (KeyError,TypeError,AttributeError) as exc:
        raise ValueError('Malformed provider event') from exc


def fixtures(provider, token, start, end, competitions, now, db):
    if not token:return [dict(_error('missing_key')[1],provider=provider,events=[],rejections=[],complete=False)]
    if end<start or (end-start).days>8:raise ValueError('Requested range exceeds supported eight-day window')
    lookup={c['id']:c for c in competitions}
    queries=[('/matches',dict(dateFrom=start.isoformat(),dateTo=end.isoformat(),competitions=','.join(map(str,lookup))))] if provider=='football_data' else [
        ('/fixtures',dict(date=(start+timedelta(days=i)).isoformat(),timezone='UTC')) for i in range((end-start).days+1)]
    feeds=[]
    for path,params in queries:
        body,meta=read_json(provider,path,params,token,now,db)
        observed=meta.get('observed_at',utc(now).isoformat())
        feed=dict(meta,provider=provider,events=[],rejections=[],complete=body is not None,observed_at=observed)
        if body is None:feeds.append(feed);continue
        raw=json.dumps(body,sort_keys=True,allow_nan=False).encode()
        digest=hashlib.sha256(raw).hexdigest()
        feed['snapshot_hash']=digest
        try:
            if body.get('paging',{}).get('total',1)!=1:raise ValueError('Partial response requires bounded pagination')
            records=body['matches' if provider=='football_data' else 'response']
            if not isinstance(records,list):raise ValueError('Invalid match collection')
            seen=set()
            for row in records:
                try:
                    cid=row['competition' if provider=='football_data' else 'league']['id']
                    if cid not in lookup:continue
                    event=normalize_event(provider,row,observed,lookup[cid])
                    if event['event_id'] in seen:raise ValueError('Duplicate identity')
                    seen.add(event['event_id'])
                    event.update(snapshot_hash=digest,source_url=meta['source_url'])
                    feed['events'].append(event)
                except (ValueError,KeyError,TypeError,AttributeError):
                    rejected=dict(row_index=len(seen),reason='invalid_event')
                    if isinstance(row,dict):
                        mid=row.get('id') if provider=='football_data' else (row.get('fixture') or {}).get('id')
                        if type(mid) is int and mid>0:rejected['event_id']=f'{provider}:{mid}'
                    feed['rejections'].append(rejected)
            rejected_ids={r.get('event_id') for r in feed['rejections']}
            feed['events']=[r for r in feed['events'] if r['event_id'] not in rejected_ids]
            feed['complete']=not feed['rejections']
        except (ValueError,KeyError,TypeError,AttributeError):
            feed.update(state='invalid_response',complete=False,reason='invalid_or_partial_response',events=[])
        save_feed(db,feed,raw)
        feeds.append(feed)
    return feeds
