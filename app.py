"""Local research interface. External operator actions are always human-operated."""
import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from data import ROOT, connect, latest_matches, utc
from live import fetch_season, recent_halves, season_for, upcoming_matches
from observations import MARKET, observation_state, record_booking, record_observation
from worldwide import bundesliga_feed, collect_feeds, rank_estimates, select_fixtures
from worldwide_store import connect_worldwide

WAT = timezone(timedelta(hours=1), 'WAT')
DATA_DIR = Path(os.environ.get('FH_ENGINE_DATA_DIR', ROOT/'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def wat(value):
    return utc(value).astimezone(WAT).strftime('%d %b %Y, %H:%M WAT')


def csv_bytes(rows):
    if not rows:
        return b''
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        # Prevent spreadsheet formulas in human-entered export fields.
        writer.writerow({k: "'"+v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v
                         for k, v in row.items()})
    return output.getvalue().encode('utf-8-sig')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else None


@st.cache_data(ttl=300, show_spinner=False, max_entries=2)
def live_feed(season):
    # Cache failures too: reruns must not hammer the community API.
    try:
        return fetch_season(season), None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return None, f'{type(exc).__name__}: {str(exc)[:180]}'


def research_report(relative):
    return read_json(DATA_DIR/relative) or read_json(ROOT/'evidence'/relative)


def provider_tokens():
    tokens={}
    for name in ('FOOTBALL_DATA_TOKEN','API_FOOTBALL_KEY'):
        value=os.environ.get(name)
        if not value:
            try:
                value=st.secrets.get(name)
            except (FileNotFoundError,KeyError):
                value=None
        if value: tokens[name]=value
    return tokens


def show_finder(feed, enabled, now):
    st.subheader('Find games worldwide')
    horizon=st.selectbox('When (Nigeria time)',['Today','Tomorrow','Next 7 days'])
    view=st.selectbox('Show',['All fixtures','Eligible estimates'])
    limit_label=st.selectbox('Selection limit',['Top 20','Top 50','All eligible'])
    limit={'Top 20':20,'Top 50':50,'All eligible':None}[limit_label]
    st.button('Check fixtures again',help='Respects shared source caching and request allowances.')
    feeds=[bundesliga_feed(feed)] if feed else []
    tokens=provider_tokens()
    world_db=connect_worldwide(DATA_DIR/'worldwide.sqlite')
    try:
        day=now.astimezone(WAT).replace(hour=0,minute=0,second=0,microsecond=0)
        if horizon=='Tomorrow':day+=timedelta(days=1)
        end=day+timedelta(days=7 if horizon=='Next 7 days' else 1)
        if enabled:
            feeds+=collect_feeds(tokens,now,day.astimezone(timezone.utc).date(),end.astimezone(timezone.utc).date(),world_db)
        # Selection time follows retrieval; newly fetched timestamps must not appear future-dated.
        now=datetime.now(timezone.utc)
        eligible=select_fixtures(feeds,now,horizon,[],[])
        regions=st.multiselect('Regions',sorted({r['region'] for r in eligible}))
        countries=st.multiselect('Countries',sorted({r['country'] for r in eligible if not regions or r['region'] in regions}))
        league_names={r['competition_id']:r['country']+' · '+r['competition'] for r in eligible}
        leagues=st.multiselect('Leagues',sorted(league_names),format_func=lambda cid:league_names[cid])
        selected=select_fixtures(feeds,now,horizon,regions,leagues)
        if countries:selected=[r for r in selected if r['country'] in countries]
        estimates=rank_estimates(selected,limit)
        st.metric('Matching fixtures',len(selected))
        st.caption(f'{len(selected)} current fixtures match your filters; {len(estimates)} eligible estimates under the selected daily limit.')
        st.caption('Only actually available countries appear in filters. Top 20/50 applies to released estimates per Nigeria calendar day; All fixtures keeps every matching game visible.')
        shown=estimates if view=='Eligible estimates' else selected
        if shown:
            rows=[{'Match ID':r['event_id'],'Home':r['home'],'Away':r['away'],
                'Country':r['country'],'League':r['competition'],'Kickoff (Nigeria)':wat(r['kickoff']),
                'Probability':f'{r["probability"]:.0%}' if r.get('probability_state')=='released' else 'Not validated',
                'Evidence status':r['probability_reason'],'Source':r['provider'],'Retrieved':wat(r['observed_at']),
                'SportyBet market':'Check manually'} for r in shown]
            st.dataframe(rows,hide_index=True,width='stretch')
            st.download_button('Export fixture list',csv_bytes(rows),'current-fixtures.csv','text/csv')
        elif not eligible:
            st.info('No fixtures available in this window from the active feeds. Try Next 7 days or configure additional sources below.')
        else:
            st.info('No eligible probability estimates yet. Choose All fixtures to see current games; league models still need validation.')
        with st.expander('First-half evidence and model details'):
            st.write('Recent goal frequencies are descriptive, not calibrated probabilities. Worldwide league models begin in shadow research; the Bundesliga candidate is also unvalidated.')
            if feed:
                lookup={f'openligadb:{r["match_id"]}':r for r in feed['matches']}
                counts=[]
                for row in selected:
                    original=lookup.get(row['event_id'])
                    if original:
                        counts.append({'Fixture':row['home']+' vs '+row['away'],
                            'Home FH goals / games':recent_halves(feed['matches'],original['home_id'],now),
                            'Away FH goals / games':recent_halves(feed['matches'],original['away_id'],now),
                            'Model':'Unreleased','Sample scope':'Latest 10 completed games in current season with HT data'})
                if counts:st.dataframe(counts,hide_index=True)
        with st.expander('Worldwide sources and setup',expanded=not tokens):
            st.dataframe([{'Source':f['provider'],'State':f['state'],'Returned fixtures':len(f.get('events',[])),
                'Complete response':f.get('complete',False),'Reason':f.get('reason',''),
                'Retrieved':wat(f['observed_at']) if f.get('observed_at') else 'Not checked'} for f in feeds],hide_index=True)
            st.write('Expansion targets include Europe, Africa, Asia, the Americas and Oceania. A country is live only when its free provider account returns a current, reviewed competition. Free-season restrictions and quotas can limit coverage.')
            st.markdown('Create free accounts at [football-data.org](https://www.football-data.org/client/register) and optionally [API-Football](https://dashboard.api-football.com/register). In your Streamlit app settings → Secrets, add the issued keys. Do not paste keys into this chat or commit them to GitHub.')
            st.code('FOOTBALL_DATA_TOKEN = "your football-data.org free token"\nAPI_FOOTBALL_KEY = "your API-Football direct free key"',language='toml')
            st.caption('API-Football competition identities also require review before ranking. No subscriptions, auto-upgrades, betting account access or automated wagering. Do not pay for a plan to enable this build.')
            st.markdown('[football-data.org attribution](https://www.football-data.org/) · [API-Football attribution](https://www.api-football.com/)')
    finally:
        world_db.close()


def display():
    now = datetime.now(timezone.utc)
    st.set_page_config(page_title='First-Half Goals Lab', page_icon='⚽', layout='wide')
    st.caption('WORLDWIDE COVERAGE TARGET • PERSONAL RESEARCH • ZERO SUBSCRIPTIONS')
    st.title('First-Half Goals Lab')
    st.write('Find upcoming games across your available leagues and inspect first-half goal evidence.')
    enabled = st.toggle('Load current fixtures', value=os.environ.get('FH_ENGINE_DISABLE_LIVE') != '1')
    feed, feed_error = (None, None)
    if enabled:
        with st.spinner('Checking the current Bundesliga schedule…'):
            feed, feed_error = live_feed(season_for(now))
    if feed_error:
        st.error('The fixture source could not be checked. Retry after five minutes. No current fixtures are claimed.')
        st.caption(feed_error)
    st.info('Current fixtures are available from the football data feed. First-half goal counts are descriptive; validated probabilities and SportyBet market availability remain unverified.' if feed else
            'Current fixture retrieval is off or unavailable. Saved research remains accessible; no current games are claimed.')
    policy = read_json(ROOT/'config/source-policy.json')
    db = connect(DATA_DIR/'research.sqlite')
    try:
        matches = latest_matches(db)
        current_matches = feed['matches'] if feed else []
        upcoming = upcoming_matches(current_matches, now, 365)
        snapshot = db.execute('SELECT MAX(observed_at) FROM snapshots').fetchone()[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Bundesliga season fixtures', len(current_matches))
        c2.metric('Bundesliga upcoming', len(upcoming))
        c3.metric('Reviewed corrections', sum('correction' in r for r in matches))
        c4.metric('Validated forecasts', 0)
        if feed:
            st.caption(f'Schedule retrieved: {wat(feed["observed_at"])} · Cached for up to 5 minutes · OpenLigaDB, community-maintained. Kickoffs may change.')
        st.caption(f'Local research: {len(matches)} saved matches; observed {wat(snapshot)}.' if snapshot else 'Historical research reports are bundled with this deployment. No local database import is required to find current games.')
        fixtures_tab, audit_tab, backtest_tab, manual_tab, readiness_tab = st.tabs(
            ['Fixtures', 'Data audit', 'Backtest', 'Manual records', 'Readiness'])
        with fixtures_tab:
            show_finder(feed,enabled,now)
        with audit_tab:
            st.subheader('Data quality and provenance')
            st.write('A plausible score is not necessarily a correct score. Both zero-goal and nonzero halves remain visible.')
            quarantined = [r for r in matches if r['quality'] == 'quarantined']
            if quarantined:
                st.error(f'{len(quarantined)} current records are quarantined and excluded.')
                st.dataframe(quarantined, hide_index=True)
            comparison_file = DATA_DIR/'cross-source-score-comparison.csv'
            if not comparison_file.exists():
                comparison_file = ROOT/'evidence/cross-source-score-comparison.csv'
            if comparison_file.exists():
                with comparison_file.open(encoding='utf-8-sig', newline='') as file:
                    comparison = list(csv.DictReader(file))
                counts = {state: sum(r['state'] == state for r in comparison)
                          for state in ('agree', 'score_disagreement', 'reference_ht_missing')}
                st.dataframe([{'Original comparison state': k, 'Matches': v} for k, v in counts.items()], hide_index=True)
                st.info('The reference archive lacks explicit half-time fields for 126 matches, including 125 recorded as 0–0 at full time. These rows were retained, not silently discarded.')
                st.download_button('Download full comparison', comparison_file.read_bytes(), 'cross-source-score-comparison.csv')
            corrections = [r['correction'] for r in matches if 'correction' in r]
            if corrections:
                st.dataframe([{'Match ID': c['source_match_id'], 'Original HT': c['original_ht'],
                               'Reviewed HT': c['corrected_ht'], 'Authority': c['authority_url']} for c in corrections],
                             hide_index=True, width='stretch',
                             column_config={'Authority': st.column_config.LinkColumn('Authority')})
            st.caption('Each correction is bound to its original score and snapshot hash. All 100 fixed-sample half-time scores were corroborated against official publications by assisted desk review. This does not certify the full archive or independent upstream collection.')
        with backtest_tab:
            st.subheader('Historical evidence')
            report = research_report('reports/v1/backtest.json')
            if not report:
                st.info('No backtest report is available yet. No model performance is claimed.')
            else:
                st.info('Retrospective research only. Historical publication times were reconstructed; prospective performance and profitable value are unproven.')
                st.write('Forecast timing: **60 minutes before kickoff**. Earlier results enter the reconstructed history after at least 24 hours.')
                metrics_rows = []
                for name, key in [('Development 2024–25', 'development'), ('Final sequential holdout 2025–26', 'holdout')]:
                    m = report[key]
                    if m['count']:
                        metrics_rows.append({'Period': name, 'Matches': m['count'],
                                             'Model log loss': round(m['log_loss'], 4),
                                             'Baseline log loss': round(m['baseline']['log_loss'], 4),
                                             'Model Brier': round(m['brier'], 4),
                                             'Baseline Brier': round(m['baseline']['brier'], 4)})
                st.dataframe(metrics_rows, hide_index=True, width='stretch')
                st.caption('Lower log loss and Brier score are better. The baseline is the earlier league goal frequency, not bookmaker odds.')
                holdout = report['holdout']
                if holdout.get('count'):
                    interval = holdout['log_loss_difference_95ci']
                    if interval:
                        st.write(f'Model minus baseline log-loss difference, 95% week-block interval: **[{interval[0]:.4f}, {interval[1]:.4f}]**')
                        if interval[0] <= 0 <= interval[1]:
                            st.write('The interval crosses zero: this test does not show a clear improvement over the baseline.')
                    st.write('Retrospective evidence gate: **'+('passed' if holdout['retrospective_metric_gate'] else 'not passed')+'**. Operational release remains locked.')
                    if holdout['reliability']:
                        st.dataframe(holdout['reliability'], hide_index=True, width='stretch')
                with st.expander('Monthly folds and exclusions'):
                    st.write(f'Sealed configuration: {report["selection"]["selected_configuration"]}')
                    st.dataframe(report['folds'], hide_index=True, width='stretch')
                    st.write(f'{len(report["exclusions"])} historical rows excluded for insufficient feature history.')
                st.download_button('Download full research report', json.dumps(report, indent=2), 'backtest.json', 'application/json')
                st.caption('No historical SportyBet ROI was calculated. The selected configuration was sealed before evaluating the final holdout.')
            challenger = research_report('reports/poisson-v2-exploratory/report.json')
            if challenger:
                with st.expander('Poisson challenger — exploratory', expanded=True):
                    st.warning('Exploratory comparison on already inspected seasons. This is not fresh holdout evidence; operational release remains locked.')
                    st.metric('Exploratory challenger matches', challenger['pooled_outer']['count'])
                    pooled = challenger['pooled_outer']
                    st.write(f'Across those matches: challenger log loss **{pooled["log_loss"]:.4f}**, league baseline **{pooled["baseline"]["log_loss"]:.4f}**.')
                    baseline_interval = pooled['log_loss_difference_95ci']
                    if baseline_interval:
                        st.write(f'Challenger minus league baseline, 95% week-block interval: **[{baseline_interval[0]:.4f}, {baseline_interval[1]:.4f}]**.')
                        if baseline_interval[0] <= 0 <= baseline_interval[1]:
                            st.write('The baseline comparison includes zero: a reliable improvement has not been demonstrated.')
                    comparison = challenger['v1_common_cohort']
                    if comparison['shared_count']:
                        st.caption(f'Both models below use the same {comparison["shared_count"]} matches from 2025–26. Lower log loss and Brier are better.')
                        st.dataframe([{'Model':label, 'Matches':m['count'], 'Log loss':round(m['log_loss'],4),
                                       'Brier':round(m['brier'],4), 'ROC-AUC':round(m['auc'],4) if m['auc'] is not None else None}
                                      for label,m in [('Poisson challenger',comparison['challenger']),
                                                      ('Original logistic',comparison['original_v1'])]],
                                     hide_index=True, width='stretch')
                        interval = comparison['challenger_minus_v1_weekly_95ci']
                        if interval:
                            st.write(f'Challenger minus original log-loss difference, 95% week-block interval: **[{interval[0]:.4f}, {interval[1]:.4f}]**')
                        fortnight = comparison['challenger_minus_v1_fortnightly_95ci']
                        if fortnight:
                            st.write(f'The same comparison with fortnightly blocks: **[{fortnight[0]:.4f}, {fortnight[1]:.4f}]**.')
                            if interval and interval[1] < 0 and fortnight[0] <= 0 <= fortnight[1]:
                                st.write('The improvement over the original model is sensitive to block length; robust superiority has not been demonstrated.')
                    st.caption('Earlier inner seasons choose settings before each outer season. All results remain retrospective research; no SportyBet return is calculated.')
                    st.download_button('Download challenger report', json.dumps(challenger,indent=2),
                                       'poisson-v2-exploratory.json','application/json')
        with manual_tab:
            st.subheader('Human observations and booking references')
            st.write('Visit SportyBet Nigeria yourself. These forms save what you observed; they do not contact SportyBet, create a code or place a wager.')
            manual_enabled = os.environ.get('FH_ENGINE_ENABLE_MANUAL_RECORDS') == '1'
            if not manual_enabled:
                st.info('Personal record forms are disabled on shared deployments. Enable FH_ENGINE_ENABLE_MANUAL_RECORDS=1 only on your private local installation.')
            elif not upcoming:
                st.info('Load current future fixtures before recording an observation or booking reference.')
            else:
                by_id = {r['match_id']: r for r in upcoming}
                label = lambda mid: f'{by_id[mid]["home"]} vs {by_id[mid]["away"]} · {wat(by_id[mid]["kickoff"])}'
                with st.form('observation'):
                    mid = st.selectbox('Fixture observed', list(by_id), format_func=label)
                    event = st.text_input('SportyBet event identifier copied from the official interface')
                    odds = st.number_input('Decimal odds observed', min_value=1.01, max_value=1000.0, value=None, step=0.01)
                    observed_text = st.text_input('Observed time in WAT (YYYY-MM-DD HH:MM)', now.astimezone(WAT).strftime('%Y-%m-%d %H:%M'))
                    state = st.selectbox('Market availability observed', ['active', 'suspended', 'unavailable'])
                    note = st.text_area('Observation note — no account, password or payment information', max_chars=1000)
                    confirmed = st.checkbox('I confirmed the real senior fixture and exactly 1st Half · Match Total Goals · Over 0.5 on Nigeria’s interface')
                    submitted = st.form_submit_button('Save human observation')
                if submitted:
                    fixture = by_id[mid]
                    try:
                        observed_at = datetime.strptime(observed_text, '%Y-%m-%d %H:%M').replace(tzinfo=WAT)
                        saved = record_observation(db, dict(MARKET, match_id=mid, home=fixture['home'], away=fixture['away'],
                            fixture_hash=fixture['snapshot_hash'], kickoff=fixture['kickoff'], odds=odds,
                            observed_at=observed_at.isoformat(), event_id=event, market_status=state,
                            event_type='real_senior_football', evidence_note=note, human_identity_confirmed=confirmed), now)
                        st.success(f'Human observation saved. Status: {observation_state(saved, fixture, now)}. Readiness remains blocked.')
                    except (ValueError, TypeError, KeyError) as exc:
                        st.error(str(exc))
                with st.form('booking'):
                    code = st.text_input('Booking code copied from SportyBet Nigeria', max_chars=32)
                    selected = st.multiselect('Selections recorded in the original code — first-half match Over 0.5 only', list(by_id), format_func=label)
                    reloaded = st.checkbox('I personally reloaded the code in the official Nigeria interface')
                    loaded_ids = st.multiselect('All selections actually visible after reload — confirm period and line on each', list(by_id), format_func=label)
                    book_submit = st.form_submit_button('Save booking reference')
                if book_submit:
                    make_legs = lambda ids: [dict(MARKET, match_id=mid) for mid in ids]
                    try:
                        saved = record_booking(db, {'code': code, 'country': 'NG', 'selection_manifest': make_legs(selected),
                            'human_reloaded': reloaded, 'reloaded_at': now.isoformat(), 'reloaded_manifest': make_legs(loaded_ids)}, now)
                        st.success(f'Reference saved: {saved["code_state"]}. Current odds and operational readiness remain unverified.')
                    except (ValueError, TypeError, KeyError) as exc:
                        st.error(str(exc))
            history = [json.loads(r[0]) for r in db.execute('SELECT record FROM observations ORDER BY id DESC LIMIT 50')] if manual_enabled else []
            if history:
                st.write('Saved observation history')
                lookup = {r['match_id']: r for r in current_matches}
                display_rows = [{'Match ID': r['match_id'], 'Odds observed': r['odds'], 'Observed': wat(r['observed_at']),
                                 'Current record state': observation_state(r, lookup[r['match_id']], now)
                                 if r['match_id'] in lookup and lookup[r['match_id']]['quality'] != 'quarantined' else 'mismatch'} for r in history]
                st.dataframe(display_rows, hide_index=True)
                st.download_button('Export human observation history', csv_bytes(display_rows), 'human-observations.csv', 'text/csv')
            bookings = [json.loads(r[0]) for r in db.execute('SELECT record FROM bookings ORDER BY id DESC LIMIT 50')] if manual_enabled else []
            if bookings:
                st.dataframe([{'Code': b['code'], 'Recorded': wat(b['entered_at']), 'Reload record': b['code_state'],
                               'Current odds': 'Unverified', 'Readiness': 'Blocked'} for b in bookings], hide_index=True)
        with readiness_tab:
            st.subheader('What still needs evidence')
            gates = [('Documented read-only fixture API access', policy['live_access_enabled']),
                     ('Fixed 100-match official score corroboration', policy['independent_score_audit_passed']),
                     ('Current fixture identity and kickoff checks', policy['current_fixture_checks_passed']),
                     ('SportyBet Nigeria settlement rules', policy['nigeria_rules_verified']),
                     ('Human booking / reload workflow', policy['manual_code_workflow_verified']),
                     ('Prospective forecast validation', policy['prospective_model_validation_passed']),
                     ('Prospective price-value evidence', policy['price_edge_supported'])]
            st.dataframe([{'Requirement': name, 'State': 'Verified' if passed else 'Pending'} for name, passed in gates], hide_index=True, width='stretch')
            st.write('Until these gates are satisfied, the application makes no current-match probability or profitable-edge claim. Automated wagering is excluded.')
        st.divider()
        st.caption('Contains OpenLigaDB information under ODbL 1.0. Reference comparison: openfootball, CC0. Personal local research; 18+; no guaranteed outcomes.')
        st.markdown('[Data source](https://www.openligadb.de/) · [Data license](https://opendatacommons.org/licenses/odbl/1-0/) · [Official Nigeria help](https://www.sportybet.com/ng/help)')
    finally:
        db.close()


display()
