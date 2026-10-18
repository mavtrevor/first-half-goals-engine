# Poisson challenger: execution plan and frozen exploratory protocol

18 October 2026. Spec: `model-investigation-next-experiment.md`. The user's instruction to proceed authorizes this offline research experiment. All inspected data stays exploratory; no fresh confirmatory period is assigned and no forecast or betting gate opens.

## Protocol fixed before running

`config/challenger-v2.json` contains the accepted settings. Only those settings are supported; reject edits that claim unsupported behavior. Two log-link Poisson regressors model home/away HT counts separately. Each uses an intercept and training-vocabulary one-hot attacking/defending team effects, L2 alpha in {0.01,0.1,1}, no time decay, and up to five earlier years. Unknown coefficients use zero log effect (league intercept), but fixtures still need v1's minimum 10 previous league matches per team. Labels/counts must agree and all input counts/IDs must be valid. Convergence warnings fail the candidate rather than silently using an unfinished fit.

For each monthly fold, the last two years before the test month are reserved for calibration; training ends before that period. Result availability uses a 24-hour lag in both labels and feature history. Require 500 training rows spanning at least 730 days, and 500 calibration rows with 100 of each binary class. Unknown/invalid identities, overlapping train/calibration rows, future cutoffs, stale calibrator lineage and inference at/before calibration-label availability fail closed.

The two Poisson rates yield `p = 1-exp(-(lambda_home+lambda_away))`. Compare identity calibration with an independent, later, regularized positive-slope sigmoid (C=1). Reject nonpositive-slope sigmoid and disclose identity fallback. Preserve both raw and calibrated probabilities. Fit from exactly the same eligible-row set used by the v1 feature builder; evaluation compares identical match IDs and cutoffs. Reuse the same league-frequency baseline.

Outer season 2024 uses inner season 2023 for alpha/calibration selection; outer 2025 uses inner 2024. Each inner season has monthly chronological training/calibration/validation splits. All grid candidates must predict the complete shared validation cohort; select minimum pooled inner log loss, tie-breaking toward larger alpha then identity. Seal the selected configuration before its outer season. Refit the selected pair monthly using only earlier rows. This nested chronology is a development discipline, not a claim that previously inspected seasons are untouched.

The three-year minimum-span restriction in the old runner is replaced by a declared two-year minimum for this challenger because the 2018 archive would otherwise prevent early inner folds. This costs cross-model training-rule equivalence; evaluation cohorts, not fitting procedures, are held identical. The old runner and its archived reports are unchanged.

Save code, full protocol and actual effective normalized inputs before fitting; persist selection seals, fold coverage/failures and model lineage. Include training mean squared Pearson residuals for both counts and residual correlation as descriptive diagnostics, without claiming that these validate independence or dispersion. Report log loss, Brier, AUC, supported reliability bins, paired weekly and fortnightly uncertainty. Compare the 2025 outer cohort to frozen v1 by intersection, checking the target, kickoff/cutoff and baseline match; disclose missing IDs. Operational release is always false, even if an exploratory comparison improves.

## Tasks and verification

1. Add `poisson_model.py`: failing tests first for rate arithmetic, team effects, unknown-team shrinkage, invalid counts, class minimums, overlap, temporal label availability, lineage and nonfinite predictions. Run those tests and the existing suite; commit.
2. Add separate `challenger.py`: tests first for strict protocol validation, nested inner-before-outer selection, common-cohort selection, rejection of partial candidates, immutable output directory, alignment of original comparator and permanently exploratory reports. Archive inputs, then run the frozen experiment once; capture observed results without changing settings.
3. Add a clearly labelled exploratory section to the existing Backtest screen and document the actual result, commands and remaining gates. Run UI smoke tests and the full suite, check original evidence hashes, visually inspect the screen, and obtain one fresh final code review. Address important findings with reproducing tests in one fix pass. Commit and update the already authorized private repository.

Review focus: mismatched label/feature timestamps; forward use of calibration outcomes or outer labels during model selection; vocabulary/unknown-team handling and count validation; comparator cohort alignment; false evidence of prospective release; overwrite/partial-run provenance. No external data adapter, package addition, account access or automatic wager is part of these tasks.
