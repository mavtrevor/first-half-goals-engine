"""Local research interface. External operator actions are always human-operated."""
import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from data import ROOT, connect, latest_matches, utc
from observations import MARKET, observation_state, record_booking, record_observation

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


def display():
    now = datetime.now(timezone.utc)
    st.set_page_config(page_title='First-Half Goals Lab', page_icon='⚽', layout='wide')
    st.caption('BUNDESLIGA • PERSONAL RESEARCH • ZERO SUBSCRIPTIONS')
    st.title('First-Half Goals Lab')
    st.write('Explore the evidence before trusting a prediction.')
    st.warning('Live retrieval is disabled. This is an offline research workbench; current-match forecasts and SportyBet readiness remain locked.')
    policy = read_json(ROOT/'config/source-policy.json')
    db = connect(DATA_DIR/'research.sqlite')
    try:
        matches = latest_matches(db)
        valid = [r for r in matches if r.get('target') in (0, 1)]
        upcoming = sorted([r for r in matches if r.get('kickoff') and not r.get('finished')
                           and utc(r['kickoff']) > now], key=lambda r: r['kickoff'])
        snapshot = db.execute('SELECT MAX(observed_at) FROM snapshots').fetchone()[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Recorded matches', len(matches))
        c2.metric('Finished with HT score', len(valid))
        c3.metric('Reviewed corrections', sum('correction' in r for r in matches))
        c4.metric('Validated forecasts', 0)
        st.caption(f'Saved data observed: {wat(snapshot)}. No continuous verification.' if snapshot else 'No saved snapshots loaded yet.')
        fixtures_tab, audit_tab, backtest_tab, manual_tab, readiness_tab = st.tabs(
            ['Fixtures', 'Data audit', 'Backtest', 'Manual records', 'Readiness'])
        with fixtures_tab:
            st.subheader('Upcoming fixtures in the saved snapshot')
            st.caption('Kickoffs are unconfirmed. An old snapshot can include postponed or changed fixtures.')
            if not upcoming:
                st.info('No fixtures available in the selected saved data. No match probabilities are available.')
            else:
                horizon = st.selectbox('Show fixtures within', [7, 14, 30, 365], format_func=lambda d: f'{d} days')
                rows = [{'Match ID': r['match_id'], 'Home': r['home'], 'Away': r['away'],
                         'Kickoff': wat(r['kickoff']), 'Time status': 'Unconfirmed',
                         'Probability': 'Unavailable — validation pending'}
                        for r in upcoming if utc(r['kickoff']) <= now+timedelta(days=horizon)]
                if rows:
                    st.dataframe(rows, hide_index=True, width='stretch')
                    st.download_button('Export fixture list', csv_bytes(rows), 'saved-fixtures.csv', 'text/csv')
                else:
                    st.info('No fixtures within this horizon in the saved snapshot.')
        with audit_tab:
            st.subheader('Data quality and provenance')
            st.write('A plausible score is not necessarily a correct score. Both zero-goal and nonzero halves remain visible.')
            quarantined = [r for r in matches if r['quality'] == 'quarantined']
            if quarantined:
                st.error(f'{len(quarantined)} current records are quarantined and excluded.')
                st.dataframe(quarantined, hide_index=True)
            comparison_file = DATA_DIR/'cross-source-score-comparison.csv'
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
            st.caption('Each correction is bound to its original score and snapshot hash. The independent 100-match audit remains incomplete.')
        with backtest_tab:
            st.subheader('Historical evidence')
            report = read_json(DATA_DIR/'reports/v1/backtest.json')
            if not report:
                st.info('No backtest report is available yet. No model performance is claimed.')
            else:
                st.info('Retrospective research only. Historical publication times were reconstructed; prospective performance and profitable value are unproven.')
                st.write(f'Sealed configuration: **{report["selection"]["selected_configuration"]}** · T−60 horizon · 24-hour result-availability lag')
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
                    st.write(f'Model minus baseline log-loss difference, 95% week-block interval: **{interval}**')
                    st.write('Retrospective evidence gate: **'+('passed' if holdout['retrospective_metric_gate'] else 'not passed')+'**. Operational release remains locked.')
                    if holdout['reliability']:
                        st.dataframe(holdout['reliability'], hide_index=True, width='stretch')
                with st.expander('Monthly folds and exclusions'):
                    st.dataframe(report['folds'], hide_index=True, width='stretch')
                    st.write(f'{len(report["exclusions"])} historical rows excluded for insufficient feature history.')
                st.download_button('Download full research report', json.dumps(report, indent=2), 'backtest.json', 'application/json')
                st.caption('No historical SportyBet ROI was calculated. The selected configuration was sealed before evaluating the final holdout.')
        with manual_tab:
            st.subheader('Human observations and booking references')
            st.write('Visit SportyBet Nigeria yourself. These forms save what you observed; they do not contact SportyBet, create a code or place a wager.')
            if not upcoming:
                st.info('Load saved future fixtures before recording an observation or booking reference.')
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
            history = [json.loads(r[0]) for r in db.execute('SELECT record FROM observations ORDER BY id DESC LIMIT 50')]
            if history:
                st.write('Saved observation history')
                lookup = {r['match_id']: r for r in matches}
                display_rows = [{'Match ID': r['match_id'], 'Odds observed': r['odds'], 'Observed': wat(r['observed_at']),
                                 'Current record state': observation_state(r, lookup[r['match_id']], now)
                                 if r['match_id'] in lookup and lookup[r['match_id']]['quality'] != 'quarantined' else 'mismatch'} for r in history]
                st.dataframe(display_rows, hide_index=True)
                st.download_button('Export human observation history', csv_bytes(display_rows), 'human-observations.csv', 'text/csv')
            bookings = [json.loads(r[0]) for r in db.execute('SELECT record FROM bookings ORDER BY id DESC LIMIT 50')]
            if bookings:
                st.dataframe([{'Code': b['code'], 'Recorded': wat(b['entered_at']), 'Reload record': b['code_state'],
                               'Current odds': 'Unverified', 'Readiness': 'Blocked'} for b in bookings], hide_index=True)
        with readiness_tab:
            st.subheader('What still needs evidence')
            gates = [('API access terms', policy['live_access_enabled']),
                     ('Independent 100-match score audit', policy['independent_score_audit_passed']),
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
