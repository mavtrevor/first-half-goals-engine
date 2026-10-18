# Model card: Bundesliga retrospective v1

Status: **unvalidated research; not released for current-match recommendations**.

Target: at least one goal by either team at first-half completion, including stoppage time. Only Bundesliga regulation league games; no live, virtual, youth or cup model.

Data: saved OpenLigaDB score snapshots, with 20 hash-bound, authority-supported HT corrections. Reference HT absence does not exclude a source-labeled row. Subsequent assisted desk review corroborated all 100 fixed-sample half-time scores against separate official publications; it does not establish upstream collection independence or population-wide accuracy. Historical publication timestamps and historical corrections were not reconstructed exactly.

Features: last-20 eligible league-match team scoring/conceding and nonzero frequencies; venue summaries with shrinkage; history counts. Inputs use earlier available results only. General scoring priors are pooled per-team league means; venue priors distinguish home and away. New/insufficient-history teams abstain. No current-match shots/cards, xG, injury feed or LLM estimates.

Availability: research forecasts are reconstructed at T−60 using a conservative 24-hour result lag. This cannot recreate every historic postponement, publication delay or correction. Current saved observations cannot be relabeled as past prospective observations.

Method: standardized logistic regression, C in {0.1, 1, 10}; identity versus regularized monotonic sigmoid calibration. Each month, training precedes a separate trailing two-year calibration period and then the test month. At least 500 calibration rows and 100 of each outcome are required. The base model/calibrator pair is frozen per test month. Development selected C=10 with sigmoid calibration; no subsequent tuning used the final holdout.

| Period | Eligible predictions | Model log loss | League baseline log loss | Model Brier | Baseline Brier |
|---|---:|---:|---:|---:|---:|
| Development 2024–25 | 286 | 0.539207 | 0.541245 | 0.177203 | 0.177895 |
| Sequential holdout 2025–26 | 296 | 0.540205 | 0.539195 | 0.177592 | 0.177043 |

Lower scores are better. The final holdout's paired weekly-block 95% interval for model-minus-baseline log loss is **[-0.005040, 0.007438]**; the fortnight-block interval is **[-0.004375, 0.007157]**. Both span zero. The model was slightly worse on both main holdout scores and has not demonstrated an improvement.

Holdout mean model probability was 0.77349 and the observed rate was 0.77027. A close overall mean is not enough: holdout ROC-AUC was about 0.515 and calibration slope about 0.199. The model provides little demonstrated ranking value. Only 68 negative outcomes occur in this final-period sample, which also limits supported calibration claims. Reliability-bin intervals describe bin frequency, not a guaranteed single-match probability interval.

The release rule remains failed: insufficient final-period sample/class counts for the stronger evidence gate, no clear baseline improvement, no prospective test and no legitimate SportyBet historical first-half prices. The completed fixed-sample official corroboration does not rescue this result. No return/ROI, daily picks, individual future confidence bounds, stake recommendation or accumulator probability was calculated.

Do not fix the result by tuning again on the same holdout. Any proposed challenger needs a new declared experiment and independent confirmation. A 48-hour availability-lag sensitivity is separate evidence and cannot rescue or replace a failed primary test.

The frozen v1 source and hashes are saved beside the report. Later source fixes are recorded separately and do not change these historical results silently.

The subsequent Poisson challenger is documented in challenger-v2-results.md. Its results on this inspected archive remain exploratory; they do not replace v1's original test or establish operational readiness.
