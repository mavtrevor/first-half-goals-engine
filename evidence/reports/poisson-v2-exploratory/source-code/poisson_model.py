"""Separate first-half count models for explicitly retrospective research."""
import hashlib
import json
import warnings
from datetime import timedelta

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, PoissonRegressor

from data import positive_id, utc


def probability_from_rates(home, away):
    if any(type(v) not in (int, float) or not np.isfinite(v) or v < 0 for v in (home, away)):
        raise ValueError('Invalid Poisson rate')
    total = home + away
    if not np.isfinite(total):
        raise ValueError('Nonfinite total rate')
    return float(-np.expm1(-total))


def team_matrix(rows, vocabulary, away=False):
    n = len(vocabulary)
    result = np.zeros((len(rows), 2*n))
    for i, row in enumerate(rows):
        h, a = positive_id(row['home_id']), positive_id(row['away_id'])
        if h == a:
            raise ValueError('Home and away identities must differ')
        attacker, defender = (a, h) if away else (h, a)
        if attacker in vocabulary:
            result[i, vocabulary[attacker]] = 1
        if defender in vocabulary:
            result[i, n+vocabulary[defender]] = 1
    return result


def _rates(pair, rows):
    home = pair['home'].predict(team_matrix(rows, pair['vocabulary']))
    away = pair['away'].predict(team_matrix(rows, pair['vocabulary'], away=True))
    if not np.isfinite(home).all() or not np.isfinite(away).all() or np.any(home < 0) or np.any(away < 0):
        raise ValueError('Nonfinite or negative fitted rate')
    return home, away


def _logits(probabilities):
    p = np.clip(probabilities, 1e-6, 1-1e-6)
    return np.log(p/(1-p)).reshape(-1, 1)


def fit_counts(train, calibration_rows, alpha, calibration='sigmoid'):
    if type(alpha) not in (int, float) or alpha not in (0.01, 0.1, 1.0) or calibration not in ('identity', 'sigmoid'):
        raise ValueError('Unsupported count-model configuration')
    if len(train) < 500 or len(calibration_rows) < 500:
        raise ValueError('Insufficient training/calibration observations')
    for rows in (train, calibration_rows):
        ids = [positive_id(r['match_id']) for r in rows]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate fitting identity')
        for r in rows:
            positive_id(r['home_id']); positive_id(r['away_id'])
            if r['home_id'] == r['away_id'] or any(type(r[k]) is not int or r[k] < 0 for k in ('ht_home', 'ht_away')):
                raise ValueError('Invalid count or team identity')
            if type(r['target']) is not int or r['target'] != int(r['ht_home']+r['ht_away'] > 0):
                raise ValueError('Binary target and count disagree')
            if utc(r['cutoff']) >= utc(r['kickoff']) or not r.get('snapshot_hash'):
                raise ValueError('Invalid feature cutoff or source lineage')
    if {r['match_id'] for r in train} & {r['match_id'] for r in calibration_rows}:
        raise ValueError('Training/calibration identities overlap')
    label_lag = timedelta(hours=24)
    if max(utc(r['kickoff']) for r in train)+label_lag >= min(utc(r['cutoff']) for r in calibration_rows):
        raise ValueError('Training labels were not available before calibration')
    if (max(utc(r['kickoff']) for r in train)-min(utc(r['kickoff']) for r in train)).days < 730:
        raise ValueError('Training span is shorter than two years')
    targets = np.array([r['target'] for r in calibration_rows])
    if min(np.bincount(targets, minlength=2)) < 100:
        raise ValueError('Insufficient calibration class support')
    vocabulary = {team: i for i, team in enumerate(sorted({r[k] for r in train for k in ('home_id', 'away_id')}))}
    identity_keys = ('match_id', 'home_id', 'away_id', 'ht_home', 'ht_away', 'target', 'kickoff', 'cutoff', 'snapshot_hash')
    fingerprint = {'alpha': alpha, 'calibration': calibration,
        'train': [{k: r[k] for k in identity_keys} for r in sorted(train, key=lambda r: r['match_id'])],
        'calibration_rows': [{k: r[k] for k in identity_keys} for r in sorted(calibration_rows, key=lambda r: r['match_id'])]}
    model_id = hashlib.sha256(json.dumps(fingerprint, sort_keys=True, allow_nan=False).encode()).hexdigest()
    pair = {'vocabulary': vocabulary, 'model_id': model_id, 'calibration_for': model_id,
            'calibrator': None, 'calibration_fallback': None, 'alpha': alpha,
            'minimum_inference_cutoff': (max(utc(r['kickoff']) for r in calibration_rows)+label_lag).isoformat(),
            'state': 'retrospective_exploratory', 'operational_release': False}
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        for side, away in (('home', False), ('away', True)):
            y = np.array([r['ht_away' if away else 'ht_home'] for r in train])
            if not y.sum():
                raise ValueError('No positive counts for a fitting side')
            pair[side] = PoissonRegressor(alpha=alpha, max_iter=2000, tol=1e-8).fit(team_matrix(train, vocabulary, away), y)
        h, a = _rates(pair, calibration_rows)
        raw = np.array([probability_from_rates(float(x), float(y)) for x, y in zip(h, a)])
        if calibration == 'sigmoid':
            calibrator = LogisticRegression(C=1, max_iter=1000, random_state=42).fit(_logits(raw), targets)
            if calibrator.coef_[0, 0] > 0:
                pair['calibrator'] = calibrator
            else:
                pair['calibration_fallback'] = 'nonpositive_slope_identity_fallback'
    h, a = _rates(pair, train)
    home_residual = (np.array([r['ht_home'] for r in train])-h)/np.sqrt(np.maximum(h, 1e-12))
    away_residual = (np.array([r['ht_away'] for r in train])-a)/np.sqrt(np.maximum(a, 1e-12))
    pair['count_diagnostics'] = {'home_mean_squared_pearson_residual': float(np.mean(home_residual**2)),
        'away_mean_squared_pearson_residual': float(np.mean(away_residual**2)),
        'residual_correlation': float(np.corrcoef(home_residual, away_residual)[0, 1])
            if np.std(home_residual) > 0 and np.std(away_residual) > 0 else None,
        'interpretation': 'training_descriptive_only_not_assumption_validation'}
    return pair


def predict_counts(pair, row):
    if pair['model_id'] != pair['calibration_for']:
        raise ValueError('Calibrator belongs to another count model')
    if utc(row['cutoff']) <= utc(pair['minimum_inference_cutoff']) or utc(row['cutoff']) >= utc(row['kickoff']):
        raise ValueError('Prediction cutoff overlaps calibration label availability or kickoff')
    h, a = _rates(pair, [row])
    raw = probability_from_rates(float(h[0]), float(a[0]))
    calibrated = float(pair['calibrator'].predict_proba(_logits([raw]))[0, 1]) if pair['calibrator'] is not None else raw
    if not np.isfinite(calibrated) or not 0 <= calibrated <= 1:
        raise ValueError('Invalid calibrated probability')
    return {'raw_p': raw, 'calibrated_p': calibrated, 'lambda_home': float(h[0]), 'lambda_away': float(a[0]),
            'unseen_teams': [row[k] for k in ('home_id', 'away_id') if row[k] not in pair['vocabulary']],
            'model_id': pair['model_id'], 'state': 'retrospective_exploratory', 'operational_release': False}
