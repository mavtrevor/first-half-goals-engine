# Model diagnosis and next experiment

17 October 2026. Descriptive analysis of the existing frozen v1 predictions only. No model was fitted, parameters changed or holdout rerun. Numeric results are saved in `evidence/v1-diagnostic-summary.json`, bound to the original report hash.

## What the saved results show

The fixed-sample score review found no additional label corrections. That removes a sample-level corroboration gap, but it does not explain away the model's weak test.

| Frozen 2025–26 result | Value |
|---|---:|
| Eligible predictions | 296 |
| Positive / negative outcomes | 228 / 68 |
| ROC-AUC | 0.5146 |
| Model log loss | 0.540205 |
| League baseline log loss | 0.539195 |
| Model-minus-baseline loss | +0.001010 |
| Weekly-block 95% interval for that difference | [-0.005040, +0.007438] |
| Mean model probability on positive outcomes | 0.773535 |
| Mean model probability on negative outcomes | 0.773327 |
| Central 90% of model probabilities | 0.731339–0.812735 |
| Mean absolute model deviation from baseline | 0.021634 |

The model assigned almost the same average score to halves that had goals and halves that did not. Its average model score was higher than the baseline in 193 of 296 matches. On positive outcomes, that change improved mean log loss by 0.012022; on negative outcomes it worsened mean log loss by 0.044704. The weighted total was slightly worse. These are descriptive outcome-conditioned results, not a rule for selecting future matches.

Development selected C=10 with sigmoid calibration, but its development log loss improved over C=1 with sigmoid by only about 0.000064. This is weak evidence for a reliably optimal setting. All 20 monthly folds were evaluated; the result was not caused by skipped folds. The training/calibration/test counts and saved exclusions remain available for inspection. Historical publication times were reconstructed and insufficient-history fixtures were excluded, so coverage still matters.

**Diagnosis supported by the evidence:** the released research candidate has little demonstrated match-ranking value and its small deviations from the league baseline did not help on the final period. A close overall average probability does not establish useful discrimination. A positive monotonic calibration transform preserves ordering within a frozen monthly pair, so calibration alone cannot manufacture missing within-month ranking information. Different monthly transforms can affect an aggregate cross-month ranking.

**Unproven hypotheses:** last-20 score summaries may be too noisy, useful team/opponent structure may be insufficiently represented, and the data regime may have shifted. The current results cannot distinguish those causes. Adding xG, injuries or more complex algorithms is not justified by this audit, and no free comprehensive feed for those features has been established.

## Concrete decisions

1. **NO-GO: promote v1 or claim a profitable edge.** Preserve its failed/inconclusive evaluation, including the legacy feature-lag-only sensitivity limitation.
2. **GO: an explicitly labelled retrospective development experiment.** Previously inspected seasons, including 2025–26 and already viewed 2026–27 results, may be used for development only. They cannot become a fresh confirmatory test for a challenger designed after seeing these results.
3. **NO-GO: call another run on 2025–26 an untouched holdout.** Any such result is exploratory.
4. **CONDITIONAL GO: future research-only shadow evaluation.** Before recording predictions, freeze the full challenger protocol and code; establish lawful data access or a documented manual source workflow; confirm fixture identity/time/status; and retain input snapshots actually available by the forecast cutoff. This is not operational betting release and contains no wager action.

## Proposed challenger specification, not yet an executed experiment

Use one transparent opponent-adjusted first-half count model alongside the unchanged league-frequency baseline. Fit a regularized Poisson model separately for home and away first-half goal counts, using league intercepts and team attack/defence effects; derive the probability of at least one goal as `1 - exp(-(lambda_home + lambda_away))`. This is a modelling assumption, not an empirical guarantee: independence/dispersion and calibration must be evaluated. Reuse the current score archive and existing packages. Do not assume the challenger is better or present a sample probability without fitting.

Before implementation, fix the exact regularization grid, training window/decay, promoted-team shrinkage, calibration method/window, minimum class counts, timestamp lag and all abstention rules in a versioned protocol. Select them only through nested chronological development folds, and compare against v1 and the league baseline on identical eligible cohorts. Report all coverage/exclusions; keep the promoted-team minimum-history requirement unless a new rule is separately validated. The current runner supports only its frozen logistic protocol, so a challenger requires a separately versioned runner rather than changing its recorded settings.

For a future confirmatory protocol, keep T−60 prediction timing, no retrospective snapshots masquerading as past observations, and distinct earlier training / later calibration / still-later test periods. Record both model and baseline predictions before kickoff. A prediction window missed, an unconfirmed kickoff, or a late input means abstention. Corrections after the cutoff enter only later versions. Do not inspect accumulating test metrics to keep choosing models or stop when results look favourable.

The earliest eligible confirmatory match must be **after** the future protocol/code seal and after verified inputs can be recorded prospectively. No retroactive start date is assigned here. The existing evidence rule requires at least 500 eligible final-period predictions and at least 100 outcomes of each class; one Bundesliga season has only 306 scheduled matches, so it cannot satisfy the 500-prediction rule on its own. Set the evaluation endpoint as the end of the first complete predeclared season after those sample/class minima have been reached; decide that stopping rule before collection. If results remain inconclusive, report that outcome rather than resetting the test.

Use the existing paired week-block loss comparison, fortnight-block sensitivity, Brier score and supported calibration checks. Any selection threshold or price-edge rule must be chosen on development data and declared before the future test. Genuine SportyBet odds/availability observations and settlement rules are separate requirements for value analysis; a probability-only research test cannot establish betting profitability.

**Next implementation gate:** approve/freeze that complete challenger protocol and resolve the actual prospective data workflow. No challenger code, new predictions, bookmaker integration or wagering was added in this stage.
