"""Small logistic model with a separate, chronologically later calibrator."""
import hashlib
import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data import utc
from features import FEATURE_NAMES


def matrix(rows):
    x = np.asarray([r['values'] for r in rows], dtype=float)
    if x.ndim != 2 or x.shape[1] != len(FEATURE_NAMES) or not np.isfinite(x).all():
        raise ValueError('Invalid feature vector')
    return x


def fit_pair(train_rows, calibration_rows, config):
    method = config.get('calibration', 'sigmoid')
    regularization = config.get('C', 1.0)
    if method not in ('identity', 'sigmoid') or regularization not in (0.1, 1.0, 10.0):
        raise ValueError('Unsupported experiment configuration')
    if len(train_rows) < 100 or len(calibration_rows) < 500:
        raise ValueError('Insufficient train/calibration observations')
    for rows in (train_rows, calibration_rows):
        if any(type(r['target']) is not int or r['target'] not in (0, 1)
               or utc(r['cutoff']) >= utc(r['kickoff']) for r in rows):
            raise ValueError('Invalid label or future information cutoff')
        if len({r['match_id'] for r in rows}) != len(rows):
            raise ValueError('Duplicate match identity in fitting data')
    if {r['match_id'] for r in train_rows} & {r['match_id'] for r in calibration_rows}:
        raise ValueError('Training and calibration identities overlap')
    if max(utc(r['kickoff']) for r in train_rows) >= min(utc(r['cutoff']) for r in calibration_rows):
        raise ValueError('Training and calibration chronology overlaps')
    y_train = np.array([r['target'] for r in train_rows])
    y_cal = np.array([r['target'] for r in calibration_rows])
    if len(np.unique(y_train)) != 2 or min(np.bincount(y_cal, minlength=2)) < 100:
        raise ValueError('Insufficient class support for calibration')
    estimator = make_pipeline(StandardScaler(), LogisticRegression(C=regularization, max_iter=1000, random_state=42))
    estimator.fit(matrix(train_rows), y_train)
    calibrator = None
    fallback = None
    if method == 'sigmoid':
        raw_logit = estimator.decision_function(matrix(calibration_rows)).reshape(-1, 1)
        calibrator = LogisticRegression(C=1.0, max_iter=1000, random_state=42).fit(raw_logit, y_cal)
        if calibrator.coef_[0, 0] <= 0:
            calibrator, fallback = None, 'non_monotonic_calibration_rejected'
    fingerprint = json.dumps({'train': train_rows, 'calibration': calibration_rows, 'config': config},
                             sort_keys=True, default=str, allow_nan=False).encode()
    model_id = hashlib.sha256(fingerprint).hexdigest()
    return {'estimator': estimator, 'calibrator': calibrator, 'model_id': model_id,
            'calibration_for': model_id, 'config': config,
            'calibration_fallback': fallback, 'state': 'research',
            'training_end': max(r['kickoff'] for r in train_rows),
            'calibration_end': max(r['kickoff'] for r in calibration_rows),
            'train_count': len(train_rows), 'calibration_count': len(calibration_rows)}


def predict_pair(pair, feature_row):
    if pair['model_id'] != pair['calibration_for']:
        raise ValueError('Calibrator belongs to a different model')
    x = matrix([feature_row])
    raw = float(pair['estimator'].predict_proba(x)[0, 1])
    calibrated = raw
    if pair['calibrator'] is not None:
        logits = pair['estimator'].decision_function(x).reshape(-1, 1)
        calibrated = float(pair['calibrator'].predict_proba(logits)[0, 1])
    if not np.isfinite([raw, calibrated]).all():
        raise ValueError('Nonfinite probability')
    return {'raw_p': raw, 'calibrated_p': calibrated, 'state': 'research', 'model_id': pair['model_id']}


def metrics(targets, probabilities):
    y, p = np.asarray(targets), np.asarray(probabilities, dtype=float)
    if not len(y) or y.shape != p.shape or not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Invalid evaluation arrays')
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    result = {'count': len(y), 'positives': int(y.sum()), 'negatives': int(len(y)-y.sum()),
              'brier': float(np.mean((p-y)**2)),
              'log_loss': float(np.mean(-y*np.log(clipped)-(1-y)*np.log(1-clipped))),
              'mean_prediction': float(p.mean()), 'observed_frequency': float(y.mean()),
              'mean_calibration_gap': float(abs(p.mean()-y.mean())),
              'auc': float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
              'calibration_intercept': None, 'calibration_slope': None, 'reliability': []}
    if len(y) >= 100 and len(np.unique(y)) == 2:
        logits = np.log(clipped/(1-clipped)).reshape(-1, 1)
        diagnostic = LogisticRegression(C=1e6, max_iter=1000).fit(logits, y)
        result.update(calibration_intercept=float(diagnostic.intercept_[0]),
                      calibration_slope=float(diagnostic.coef_[0, 0]))
    if len(y) >= 100:
        for indices in np.array_split(np.argsort(p, kind='stable'), min(5, len(y)//100)):
            freq = float(y[indices].mean())
            n = len(indices)
            # Wilson interval for the observed bin frequency, not a single-match interval.
            den = 1 + 1.96**2/n
            center = (freq + 1.96**2/(2*n))/den
            half = 1.96*np.sqrt(freq*(1-freq)/n + 1.96**2/(4*n*n))/den
            result['reliability'].append({'count': n, 'mean_prediction': float(p[indices].mean()),
                                           'observed_frequency': freq, 'frequency_95ci': [center-half, center+half]})
    return result
