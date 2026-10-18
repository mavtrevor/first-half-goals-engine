"""Explicit worldwide historical research, never a live prediction release."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data import ROOT, utc
from providers import normalize_event, read_json
from worldwide_store import observations, save_feed


def import_history(db, provider, competition, season_ids, token, now):
    if not token:return dict(state='missing_key',seasons=[],imported=0)
    results=[];count=0
    for season in season_ids:
        if not str(season).isdecimal():raise ValueError('Invalid historical season')
        year=int(season)
        season_end=None
        season_metadata_hash=None
        if provider=='api_football':
            info,info_meta=read_json(provider,'/leagues',dict(id=competition['id'],season=year),token,now,db)
            try:
                if info is None:raise ValueError('Season metadata unavailable')
                if info.get('paging',{}).get('total',1)!=1:raise ValueError('Incomplete season metadata')
                leagues=[r for r in info['response'] if r['league']['id']==competition['id']]
                if len(leagues)!=1:raise ValueError('Ambiguous season competition')
                seasons=[s for s in leagues[0]['seasons'] if s['year']==year]
                if len(seasons)!=1 or not seasons[0].get('end'):raise ValueError('Missing requested season end')
                season_end=seasons[0]['end']
                datetime.fromisoformat(season_end)
                info_raw=json.dumps(info,sort_keys=True,allow_nan=False).encode()
                season_metadata_hash=hashlib.sha256(info_raw).hexdigest()
                save_feed(db,dict(provider=provider,state='ready',events=[],rejections=[],complete=True,
                    observed_at=info_meta.get('observed_at',utc(now).isoformat()),source_url=info_meta['source_url'],
                    snapshot_hash=season_metadata_hash),info_raw)
            except (ValueError,KeyError,TypeError,AttributeError):
                results.append(dict(season=year,state=info_meta.get('state','invalid_response') if info is None else 'season_metadata_unavailable'))
                continue
        path=f'/competitions/{competition["id"]}/matches' if provider=='football_data' else '/fixtures'
        params=dict(season=year,status='FINISHED' if provider=='football_data' else 'FT')
        if provider=='api_football':params['league']=competition['id']
        body,meta=read_json(provider,path,params,token,now,db)
        if body is None:
            results.append(dict(season=year,state=meta['state']));continue
        raw=json.dumps(body,sort_keys=True,allow_nan=False).encode();digest=hashlib.sha256(raw).hexdigest()
        observed=meta.get('observed_at',utc(now).isoformat())
        feed=dict(provider=provider,state='ready',events=[],rejections=[],complete=True,
                  observed_at=observed,snapshot_hash=digest,source_url=meta['source_url'])
        try:
            if body.get('paging',{}).get('total',1)!=1:raise ValueError('Incomplete history response')
            records=body['matches' if provider=='football_data' else 'response']
            if not isinstance(records,list):raise ValueError('Invalid history')
            for index,row in enumerate(records):
                try:
                    # Each historic response supplies the actual season identity; not today's catalog season.
                    sid=row['season']['id'] if provider=='football_data' else row['league']['season']
                    if provider=='football_data':
                        if int(row['season']['startDate'][:4])!=year:raise ValueError('History year mismatch')
                    elif sid!=year:raise ValueError('History year mismatch')
                    event=normalize_event(provider,row,observed,dict(competition,season_id=sid))
                    event.update(snapshot_hash=digest,source_url=meta['source_url'])
                    end=row.get('season',{}).get('endDate') if provider=='football_data' else season_end
                    event.update(season_year=year,season_metadata_hash=season_metadata_hash,season_complete=bool(end and
                        datetime.fromisoformat(end).replace(tzinfo=timezone.utc)+timedelta(days=1)<=utc(observed)))
                    feed['events'].append(event)
                except (KeyError,TypeError,ValueError,AttributeError):
                    rejected=dict(row_index=index,reason='invalid_historical_event')
                    if isinstance(row,dict):
                        mid=row.get('id') if provider=='football_data' else (row.get('fixture') or {}).get('id')
                        if type(mid) is int and mid>0:rejected['event_id']=f'{provider}:{mid}'
                    feed['rejections'].append(rejected)
            if len({r['event_id'] for r in feed['events']})!=len(feed['events']):raise ValueError('Duplicate history')
            feed['complete']=not feed['rejections']
        except (KeyError,TypeError,ValueError,AttributeError):
            feed.update(state='invalid_response',complete=False,events=[])
        if not feed['complete']:
            for row in feed['events']:row['quality']='incomplete_source'
        save_feed(db,feed,raw)
        count+=len(feed['events'])
        results.append(dict(season=year,state='ready' if feed['complete'] else 'incomplete',matches=len(feed['events'])))
    return dict(state='ready' if results and all(r['state']=='ready' for r in results) else 'incomplete_history',seasons=results,imported=count)


def league_rows(db, competition_id, cutoff, mode):
    if mode not in ('retrospective','observed'):raise ValueError('Invalid availability mode')
    as_of=utc(cutoff) if mode=='observed' else datetime.max.replace(tzinfo=timezone.utc)
    return observations(db,competition_id,as_of)


def _mapped_inputs(rows, identity_map):
    if len({r['competition_id'] for r in rows})>1:raise ValueError('Mixed league history')
    if len({r['event_id'] for r in rows})!=len(rows):raise ValueError('Duplicate effective history')
    mapping=dict(identity_map)
    if len(set(mapping.values()))!=len(mapping) or any(type(v) is not int or v<=0 for v in mapping.values()):
        raise ValueError('Invalid stable identity map')
    keys={('event:' if k=='event_id' else 'team:')+r[k] for r in rows for k in ('event_id','home_id','away_id')}
    for key in sorted(keys):
        if key not in mapping:mapping[key]=max(mapping.values(),default=0)+1
    result=[]
    for row in sorted(rows,key=lambda r:(r['kickoff'],r['event_id'])):
        if row.get('target') is None or row.get('status')!='FINISHED' or row.get('quality')!='structurally_valid':continue
        h,a=row['ht_home'],row['ht_away']
        if any(type(v) is not int or v<0 for v in (h,a)) or type(row['target']) is not int or row['target']!=int(h+a>0):
            raise ValueError('Target and explicit HT scores disagree')
        if row['home_id']==row['away_id'] or not row.get('snapshot_hash'):raise ValueError('Invalid identity/provenance')
        kickoff=utc(row['kickoff'])
        result.append(dict(row,match_id=mapping['event:'+row['event_id']],home_id=mapping['team:'+row['home_id']],
            away_id=mapping['team:'+row['away_id']],source_home_id=row['home_id'],source_away_id=row['away_id'],
            cutoff=(kickoff-timedelta(minutes=60)).isoformat(),season=row['season_id']))
    return result,mapping


def count_inputs(rows, identity_map, cutoff, mode='retrospective'):
    cutoff=utc(cutoff)
    if mode not in ('retrospective','observed'):raise ValueError('Invalid availability mode')
    mapped,mapping=_mapped_inputs(rows,identity_map)
    return [r for r in mapped if cutoff-timedelta(days=5*366)<=utc(r['kickoff'])
            and utc(r['kickoff'])+timedelta(hours=24)<cutoff
            and (mode=='retrospective' or utc(r['observed_at'])<=cutoff)],mapping


def split_league(rows, start):
    start=utc(start)
    cal_start=start.replace(year=start.year-2)
    first=start.replace(year=start.year-5)
    return ([r for r in rows if first<=utc(r['kickoff']) and utc(r['kickoff'])+timedelta(hours=24)<cal_start-timedelta(hours=1)],
            [r for r in rows if cal_start<=utc(r['kickoff']) and utc(r['kickoff'])+timedelta(hours=24)<start-timedelta(hours=1)])


def _eligible(rows):
    eligible=[]
    for row in rows:
        cutoff=utc(row['cutoff'])
        history=[r for r in rows if cutoff-timedelta(days=5*366)<=utc(r['kickoff'])
                 and utc(r['kickoff'])+timedelta(hours=24)<cutoff]
        if all(sum(team in (r['home_id'],r['away_id']) for r in history)>=10 for team in (row['home_id'],row['away_id'])):
            eligible.append(row)
    return eligible


def _evaluate_period(all_rows, eligible, year, alpha, calibration):
    from poisson_model import fit_counts,predict_counts
    from sklearn.exceptions import ConvergenceWarning
    predictions=[];folds=[]
    test=[r for r in eligible if r.get('season_year')==year]
    months=sorted({utc(r['kickoff']).replace(day=1,hour=0,minute=0,second=0,microsecond=0) for r in test})
    for start in months:
        cohort=[r for r in test if utc(r['kickoff']).year==start.year and utc(r['kickoff']).month==start.month]
        train,cal=split_league(eligible,start)
        try:
            pair=fit_counts(train,cal,alpha,calibration)
            for row in cohort:
                estimate=predict_counts(pair,row)
                history=[r for r in all_rows if utc(row['cutoff'])-timedelta(days=5*366)<=utc(r['kickoff'])
                         and utc(r['kickoff'])+timedelta(hours=24)<utc(row['cutoff'])]
                baseline=(sum(r['target'] for r in history)+1)/(len(history)+2)
                predictions.append(dict(event_id=row['event_id'],match_id=row['match_id'],kickoff=row['kickoff'],
                    cutoff=row['cutoff'],target=row['target'],p=estimate['calibrated_p'],baseline=baseline,
                    model_id=pair['model_id'],unseen_teams=estimate['unseen_teams']))
            folds.append(dict(month=start.isoformat(),state='complete',count=len(cohort)))
        except (ValueError,ConvergenceWarning,ArithmeticError):
            folds.append(dict(month=start.isoformat(),state='fit_unavailable',count=0))
    return dict(predictions=predictions,folds=folds,expected_count=len(test),
                complete=bool(test) and len(predictions)==len(test) and all(f['state']=='complete' for f in folds))


def assess_evidence(report):
    return dict(released=False,reason='prospective_confirmatory_protocol_and_evidence_pending',
                retrospective_state=report.get('state','unknown'))


def evaluate_league(rows, protocol, output):
    from backtest import summarize
    digest=hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest()
    if digest!='f605921135d5342e8f8fd27796c5f51c8917c6635aaedb21a45cb94cdd13e95b':
        raise ValueError('Unsupported or changed worldwide protocol')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    raw=json.dumps(sorted(rows,key=lambda r:r['event_id']),sort_keys=True,allow_nan=False).encode()
    (output/'effective-inputs.json').write_bytes(raw)
    source=output/'source-code';source.mkdir()
    hashes={}
    for path in [ROOT/n for n in ('worldwide_research.py','poisson_model.py','model.py','backtest.py','data.py')]+[ROOT/'config/worldwide-protocol.json']:
        name=path.name;payload=path.read_bytes();(source/name).write_bytes(payload)
        hashes[name]=hashlib.sha256(payload).hexdigest()
    manifest=dict(protocol=protocol,protocol_sha256=hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest(),
        effective_inputs_sha256=hashlib.sha256(raw).hexdigest(),code_sha256=hashes,created_at=datetime.now(timezone.utc).isoformat())
    (output/'run-manifest.json').write_text(json.dumps(manifest,indent=2))
    mapped,mapping=_mapped_inputs(rows,{})
    (output/'identity-map.json').write_text(json.dumps(mapping,sort_keys=True))
    eligible=_eligible(mapped)
    seasons=sorted({r['season_year'] for r in mapped if r.get('season_complete') is True and type(r.get('season_year')) is int})
    report=dict(state='insufficient_history',operational_release=False,availability='retrospective_reconstruction',
        competition_id=rows[0]['competition_id'] if rows else None,eligible_rows=len(eligible),
        excluded_rows=len(rows)-len(eligible),protocol_sha256=manifest['protocol_sha256'],selection=None,predictions=[])
    if len(seasons)>=2:
        inner,outer=seasons[-2:]
        (output/'period-seal.json').write_text(json.dumps(dict(inner=inner,outer=outer,status='exploratory_not_untouched')))
        candidates=[]
        for alpha in protocol['alpha_grid']:
            for method in protocol['calibration_candidates']:
                result=_evaluate_period(mapped,eligible,inner,alpha,method)
                score=summarize(result['predictions'])
                candidates.append(dict(alpha=alpha,calibration=method,complete=result['complete'],
                    summary=score,folds=result['folds']))
        valid=[r for r in candidates if r['complete']]
        (output/'inner-candidates.json').write_text(json.dumps(candidates,allow_nan=False,indent=2))
        if valid:
            selected=min(valid,key=lambda r:(r['summary']['log_loss'],-r['alpha'],r['calibration']!='identity'))
            seal=dict(inner=inner,outer=outer,alpha=selected['alpha'],calibration=selected['calibration'])
            (output/'selection.json').write_text(json.dumps(seal,sort_keys=True))
            result=_evaluate_period(mapped,eligible,outer,seal['alpha'],seal['calibration'])
            predictions=result['predictions']
            from worldwide import rank_estimates
            ranked=rank_estimates([dict(r,probability=r['p'],probability_state='released') for r in predictions],20)
            report.update(state='retrospective_exploratory',selection=seal,predictions=predictions,
                folds=result['folds'],complete=result['complete'],summary=summarize(predictions),
                daily_top20=summarize(ranked),daily_top20_count=len(ranked))
    report['evidence']=assess_evidence(report)
    (output/'report.json').write_text(json.dumps(report,allow_nan=False,indent=2))
    manifest['report_sha256']=hashlib.sha256((output/'report.json').read_bytes()).hexdigest()
    (output/'run-manifest.json').write_text(json.dumps(manifest,indent=2))
    return report


def shadow_league(db, competition_id, report, now):
    from poisson_model import fit_counts
    from worldwide_forecasts import record_shadow
    if report.get('competition_id')!=competition_id or not report.get('selection'):
        raise ValueError('A sealed league-specific research selection is required')
    rows=league_rows(db,competition_id,now,'observed')
    history,mapping=count_inputs(rows,{},now,mode='observed')
    eligible=_eligible(history)
    train,cal=split_league(eligible,utc(now).replace(day=1,hour=0,minute=0,second=0,microsecond=0))
    selection=report['selection']
    try:pair=fit_counts(train,cal,selection['alpha'],selection['calibration'])
    except ValueError:pair=None
    records=[]
    for event in rows:
        if event['status'] not in ('SCHEDULED','TIMED'):continue
        if not 55<=(utc(event['kickoff'])-utc(now)).total_seconds()/60<=65:continue
        inputs=dict(event_id=event['event_id'],match_id=mapping['event:'+event['event_id']],
            home_id=mapping['team:'+event['home_id']],away_id=mapping['team:'+event['away_id']],
            source_home_id=event['home_id'],source_away_id=event['away_id'],kickoff=event['kickoff'],
            cutoff=utc(now).isoformat(),fixture_hash=event['snapshot_hash'],
            home_history=sum(event['home_id'] in (r['source_home_id'],r['source_away_id']) for r in history),
            away_history=sum(event['away_id'] in (r['source_home_id'],r['source_away_id']) for r in history),
            input_hashes=sorted({r['snapshot_hash'] for r in history}),
            maximum_observed_at=max([event['observed_at']]+[r['observed_at'] for r in history]))
        records.append(record_shadow(db,event,pair,inputs,now))
    return records


def main():
    import argparse
    import os
    import re
    import tomllib
    from providers import catalog
    from worldwide_store import connect_worldwide
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['catalog','import-history','evaluate','shadow'])
    parser.add_argument('--provider',choices=['football_data','api_football'],default='football_data')
    parser.add_argument('--competition',type=int)
    parser.add_argument('--seasons',nargs='+',default=[])
    parser.add_argument('--run',default='worldwide-v1')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.run):parser.error('Use a simple unique run name')
    if args.command!='catalog' and not args.competition:parser.error('--competition is required')
    now=datetime.now(timezone.utc);folder=ROOT/'data';folder.mkdir(exist_ok=True)
    db=connect_worldwide(folder/'worldwide.sqlite')
    try:
        cid=f'{args.provider}:{args.competition}'
        output=folder/'reports/worldwide'/args.run
        if args.command in ('catalog','import-history'):
            name='FOOTBALL_DATA_TOKEN' if args.provider=='football_data' else 'API_FOOTBALL_KEY'
            secret_file=ROOT/'.streamlit/secrets.toml'
            local=tomllib.loads(secret_file.read_text()) if secret_file.exists() else {}
            token=os.environ.get(name) or local.get(name)
            inventory=catalog(args.provider,token,now,db)
            if args.command=='catalog':result=inventory
            elif inventory['state']!='ready':result=dict(state=inventory['state'])
            else:
                competition=next((c for c in inventory['competitions'] if c['id']==args.competition and c['classification']=='senior_real'),None)
                if not competition:result=dict(state='reviewed_competition_unavailable')
                elif not args.seasons:parser.error('--seasons is required for import-history')
                else:result=import_history(db,args.provider,competition,args.seasons,token,now)
        elif args.command=='evaluate':
            rows=league_rows(db,cid,now,'retrospective')
            result=evaluate_league(rows,json.loads((ROOT/'config/worldwide-protocol.json').read_text()),output)
            result={k:result[k] for k in ('state','competition_id','operational_release','eligible_rows','evidence')}
        else:
            report=json.loads((output/'report.json').read_text())
            result=dict(state='shadow_only',records=len(shadow_league(db,cid,report,now)))
        print(json.dumps(result,indent=2,allow_nan=False))
    finally:db.close()


if __name__=='__main__':main()
