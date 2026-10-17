"""Retrospective monthly walk-forward research. Never publishes live forecasts."""
import hashlib
import json
import platform
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

from data import ROOT, latest_matches, utc
from features import build_features
from model import fit_pair, metrics, predict_pair


def archive_inputs(db, output_dir, protocol):
    """Preserve the actual effective labels and generating source before fitting."""
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir/'source-code'
    archive.mkdir()
    code_hashes = {}
    for path in sorted(list(ROOT.glob('*.py')) + [ROOT/'schema.sql', ROOT/'requirements.txt']
                       + list((ROOT/'config').glob('*.json'))):
        name = path.relative_to(ROOT).as_posix()
        target = archive/name
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = path.read_bytes()
        target.write_bytes(payload)
        code_hashes[name] = hashlib.sha256(payload).hexdigest()
    effective = json.dumps(sorted(latest_matches(db), key=lambda r: r['match_id']),
                           sort_keys=True, allow_nan=False).encode()
    (output_dir/'effective-inputs.json').write_bytes(effective)
    manifest = {'python': platform.python_version(), 'numpy': np.__version__,
        'protocol': protocol, 'code_sha256': code_hashes,
        'effective_inputs_sha256': hashlib.sha256(effective).hexdigest(),
        'snapshots': [dict(r) for r in db.execute(
            'SELECT source,season,digest,observed_at,metadata FROM snapshots ORDER BY id')]}
    (output_dir/'run-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def split_month(rows, start, lag_hours=24):
    start = utc(start)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    calibration_start = start.replace(year=start.year-2)
    training_start = calibration_start.replace(year=calibration_start.year-5)
    ordered = sorted(rows, key=lambda r: (utc(r['kickoff']), r['match_id']))
    # Label publication lag must match reconstructed feature availability.
    train = [r for r in ordered if training_start <= utc(r['kickoff'])
             and utc(r['kickoff'])+timedelta(hours=lag_hours) < calibration_start-timedelta(hours=1)]
    cal = [r for r in ordered if calibration_start <= utc(r['kickoff'])
           and utc(r['kickoff'])+timedelta(hours=lag_hours) < start-timedelta(hours=1)]
    test = [r for r in ordered if start <= utc(r['kickoff']) < end]
    return train, cal, test


def difference_interval(rows, block_days=7, repeats=1000):
    if len(rows) < 100:
        return None
    blocks = {}
    for r in rows:
        block = utc(r['kickoff']).date().toordinal() // block_days
        p, b, y = np.clip(r['p'], 1e-6, 1-1e-6), np.clip(r['baseline'], 1e-6, 1-1e-6), r['target']
        delta = (-y*np.log(p)-(1-y)*np.log(1-p))-(-y*np.log(b)-(1-y)*np.log(1-b))
        blocks.setdefault(block, []).append(float(delta))
    if len(blocks) < 8:
        return None
    sums = np.array([sum(v) for v in blocks.values()])
    counts = np.array([len(v) for v in blocks.values()])
    rng = np.random.default_rng(42)
    samples = rng.integers(0, len(blocks), size=(repeats, len(blocks)))
    differences = sums[samples].sum(axis=1)/counts[samples].sum(axis=1)
    return [float(v) for v in np.quantile(differences, [0.025, 0.975])]


def summarize(rows):
    if not rows:
        return {'count': 0, 'release_state': 'research', 'reason': 'no_eligible_predictions',
                'log_loss_difference_95ci': None}
    y = [r['target'] for r in rows]
    result = metrics(y, [r['p'] for r in rows])
    baseline = metrics(y, [r['baseline'] for r in rows])
    interval = difference_interval(rows)
    supported_bins = result['reliability']
    result.update(baseline=baseline, log_loss_difference=result['log_loss']-baseline['log_loss'],
                  log_loss_difference_95ci=interval,
                  log_loss_difference_14day_95ci=difference_interval(rows, block_days=14),
                  release_state='research',
                  release_blockers=['independent_score_audit_pending', 'no_prospective_validation',
                                    'no_SportyBet_price_history', 'current_fixture_checks_pending'],
                  retrospective_metric_gate=(len(rows) >= 500 and min(result['positives'], result['negatives']) >= 100
                    and result['brier'] < baseline['brier'] and interval is not None and interval[1] < 0
                    and result['mean_calibration_gap'] <= 0.03 and bool(supported_bins)
                    and all(abs(b['mean_prediction']-b['observed_frequency']) <= 0.05 for b in supported_bins)))
    return result


def walk_forward(db, protocol, output_dir=None, progress=None):
    supported = {'target': '1H_match_total_goals_over_0.5', 'development_season': 2024,
        'holdout_season': 2025, 'training_archive_start': '2018-08-01',
        'forecast_lead_minutes': 60, 'team_window': 20, 'smoothing': 10,
        'C_grid': [0.1, 1.0, 10.0], 'calibration_candidates': ['identity', 'sigmoid'],
        'calibration_minimum': 500, 'calibration_minimum_each_outcome': 100,
        'bootstrap_seed': 42, 'bootstrap_repetitions': 1000}
    if (any(protocol.get(k) != v for k, v in supported.items())
        or protocol.get('lag_hours') not in (24, 48)
        or set(protocol) - (set(supported) | {'name', 'lag_hours', 'policy'})):
        raise ValueError('Unsupported frozen research protocol')
    digest = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    output_dir = Path(output_dir) if output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        existing = output_dir / 'backtest.json'
        if existing.exists():
            raise FileExistsError('This research run already exists; preserve it and create a new explicitly named experiment')
    records = latest_matches(db)
    if output_dir:
        archive_inputs(db, output_dir, protocol)
    rows, exclusions = [], []
    for fixture in sorted(records, key=lambda r: r.get('kickoff', '')):
        if fixture.get('target') not in (0, 1) or fixture.get('season', 9999) > 2025:
            continue
        row = build_features(db, fixture['match_id'], utc(fixture['kickoff'])-timedelta(hours=1),
                             'retrospective', lag_hours=protocol.get('lag_hours', 24), records=records)
        (rows if row['state'] == 'eligible' else exclusions).append(row)
    development = {f'{c}:{method}': [] for c in (0.1, 1.0, 10.0) for method in ('identity', 'sigmoid')}
    folds = []
    for season in (2024, 2025):
        if season == 2025:
            supported = {k: metrics([r['target'] for r in v], [r['p'] for r in v])['log_loss']
                         for k, v in development.items() if v}
            if not supported:
                raise ValueError('No development folds met calibration requirements')
            chosen = min(supported, key=supported.get)
            seal = {'protocol_hash': digest, 'selected_configuration': chosen, 'development_losses': supported,
                    'holdout_not_used_for_selection': True}
            if output_dir:
                (output_dir/'selection-seal.json').write_text(json.dumps(seal, indent=2), encoding='utf-8')
            holdout = []
        for month in (8, 9, 10, 11, 12, 1, 2, 3, 4, 5):
            year = season if month >= 8 else season+1
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            train, cal, test = split_month(rows, start, lag_hours=protocol['lag_hours'])
            if not test:
                continue
            configs = (0.1, 1.0, 10.0) if season == 2024 else (float(chosen.split(':')[0]),)
            fold = {'month': start.strftime('%Y-%m'), 'training_count': len(train), 'calibration_count': len(cal),
                    'test_count': len(test), 'state': 'evaluated'}
            if not train or (start.replace(year=start.year-2)-utc(train[0]['kickoff'])).days < 365*3:
                fold.update(state='skipped', reason='fewer_than_three_years_training_history')
                folds.append(fold)
                continue
            for c in configs:
                try:
                    pair = fit_pair(train, cal, {'C': c, 'calibration': 'sigmoid'})
                except ValueError as exc:
                    fold.update(state='skipped', reason=str(exc))
                    continue
                for r in test:
                    prediction = predict_pair(pair, r)
                    for method in ('identity', 'sigmoid') if season == 2024 else (chosen.split(':')[1],):
                        result = {k: r[k] for k in ('match_id', 'kickoff', 'cutoff', 'season', 'target', 'baseline', 'home', 'away')}
                        result.update(p=prediction['raw_p'] if method == 'identity' else prediction['calibrated_p'],
                                      model_id=pair['model_id'], state='retrospective_research')
                        (development[f'{c}:{method}'] if season == 2024 else holdout).append(result)
            folds.append(fold)
            if progress:
                progress(f'{start:%Y-%m}: {fold["state"]}, {len(test)} eligible matches')
    result = {'protocol': protocol, 'protocol_hash': digest, 'selection': seal,
              'availability': 'retrospective_reconstruction_not_historical_publication_snapshots',
              'development': summarize(development[chosen]), 'holdout': summarize(holdout),
              'folds': folds, 'exclusions': [{'match_id': r['match_id'], 'reason': r['reason']} for r in exclusions],
              'predictions': holdout, 'no_odds_return_analysis': True}
    if output_dir:
        (output_dir/'backtest.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    return result
