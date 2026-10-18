# Poisson v2 exploratory result

18 October 2026. **The challenger has modest descriptive improvements, but no operational release is justified.** Every evaluated season had already been inspected. These results are retrospective development evidence, not an untouched test and not evidence of betting profitability.

## Observed result

| Same 296 matches, 2025–26 | Log loss | Brier | ROC-AUC |
|---|---:|---:|---:|
| Poisson challenger | 0.534229 | 0.175435 | 0.579625 |
| Original logistic v1 | 0.540205 | 0.177592 | 0.514641 |
| Earlier league-frequency baseline | 0.539195 | 0.177043 | See frozen v1 report |

Lower log loss and Brier are better. There were no missing v1 match IDs in the comparison. Targets, kickoff, T−60 cutoff and baseline values were checked for every shared match before comparison.

On those 296 matches, challenger-minus-baseline log-loss difference was **-0.004967**, with weekly-block 95% interval **[-0.011328, +0.002323]**. It spans zero. Against the original logistic model, the weekly interval was **[-0.011802, -0.000098]**, while the fortnightly interval was **[-0.013276, +0.000435]**. That sensitivity prevents a robust improvement claim, even before considering the already-inspected archive.

Across both outer seasons, the challenger produced 582 predictions: 448 positive and 134 negative outcomes. Pooled log loss was 0.537596 against baseline 0.540203; Brier was 0.176463 against 0.177462; ROC-AUC was 0.545701. The pooled weekly loss-difference interval was **[-0.009201, +0.005096]** and the fortnightly interval **[-0.008964, +0.005505]**, both spanning zero. These are pooled results of a predeclared selection procedure, not one model configuration fitted to every season.

Mean pooled prediction was 0.775136 versus observed incidence 0.769759. The 2025–26 diagnostic calibration slope was about 2.123 and the pooled slope about 0.806; modest ranking improvement does not establish stable calibration. The final year still has only 68 negative outcomes. Do not tune on these diagnostics and claim the same seasons as confirmation.

## What was fitted

Home and away first-half counts were modeled separately with regularized Poisson regression: league intercepts plus training-vocabulary team attack/defence effects. Unknown team coefficients shrink to zero log effect; v1's minimum-history eligibility still applies. Probability of at least one goal follows `1-exp(-(lambda_home+lambda_away))`, an assumption-based transformation that still requires calibration and independent validation. Implementation uses the existing pinned scikit-learn package; the [official estimator documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.PoissonRegressor.html) describes its log link and L2 regularization.

Inner season 2023 selected alpha0.01/sigmoid for outer 2024; inner season2024 selected alpha0.1/sigmoid for outer2025. Each choice was sealed before that outer season's fitting/evaluation loop. Within every month, training preceded a separate two-year calibration period; earlier labels and feature histories both used a 24-hour availability lag. All three alpha values and both calibration views covered every inner validation match. All20 outer months fitted without a failed candidate or incomplete selected cohort. Count-residual diagnostics are saved per fold; they are descriptive and do not certify Poisson independence/dispersion assumptions.

The challenger explicitly uses a two-year minimum training span to permit early nested folds; v1 required three years. Evaluated cohorts are held identical, while fitting procedures differ. Settings and this difference were fixed before the challenger run and are documented in the plan.

143 of582 predictions involved at least one team absent from that fold's older training vocabulary. The declared league-intercept fallback applied to those team effects; they were not silently dropped. This is substantial shrinkage coverage, not evidence of reliable team-specific estimates for newly represented clubs. No calibration fallback occurred in the completed outer fits.

## Provenance and reproduction

The frozen protocol is `config/challenger-v2.json`, SHA-256 of its canonical JSON: `0ff479dd3485faf2260c8e887879f2beaeb5c12b4bfce636e1ff325bb5a134d6`.

The run folder contains actual normalized effective inputs, pre-fit generating code/configuration, raw snapshot identities, per-season selection seals, inner-fold coverage and losses, outer predictions, run state and report/comparator hashes. This is stronger provenance than the legacy experiments. Later fixes must preserve this original run and identify their scope; an archived source file, rather than a later working file, is the generating source.

From a fresh clone, follow README's environment/evidence-copy/import steps. The included report is already frozen; do not overwrite it. For a separately declared future version, preserve the old folder and change the protocol/implementation version intentionally before running. The command used for this version was:

```powershell
.\.venv\Scripts\python.exe challenger.py
```

The runner refuses an existing run directory, including a partial/failed run. The interface shows this evidence under **Backtest → Poisson challenger — exploratory**. Original v1 reports, source snapshots, corrected scores and operational forecast behavior remain unchanged.

## Final review corrections

The completed run's archived code is the exact pre-review generating source. Review subsequently separated identity and sigmoid fitting, so a future sigmoid convergence failure cannot discard an otherwise valid identity candidate. It also added direct fixture-ID validation at the model inference boundary. The recorded run had no fitting failures and used normalized valid IDs; neither correction changes its recorded successful-case predictions, and no retrospective rerun or retuning was performed.

The interface now shows both weekly and fortnightly comparison intervals, explicitly flags sensitivity to block length, and shows the pooled league-baseline uncertainty. Regression tests reproduce the failure paths and UI caveat. The final suite has48passing tests, including the populated comparison branch, instead of only an empty comparator. Hash checks confirm both original v1 and challenger report/code archives remain intact.

## Decision

**GO:** retain the Poisson approach as a research candidate and prepare a sealed future shadow protocol. **NO-GO:** release current-match probabilities, claim a proven improvement over the league baseline, infer value from unrecorded bookmaker odds, or place wagers.

The next stage requires a future, genuinely prospective data workflow, confirmed fixture identity/kickoff/status and a model/code seal before any eligible test match. Live-access conditions and current Nigeria rules remain unresolved. No future start date, individual prediction, booking code, ROI or automatic wager was created by this experiment.
