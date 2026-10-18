"""Run the frozen, offline Poisson v2 exploratory experiment once."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning

from backtest import archive_inputs, difference_interval, split_month, summarize
from data import ROOT, connect, latest_matches, utc
from features import build_features
from model import metrics
from poisson_model import fit_counts, predict_counts

# Exact supported settings; changing a declared protocol requires a new implementation/version.
PROTOCOL_HASH = '0ff479dd3485faf2260c8e887879f2beaeb5c12b4bfce636e1ff325bb5a134d6'


def validate_protocol(protocol):
    digest = hashlib.sha256(json.dumps(protocol, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if digest != PROTOCOL_HASH:
        raise ValueError('Unsupported or modified frozen challenger protocol')
    return digest


def nested_schedule(protocol):
    validate_protocol(protocol)
    return [(season-1, season) for season in protocol['outer_seasons']]


def exploratory_summary(rows):
    result = summarize(rows)
    result.pop('retrospective_metric_gate', None)
    result.update(release_state='retrospective_exploratory', operational_release=False,
        release_blockers=['previously_inspected_archive_not_independent_confirmation',
                          'no_prospective_validation', 'current_fixture_checks_pending',
                          'no_SportyBet_price_history', 'Nigeria_rules_unverified'])
    return result


def select_candidate(candidates, expected_ids):
    losses, rejected, reference = {}, {}, None
    for key, rows in candidates.items():
        ids = [r['match_id'] for r in rows]
        if not expected_ids or len(ids) != len(set(ids)) or set(ids) != expected_ids:
            rejected[key] = 'incomplete_or_duplicate_validation_cohort'
            continue
        identities = {r['match_id']: (r['target'], utc(r['kickoff']), utc(r['cutoff'])) for r in rows}
        if reference is None:
            reference = identities
        if identities != reference:
            rejected[key] = 'validation_label_or_timing_mismatch'
            continue
        losses[key] = metrics([r['target'] for r in rows], [r['p'] for r in rows])['log_loss']
    if not losses:
        raise ValueError('No candidate covered the complete inner validation cohort')
    chosen = min(losses, key=lambda k: (losses[k], -float(k.split(':')[0]), k.split(':')[1] != 'identity'))
    return chosen, losses, rejected


def compare_frozen(rows, original):
    new = {r['match_id']: r for r in rows}
    old = {r['match_id']: r for r in original}
    if len(new) != len(rows) or len(old) != len(original):
        raise ValueError('Duplicate comparator match identity')
    shared = sorted(set(new) & set(old))
    paired = []
    for mid in shared:
        a, b = new[mid], old[mid]
        if (a['target'] != b['target'] or utc(a['kickoff']) != utc(b['kickoff'])
            or utc(a['cutoff']) != utc(b['cutoff']) or abs(a['baseline']-b['baseline']) > 1e-12):
            raise ValueError('Frozen comparator label, time or baseline mismatch')
        paired.append(dict(a, baseline=b['p']))
    return {'shared_count': len(shared), 'missing_from_challenger': sorted(set(old)-set(new)),
        'not_in_original_v1': sorted(set(new)-set(old)), 'operational_release': False,
        'challenger': metrics([new[i]['target'] for i in shared], [new[i]['p'] for i in shared]) if shared else None,
        'original_v1': metrics([old[i]['target'] for i in shared], [old[i]['p'] for i in shared]) if shared else None,
        'challenger_minus_v1_weekly_95ci': difference_interval(paired),
        'challenger_minus_v1_fortnightly_95ci': difference_interval(paired, block_days=14)}


def evaluate_season(rows, season, configurations, progress=None):
    predictions = {key: [] for key in configurations}
    expected_ids, folds = set(), []
    for month in (8, 9, 10, 11, 12, 1, 2, 3, 4, 5):
        start = datetime(season if month >= 8 else season+1, month, 1, tzinfo=timezone.utc)
        train, cal, test = split_month(rows, start, lag_hours=24)
        expected_ids.update(r['match_id'] for r in test)
        fold = {'month': start.strftime('%Y-%m'), 'train': len(train), 'calibration': len(cal),
                'expected': len(test), 'models': [], 'failures': []}
        if test:
            for key in configurations:
                alpha, method = float(key.split(':')[0]), key.split(':')[1]
                try:
                    pair = fit_counts(train, cal, alpha=alpha, calibration=method)
                    batch = []
                    for row in test:
                        predicted = predict_counts(pair, row)
                        result = {k: row[k] for k in ('match_id','kickoff','cutoff','season','target','baseline','home','away')}
                        batch.append(dict(result, **predicted))
                    predictions[key].extend(dict(r, p=r['raw_p'] if method == 'identity' else r['calibrated_p'],
                                                  calibration_used=method) for r in batch)
                    fold['models'].append({'alpha': alpha, 'calibration':method, 'model_id': pair['model_id'],
                        'training_label_available_through': (max(utc(r['kickoff']) for r in train)+timedelta(hours=24)).isoformat(),
                        'calibration_label_available_through': pair['minimum_inference_cutoff'],
                        'calibration_fallback': pair['calibration_fallback'], 'count_diagnostics': pair['count_diagnostics']})
                except (ValueError, ConvergenceWarning, FloatingPointError) as exc:
                    fold['failures'].append({'alpha':alpha, 'calibration':method, 'reason':str(exc)})
        folds.append(fold)
        if progress:
            progress(f'{start:%Y-%m}: expected {len(test)}, fitted {len(fold["models"])}, failures {len(fold["failures"])}')
    return predictions, expected_ids, folds


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def run_experiment(db, protocol, output_dir, original_v1, progress=None):
    digest = validate_protocol(protocol)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    _save(output_dir/'run-state.json', {'state':'running','protocol_hash':digest,'operational_release':False})
    try:
        archive_inputs(db, output_dir, protocol)
        _save(output_dir/'frozen-v1-comparator.json', original_v1)
        records = latest_matches(db)
        rows, exclusions = [], []
        for fixture in sorted(records, key=lambda r: r.get('kickoff','')):
            if fixture.get('target') not in (0,1) or fixture.get('season',9999) > 2025:
                continue
            row = build_features(db, fixture['match_id'], utc(fixture['kickoff'])-timedelta(hours=1),
                                 'retrospective', lag_hours=24, records=records)
            if row['state'] != 'eligible':
                exclusions.append({'match_id':fixture['match_id'],'reason':row['reason']})
                continue
            row.update({k:fixture[k] for k in ('home_id','away_id','ht_home','ht_away','snapshot_hash')})
            rows.append(row)
        configurations = [f'{alpha}:{method}' for alpha in protocol['alpha_grid'] for method in protocol['calibration_candidates']]
        selections, outer_predictions, outer_folds, inner_cache = [], [], [], {}
        for inner, outer in nested_schedule(protocol):
            if inner not in inner_cache:
                inner_cache[inner] = evaluate_season(rows, inner, configurations, progress)
            candidates, expected, folds = inner_cache[inner]
            chosen, losses, rejected = select_candidate(candidates, expected)
            latest_label = max(utc(r['kickoff']) for r in candidates[chosen])+timedelta(hours=24)
            if latest_label >= datetime(outer,8,1,tzinfo=timezone.utc)-timedelta(hours=1):
                raise ValueError('Inner selection labels overlap outer evaluation')
            seal = {'inner_season':inner,'outer_season':outer,'selected_configuration':chosen,
                    'inner_losses':losses,'rejected_candidates':rejected,'expected_inner_matches':len(expected),
                    'last_inner_label_available':latest_label.isoformat(),'protocol_hash':digest,
                    'outer_outcomes_used_for_selection':False,'all_archive_results_exploratory':True}
            _save(output_dir/f'selection-{outer}.json',seal)
            selections.append(seal)
            _save(output_dir/f'inner-{inner}.json',{'selection':seal,'folds':folds})
            selected_predictions, expected_outer, evaluated = evaluate_season(rows,outer,[chosen],progress)
            actual = selected_predictions[chosen]
            if {r['match_id'] for r in actual} != expected_outer or len(actual) != len(expected_outer):
                raise ValueError('Selected model did not cover the complete outer cohort')
            outer_predictions.extend(actual); outer_folds.extend(evaluated)
        result = {'protocol':protocol,'protocol_hash':digest,'state':'retrospective_exploratory',
            'operational_release':False,'fresh_holdout':False,'selections':selections,
            'availability':'reconstructed_Tminus60_24h_lag_not_historical_publication_snapshots',
            'pooled_outer':exploratory_summary(outer_predictions),
            'by_season':{str(y):exploratory_summary([r for r in outer_predictions if r['season']==y]) for y in protocol['outer_seasons']},
            'v1_common_cohort':compare_frozen(outer_predictions, original_v1),
            'folds':outer_folds,'exclusions':exclusions,'predictions':outer_predictions,
            'no_odds_return_analysis':True,'sklearn_version':sklearn.__version__}
        _save(output_dir/'report.json',result)
        manifest = json.loads((output_dir/'run-manifest.json').read_text())
        manifest.update(sklearn=sklearn.__version__, report_sha256=hashlib.sha256((output_dir/'report.json').read_bytes()).hexdigest(),
            comparator_sha256=hashlib.sha256((output_dir/'frozen-v1-comparator.json').read_bytes()).hexdigest())
        _save(output_dir/'run-manifest.json',manifest)
        _save(output_dir/'run-state.json',{'state':'complete','protocol_hash':digest,'operational_release':False})
        return result
    except BaseException as exc:
        _save(output_dir/'run-state.json',{'state':'failed','reason':str(exc),'protocol_hash':digest,'operational_release':False})
        raise


if __name__ == '__main__':
    database = ROOT/'data/research.sqlite'
    if not database.exists():
        raise SystemExit('Import the saved offline evidence before running this experiment')
    protocol = json.loads((ROOT/'config/challenger-v2.json').read_text())
    original = json.loads((ROOT/'evidence/reports/v1/backtest.json').read_text())['predictions']
    db = connect(database)
    try:
        report = run_experiment(db,protocol,ROOT/'data/reports'/protocol['name'],original,
                                progress=lambda message: print(message,flush=True))
        print(json.dumps(report['pooled_outer'],indent=2))
    finally:
        db.close()
