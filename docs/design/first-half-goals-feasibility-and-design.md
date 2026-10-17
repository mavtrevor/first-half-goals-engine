# First-Half Over 0.5 Goals Engine: feasibility and technical design

Research date: **17 October 2026**, Africa/Lagos. Status: **design only; no application or prediction model implemented**.

**Follow-up audit:** The subsequent phase-0 investigation found 20 incorrect half-time scores in the inspected OpenLigaDB archive, 15 of which change the binary prediction target. Official reports support the proposed corrections. See `phase-0-findings.md` and `verified-score-corrections.json` beside this report. The original structural-check counts below remain true, but they do not establish label correctness; application implementation remains on hold pending the documented gates.

## 1. Decision

**A local, zero-subscription research engine is technically feasible with a narrow initial scope: Bundesliga fixtures, historical half-time scores, independently validated probabilities, and manual SportyBet Nigeria verification. An unattended system that reliably checks SportyBet odds and generates booking codes is not established as feasible under the stated constraints.**

This is a personal research tool. Success means reproducible, calibrated forecasts and an honest record of availability and price, including days with no eligible matches. Success does not mean guaranteed winners, a fixed number of daily selections, or proven profit.

| Capability | Decision now | Release condition |
|---|---|---|
| Architecture and evaluation design | GO | Delivered here |
| Local Bundesliga research MVP | CONDITIONAL GO for a future build | User accepts scope; source access terms reviewed; full data audit passes |
| Publish model probabilities as validated forecasts | NO-GO today | Walk-forward and prospective calibration gates pass |
| Display other leagues | CONDITIONAL, later | Separate rights, history, completeness and calibration checks per league |
| Manual SportyBet market/odds observations | GO as a design | Human checks the Nigeria site/app; observations carry timestamps and evidence |
| Store a code generated manually on SportyBet | CONDITIONAL GO | Human reloads it and checks every selection; retain provenance |
| Automated SportyBet market checking or code creation | NO-GO | Reconsider only with written authorization, supported documentation and genuinely free access |
| Historical SportyBet profitability claims | NO-GO | No suitable free, timestamped first-half odds archive verified |
| Automated wager placement, deposits or account control | OUT OF SCOPE | No execution component is to be built |

No probabilities, accuracy figures, returns, or booking codes in this report are claimed as model results.

## 2. Current source investigation

Public documentation was researched and the OpenLigaDB API was read directly. No accounts were created, no authenticated provider entitlements were tested, no SportyBet private endpoints were invoked, and no wagers or booking codes were created. Some SportyBet pages render only JavaScript shells through direct web retrieval; relevant official search-indexed content is useful evidence of documented features, not a live operational test.

### Source comparison

| Source | Free capability supported by evidence | Limitation for this engine | Decision |
|---|---|---|---|
| **OpenLigaDB** | Documented public JSON API; no authentication; community-maintained fixtures/results; homepage states ODbL | Community quality and update delays; no service guarantee; coverage varies. Separate access-terms page did not render substantive text during this investigation | Preferred Bundesliga history and fixtures source, subject to access-terms review and audit |
| **football-data.org** | Free plan advertises 12 competitions, delayed scores/schedules, fixtures, tables and 10 calls/minute. API score schema includes `halfTime` | Schema is not proof of free-account field completeness or historical entitlement. Ten seasons of history are advertised in a paid package; do not assume those are free. Advanced statistics and odds have paid offerings | Optional current-fixture/result cross-check after free-key capability test; not the historical backbone |
| **API-Football / API-Sports** | Free plan advertises 100 requests/day, endpoints including fixtures, events, statistics and odds; no card required | Available seasons are restricted. Public pricing does not establish this user's current-season or multi-season entitlement, SportyBet coverage, or exact market availability | Optional candidate; reject for essential dependencies until account-level entitlement and terms are demonstrated |
| **Football-Data.co.uk** | Downloadable historical half-time results and match statistics across European divisions | Current data page restricts use to private individuals and explicitly flags commercial/data-training products using automated bots/scrapers/AI. This wording does not establish permission for the proposed automated training pipeline | Exclude pending written permission covering this exact use; manual download or a third-party mirror does not resolve it |
| **openfootball / football.json** | Repository declares CC0; fixtures/results; inspected English 2025–26 file contains some `score.ht` entries | Mixed score shapes and missing half-time fields appear in the same file. Daily JSON generation does not guarantee fresh upstream inputs | Possible corroboration/expansion source, not a complete half-time feed by assumption |
| **StatsBomb Open Data** | Selected competitions/seasons with event data, useful for research into first-half events | Not an all-league current fixtures feed; data agreement and publication attribution apply. Repository code availability does not establish unrestricted use of the data for this project | Optional separate research only after license fit is established; not needed for MVP |
| **Wyscout public research dataset** | Published event collection for one season of seven competitions, including major European leagues and international tournaments | Historical, narrow time span; cannot sustain current team form or multi-season live evaluation alone | Methodological reference; exclude from MVP dependency chain |
| **The Odds API** (`the-odds-api.com`) | Free starter advertises 500 credits/month and betting markets | Historical odds require paid access. SportyBet Nigeria plus this exact period/line was not verified | Optional external-book benchmark only if exact market is supported; not a SportyBet verifier |

Evidence: [OpenLigaDB](https://www.openligadb.de/), [OpenLigaDB API documentation](https://github.com/OpenLigaDB/OpenLigaDB-Samples), [ODbL](https://opendatacommons.org/licenses/odbl/1-0/), [football-data.org pricing](https://www.football-data.org/pricing), [coverage](https://www.football-data.org/coverage), [score semantics](https://docs.football-data.org/general/v4/overtime.html), [API-Football pricing](https://www.api-football.com/pricing), [Football-Data.co.uk usage notice](https://football-data.co.uk/data.php), [openfootball repository](https://github.com/openfootball/football.json), [inspected English file](https://github.com/openfootball/football.json/blob/master/2025-26/en.1.json), [StatsBomb repository](https://github.com/hudl/open-data), [Wyscout research collection](https://figshare.com/collections/Soccer_match_event_dataset/4415000/5), [The Odds API plans](https://the-odds-api.com/), [historical odds documentation](https://the-odds-api.com/liveapi/guides/v4/).

### Direct feasibility checks

Reads of `https://api.openligadb.de/getmatchdata/bl1/{starting_year}` at approximately **08:19–08:20 UTC / 09:19–09:20 WAT on 17 October 2026** returned:

| Season | Matches | Marked finished | Finished matches with exactly one explicit `HalfTime` result |
|---|---:|---:|---:|
| 2018–19 | 306 | 306 | 306 |
| 2019–20 | 306 | 306 | 306 |
| 2020–21 | 306 | 306 | 306 |
| 2021–22 | 306 | 306 | 306 |
| 2022–23 | 306 | 306 | 306 |
| 2023–24 | 306 | 306 | 306 |
| 2024–25 | 306 | 306 | 306 |
| 2025–26 | 306 | 306 | 306 |
| 2026–27, in progress | 306 | 46 | 46 |

Each inspected season had unique match IDs within that season. Basic checks found no finished match with a missing/duplicate half-time or regular-time result, null or negative half-time score, or a half-time team score exceeding its regular-time score. These are **2,448 completed historical matches plus 46 current-season finished matches**, not a claim that all scores are independently correct. Complete fixture coverage is not the same as confirmed kickoff accuracy, and unplayed fixtures may carry provisional times.

The accompanying audit file records counts and checks. It does not contain a fitted model or performance results. Checks did not exhaustively validate integer types, compare every score with an independent authority, reconstruct historical publication times, or certify all match statuses. A sampled raw record also had an anomalous goal-event entry inconsistent with its final score: **do not use the goal-event array to derive labels or features in MVP**.

OpenLigaDB introduced `resultTypeKind` in August 2026. Use `HalfTime` and `After90Minutes`; do not assume array order or numeric result IDs carry universal meaning. Older/unknown mappings require an explicitly reviewed league-season mapping or exclusion. [Provider announcement](https://github.com/OpenLigaDB/OpenLigaDB-Samples/discussions/136).

### Rights and zero-cost boundaries

Use only documented API reads or expressly licensed downloads. Maintain a source register with terms URL, reviewed date, permitted purpose, attribution, retention/export conditions, rate limits and allowed endpoints. OpenLigaDB's homepage permits automated retrieval and declares ODbL, but its separate license/access pages yielded only navigation/cookie content here. Reading the effective access conditions is a **pre-build operational gate**, not evidence that additional restrictions do or do not exist.

Retain OpenLigaDB attribution and license notices. If publishing a derived database or public product, review ODbL attribution/share-alike obligations before release; a private local database is the initial scope. Do not include team crests or other media on the assumption that a data license grants image rights. football-data.org requires visible attribution and imposes conditions on API keys and use after subscription cancellation. [Provider terms](https://www.football-data.org/client/register), [ODbL text](https://opendatacommons.org/licenses/odbl/1-0/).

“Zero cost” means no paid data, subscriptions, cloud hosting, domain, LLM API, GPU or paid trial. It assumes the user already has a computer, power and internet; development time and these existing resources are not free in an economic sense. No uptime guarantee when the computer sleeps. Do not enter billing information, auto-upgrade, evade quotas, rotate accounts, or replace blocked sources with undocumented access.

## 3. SportyBet Nigeria feasibility

The official Nigeria Code Hub describes selecting outcomes and using **Book bet** to obtain a booking code, and warns that odds or availability can change. This establishes a legitimate manual feature. It does not establish a third-party API, immutable prices, a guaranteed expiry period, login requirements, or successful code creation in this investigation. [Official Code Hub](https://mobile.sportybet.com/ng/m/code-hub/load-code).

No official public SportyBet Nigeria developer portal or supported third-party odds/booking API was located. That is a research finding, not proof that private partnerships cannot exist. Nigeria terms section G.7.1 reserves the ability to block automated or robotic activity; markets may also be suspended or removed. Therefore unattended browser automation, session/cookie replay and calls copied from web/mobile traffic are excluded. [Nigeria terms](https://www.sportybet.com/ng/help?nav=terms-and-conditions).

Third-party wrappers advertising SportyBet odds or code creation do not prove operator authorization. A wrapper's own claim that it calls undocumented web endpoints is a reason to reject it here, not a supported integration route. No such endpoints were tested. An affiliate arrangement alone would not establish permission to retrieve prices or create codes. [Example wrapper's own disclosure, reviewed only as evidence of its unsupported status](https://github.com/UbongErnest/Sportybet-mcp/blob/main/README.md).

Nigeria pages show a first-half O/U market category, but the exact **Over 0.5** selection must be checked per real fixture. Search-indexed pages can be stale and are not current odds observations. Do not substitute full-match O/U, team first-half totals, first-half corners, “rest of half,” virtual football or simulated matches. [Official Nigeria football page](https://mobile.sportybet.com/ng/m/sport/football/?source=sport_menu&time=all).

The model's target includes first-half stoppage time and excludes extra time/shoot-outs. The exact current Nigeria settlement provisions for abandoned/resumed games and exceptional first-half situations were **not fully verified** through the accessible pages. Capture the Nigeria rule text before marking a market compatible; do not borrow another country's rules. Unknown settlement remains `RULES_UNVERIFIED`.

Any future supported connector needs written confirmation of: Nigeria coverage; permitted read and code-generation operations separately; exact market semantics; documentation; authentication; quotas; caching/retention; permitted personal predictive use; code loading/expiry; and zero fees. The official support page lists `nigeria.support@sportybet.com`. **No contact was sent.** [Official contact reference](https://www.sportybet.com/ng/m/help/about/terms-and-conditions/complaints-disputes-governing-law-and-jurisdiction).

## 4. Selected architecture

Three approaches were considered:

1. **Local model plus manual SportyBet observations — selected.** Meets the budget; smallest dependable boundary; manual work limits volume.
2. Model plus authorized operator connector — conditional future option. Better freshness and less manual work, but authorization and free access are unestablished.
3. Unofficial all-in-one scrape/booking bot — rejected. Unsupported access, brittle semantics and no verified entitlement.

One local Python application, one SQLite database, immutable response files and a small browser interface are sufficient. Use Python's HTTP, JSON, CSV, hashing, logging and SQLite facilities; NumPy/scikit-learn for model fitting and evaluation; a lightweight local UI such as Streamlit. Pin compatible stable versions during a future build and record them. No Node frontend, message queue, microservices, hosted database or LLM prediction dependency is necessary.

```text
Documented football API
         |
         v
Raw snapshots + source register
         |
         v
Normalize identities, times, status, scores ---> quarantine / audit
         |
         v
SQLite versioned match history
         |
         +--> as-of features --> frozen model + calibrator --> forecast ledger
         |                                                    |
         +--> finalized outcomes --> evaluation                v
                                                        local shortlist
Human visits SportyBet Nigeria --> observation form -----------+
Human creates/reloads booking code --> code record ------------+
                                                              |
                                                     display / CSV export
```

### Component contracts

| Component | Inputs → outputs | Failure behavior |
|---|---|---|
| Source adapter | Approved endpoint + bounded date/season → response file, hash, retrieval metadata | Timeout/quota/schema error: keep last snapshot, flag stale, stop dependent verification |
| Normalizer | Raw response + versioned source mapping → fixture/result versions | Unknown result kind, ambiguous identity or malformed score: quarantine |
| Feature builder | Match ID + forecast cutoff + source snapshot set → numeric features and contributing match IDs | Missing history: explicit prior fallback or abstention |
| Trainer/evaluator | Frozen temporal folds + configuration → model, calibrator, metrics, manifest | Failed gates: retain research status; never silently promote |
| Forecaster | Approved model pair + valid features → immutable forecast or reasoned abstention | No valid model/data: probability is null, not a guessed percentage |
| Observation form | Human-entered exact event/market/price evidence → timestamped observation | Mismatch/unknown rule/stale quote: unavailable for value assessment |
| Booking register | Human-pasted code + selection manifest + reload check → provenance record | Cannot reload or mismatch: unverified/unusable code status |

### Minimum persistence schema

All timestamps are timezone-aware UTC internally; display Africa/Lagos/WAT. Keep local source time and zone only as provenance. Never reinterpret German local time as Lagos time.

| Table / artifact | Required fields |
|---|---|
| `sources` | source_id, documentation_url, terms_url, reviewed_at, rights_status, attribution, endpoints, request_budget |
| `snapshots` | snapshot_id, source_id, requested_url, retrieved_at, HTTP status, response_hash, file_path, parser_version |
| `teams`, `team_aliases` | internal_team_id; source team ID; competition/context; aliases; effective dates; review status |
| `fixtures` / versions | internal_match_id, source_match_id, competition, season, home/away IDs, kickoff_utc, kickoff_confirmed, status, observed_at, source_updated_at, snapshot_id |
| `results` / versions | match_id, ht_home, ht_away, regular_home, regular_away, completion status, result_kind, observed_at, snapshot_id, quality_state |
| `feature_snapshots` | feature_id, match_id, cutoff_at, schema_version, values, history counts, contributing IDs, input hashes, availability_mode |
| `model_runs` | run_id, algorithm, hyperparameters, training cutoff, training/calibration folds, code/config/data hashes, environment versions, seed, metrics, release_state |
| `forecasts` | forecast_id, match_id, generated_at, cutoff_at, kickoff_version, feature_id, model_run_id, raw_p, calibrated_p, uncertainty method/range, abstention_reason |
| `market_observations` | observation_id, forecast_id, operator=SportyBet, country=NG, human event identifier/URL, team names, kickoff, period=1H, statistic=goals, scope=match_total, line=0.5, side=over, decimal_odds, optional under_odds, market_status, observed_at, entered_at, expires_at, evidence_path, rules_version, verifier_type=human |
| `booking_records` | record_id, code, country=NG, origin=manual_official_UI, created/entered/reloaded_at, expiry_if_displayed, selection_manifest, manifest_hash, reload_match_state |
| `evaluation_ledger` | forecast_id, outcome version, outcome_state, model metrics, paper quote, paper unit result, settlement_rule_version, exclusion reason |

Unique source match keys include source and competition-season; do not deduplicate by team names alone. Revisions append a new version; original forecasts and quotes are never overwritten. SQLite transactions make ingest idempotent and tie a forecast to a consistent input set. Provider response status 200 with an empty result is not proof there are no fixtures until endpoint semantics and completeness are checked.

### Identity and freshness rules

For football sources, prefer stable provider IDs. SportyBet matching is human-confirmed: competition, exact senior teams, home/away order, kickoff and timezone must all match. Normalize accents and aliases only to suggest a match; fuzzy similarity cannot verify it. A changed kickoff or conflicting identity invalidates observations and forces review.

Initial local policy, to be validated rather than presented as a provider guarantee:

- Refresh the selected league on demand, cached for 15 minutes, with serial requests, a conservative one-request-per-second ceiling, bounded retries and exponential backoff. Honor any stricter provider limits and `Retry-After`.
- Check upcoming fixture data within six hours for research display, and within 15 minutes before a market check. Show retrieval age and kickoff uncertainty.
- Human quote validity is at most five minutes and ends sooner on kickoff/status/market/identity changes. `observed_at` is when the human saw the price, not when it was typed.
- At the five-minute pre-kickoff guard, or if the fixture may already have started, disable pre-match value/booking readiness. This is a conservative product rule, not a claim about operator acceptance.
- A suspended, missing, stale, live or ambiguous market has no usable price. Never fill a missing quote with a prior price.
- Cache completed seasons; obtain current-season changes in bounded requests. Optional providers get hard local quota budgets, with reserved capacity for necessary refreshes.

## 5. Model and calibration design

### Target and eligible population

For a real, regulation 11-a-side senior league match, define:

`Y = 1 if ht_home + ht_away >= 1, otherwise 0`.

Use finalized first-half scores, including stoppage time. Initially admit only Bundesliga league fixtures with confirmed identity, valid scores and adequate history. Exclude cups, friendlies, youth/reserve competitions, virtual games, abandoned/unresolved games and unsupported formats. A missing half-time result is unknown, never 0–0. Keep model outcome labels separate from bookmaker settlement states.

Primary evaluation horizon: **60 minutes before confirmed kickoff**. On-demand forecasts at other horizons may be shown as exploratory with the actual lead time; they do not inherit T−60 validation automatically. No live/in-play model.

### Baseline and candidates

Start with a trailing league baseline, then at most two candidates. Do not begin with an ensemble or complex neural model.

**B0 — league base rate.** Estimate a smoothed first-half-goal frequency from earlier eligible league matches: `(positive_count + 1) / (match_count + 2)`. A five-season maximum history and optional season weighting are predefined and tuned only on development folds. Report the underlying count. This is the comparison baseline, not evidence of a match-specific edge.

**M1 — regularized binary logistic regression, preferred first candidate.** Features available from prior half-time scores only:

- Each team's smoothed first-half goals scored/conceded per game over its last 20 eligible league matches.
- Smoothed first-half nonzero-goal frequency for each team's last 20 matches.
- Home team's home-only and away team's away-only scoring/conceding summaries, shrunk strongly toward the league venue baseline.
- History counts, promoted/new-team flags, and season-progress information available at the cutoff.

For a rate, use `(sum_of_counts + k * league_rate) / (n + k)`; for binary frequency use the analogous positive-count formula. Start `k=10`; compare only `k in {5,10,20}` within development. Tune logistic regularization over a small frozen grid. Standardize using training data only. Do not rebalance classes or oversample unless probability correction and independent validation justify it.

Use only same-league completed history in MVP. Every league prior and team summary for a training or prediction row must use strictly earlier available matches; never compute a full-season aggregate and attach it to earlier matches. Reserve an initial warm-up period where no suitable prior exists. Do not equate a promoted team's lower-division form with Bundesliga form. With fewer than 10 earlier eligible matches for either team, abstain from a match-specific shortlist; show a clearly labeled league baseline if useful. Venue rates with fewer than five matches revert to the league prior. These are initial design choices to test, not established optimal cutoffs.

**M2 — first-half Poisson challenger.** Fit regularized home/away first-half goal intensities using league intercept, home advantage and shrinkage-based team attack/defence effects:

`log(lambda_home) = mu + home_advantage + attack_home + defence_away`

`log(lambda_away) = mu + attack_away + defence_home`

`P(Y=1) = 1 - exp(-(lambda_home + lambda_away))`.

Apply identification constraints and regularization. The last expression assumes independent Poisson home/away counts; score dependence and dispersion may invalidate it. Promote M2 only if it improves out-of-time scores and calibration; its mathematical form is not a guarantee.

Do not use the current match's shots, red cards, score, final statistics or post-match lineups. MVP excludes xG, injuries, player ratings and head-to-head “streak” features because reliable, as-of free coverage has not been established. No LLM generates probabilities or fills missing statistics.

### As-of integrity

Every contributing result must have been available before the forecast cutoff. For future operation, enforce `observed_at <= cutoff`; use only valid completed records observed by then. Results for matches with the same kickoff cannot inform one another.

Historical downloads retrieved today do not establish when each score became public. Historical backtests must be labeled **retrospective reconstruction**. Use only earlier calendar-day results with a conservative 24-hour availability lag from kickoff where publication times are unknown; quarantine uncertain completion cases and sensitivity-test a 48-hour lag. This reduces leakage risk but does not recreate historical corrections or postponement announcements. Do not use a provider's current `lastUpdated` timestamp as if it were original publication time. Prospective snapshots are needed for a true point-in-time test.

### Calibration

Fit each calibrator on chronologically later, held-out predictions from a frozen model. Default candidate: regularized sigmoid calibration of the clipped raw log-odds, `p_cal = sigmoid(a * logit(p_raw) + b)`, with monotonicity retained. Compare against identity calibration; never assume calibration improves an already calibrated logistic model.

Require at least 500 calibration observations and 100 observations of each outcome for the pooled sigmoid fit; otherwise retain baseline/research status and gather more data. These are proposed minimums, not statistical guarantees. Consider isotonic only with at least 1,000 representative calibration observations, adequate observations across the probability range, and a demonstrated later-period improvement. Fit per-league calibrators only when that league independently meets requirements; do not borrow a pooled claim without subgroup evidence.

Use chronological blocks or explicit forward folds; do not accept default randomized/stratified cross-validation. Scikit-learn documents the need for calibration data independent of model fitting and the small-sample overfitting risk of isotonic regression. [Calibration documentation](https://scikit-learn.org/stable/modules/calibration.html).

Report reliability diagrams with counts and uncertainty, calibration intercept/slope, mean prediction versus observed frequency, Brier score and log loss. ECE is descriptive and bin-dependent. Neither AUC nor a lower Brier score alone proves calibration.

For uncertainty, use week-block resampling of development/training/calibration data, refitting the full pipeline. Display ranges as **model-estimation sensitivity**, not a guaranteed interval for the next match. Suppress extreme confidence when similar-probability bins have little support. Never clip predictions upward to make a shortlist look stronger.

## 6. Walk-forward backtesting protocol

Pre-register the target, eligible league, horizon, exclusions, feature grid, calibration choice rules, decision thresholds, primary metrics and stop criteria before fitting. Preserve the protocol hash and record every subsequent experiment.

### Chronology

The inspected history permits a concrete starting schedule:

1. Use 2018–19 through 2021–22 as initial model-training history (up to 1,224 matches before feature warm-up/exclusions).
2. Freeze that candidate and create held-out predictions across 2022–23 and 2023–24 for calibration (up to 612 observations). Feature histories can incorporate earlier observed results as time advances; model coefficients stay frozen for this calibration stream.
3. Evaluate development on successive monthly blocks of 2024–25. At each month boundary, reserve the immediately preceding 24 calendar months for calibration and use up to five years of available history before that for training, with at least three years required. The inspected archive begins in August 2018; never assume an uninspected earlier season exists. Generate the calibration stream using that frozen model; fit its calibrator; then score only the next month. Use the actual match dates, not matchday numbers, and keep the season boundaries explicit.
4. Choose all features, hyperparameters, recalibration and selection policies using these development results only. Seal them before touching 2025–26 outcomes for evaluation.
5. Run 2025–26 as a final sequential holdout. Monthly refits may use only information then available, including earlier holdout outcomes if that online-refit rule was fixed beforehand. No tuning in response to holdout performance. Label this a prequential/online-updating holdout, not a single untouched static model test.
6. Treat 2026–27 matches already finished on the research date as retrospective. Start genuinely prospective evaluation only after forecasts and source/quote snapshots are being recorded in real time.

For each monthly refit: training ends before calibration starts; calibration ends before the test month; no outcome crosses the cutoff. A complete model/calibrator pair is frozen for the test block. Do not refit the base model on its calibration data and keep the old calibrator. If calibration counts or either-class minimum fail, skip promotion for that fold. During all periods, emit a prediction before evaluating the outcome. Date-window splits need custom handling for irregular football schedules; generic equal-row splits are insufficient. [Temporal split documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

### Metrics and selection bias

Calculate on all eligible forecasts first, then separately on the exact shortlist:

- Log loss and Brier score, with paired differences versus B0.
- Reliability bins (five equal-frequency bins initially, each at least 100 observations; reduce bins or mark insufficient), calibration intercept/slope and counts.
- ROC-AUC as secondary discrimination evidence; accuracy/hit rate only with base-rate and selection-count context.
- Coverage: total fixtures, score availability, history exclusions, valid forecasts, human-checked markets, available exact markets, quote expirations and final eligible selections.
- Season/month breakdown, newly promoted-team breakdown, probability range and missingness. Annotate pandemic-era schedule/attendance shifts; sensitivity-test excluding those seasons without choosing the best-looking result afterward.
- Both all-forecast and selected-subset calibration; choosing only high predictions changes the evaluated population.

Use paired week-block bootstrap intervals, preserving predictions/outcomes together; show a sensitivity analysis with longer blocks because teams recur across weeks. Intervals describe sampling uncertainty under the chosen scheme, not protection against all future drift. Do not count tuning experiments as independent confirmation or keep retesting the final holdout until a model passes.

### Odds and return testing

Historical score data support outcome forecasting evaluation. They do **not** support a SportyBet return calculation without the exact SportyBet NG 1H O0.5 price, availability and timestamp at the predeclared decision time. Never substitute full-time goals odds, another bookmaker, a closing quote observed later, current prices for past matches, or plausible synthetic odds.

Prospectively record every candidate and every attempted market check, including missing/suspended markets and failures. Observe quotes independently of later outcomes; keep a manual checked-universe log to expose cherry-picking. Track one paper decision per match at the first valid observation in the predefined T−60 ±5-minute window; if the window is missed, record a miss rather than backfill it.

With decimal odds `o`, calibrated probability `p`, and one paper unit:

- Break-even probability = `1/o`.
- Fair model odds = `1/p`.
- Expected net paper return = `p*o - 1`.
- Realized paper return = `o-1` for a win, `-1` for a loss, `0` for a confirmed void; unknown/disputed settlement stays pending.

If both over and under quotes are captured for the same event, time, period and line, a simple margin-normalized reference is `(1/o_over) / ((1/o_over)+(1/o_under))`. It is a market benchmark, not a true probability. A single quote does not reveal the margin.

Track paper ROI, units, price distribution, longest losing sequence and maximum drawdown, with week-block intervals. Mark these as quoted-price paper results: no actual execution was tested. Stress-test quotes reduced by 0.02 decimal odds as an explicitly hypothetical sensitivity, plus actual unavailability/expired-quote exclusion. Do not describe a later human quote as an actual wager price. Closing-line comparison is optional only if the same-market closing observations can be obtained legitimately; absence is reported.

### Proposed model release gates

All thresholds below are **pre-build policy proposals**, not achieved results or universal proofs:

- Data: at least 99% valid HT coverage in each admitted historical season, no unresolved duplicate/identity/score contradictions in the admitted set, and 100 manually cross-checked matches sampled across seasons, including 0–0 and nonzero halves. Investigate every disagreement; systematically biased exclusions fail the gate.
- Model: at least two out-of-time seasons overall, at least 500 out-of-time forecasts and 100 in each outcome; final-season evaluation remains mandatory. The one-season final holdout alone is not a large-sample certification.
- Improvement: out-of-time Brier and log loss beat the league baseline; 95% paired block-bootstrap interval for log-loss difference lies below zero. If evidence is inconclusive, retain B0/research status, not a claim of superior prediction.
- Calibration: overall mean prediction differs from observed frequency by no more than 0.03; supported reliability bins show no absolute gap above 0.05. Show uncertainty and slope/intercept; small bins cannot pass by omission. Predeclare sparse-range abstentions.
- Prospective operation: at least 12 weeks and 200 frozen eligible forecasts, whichever takes longer, with satisfactory calibration/data freshness and no leakage. With one small league this can take much of a season.
- Price/selection claims: separately require at least 300 valid prospective paper selections and a positive 95% week-block-bootstrap lower bound for ROI after the predeclared price sensitivity, with supported calibration in the selected range. Below that, or if the bound spans zero: **edge unproven**. This gate can take multiple seasons and never authorizes automated wagering.

Failure leads to a narrower league/range, a baseline display, more paper observation, or stopping the model. No threshold is relaxed after seeing a failed holdout without declaring a new experiment and collecting new confirmation data.

## 7. Odds and availability verification workflow

1. **Generate a research candidate.** Require current fixture identity, confirmed kickoff, valid history and an eligible released/research model state. Save the forecast before any outcome exists. Display probability status, history counts, source age and actual horizon.
2. **Human opens SportyBet Nigeria.** Use the official site/app; the engine does not log in or automate navigation. Human selects the real fixture and confirms competition, teams, home/away and kickoff against the local record.
3. **Confirm exact market semantics.** Match-level total goals from both teams, period first half, line 0.5, over, pre-match, active. Record both operator wording and normalized fields. Current Nigeria rules must be verified and versioned. Any ambiguity blocks eligibility.
4. **Capture price and evidence.** Enter decimal odds, observed time, status and optional under price. Attach a cropped screenshot or manual record without account details. Validate finite decimal odds greater than 1. An event link is stored only when copied from the official interface; do not construct undocumented deep links.
5. **Assess research value.** Show break-even and estimated return only with a fresh valid quote and model status. Initial paper-selection rule: conservative model-sensitivity lower estimate times odds minus one must exceed 0.03, and the forecast must lie in a supported calibration range. This 3% buffer is a proposed paper policy, not proof of an edge. Freeze it on development data and evaluate it prospectively.
6. **Expire automatically.** Any elapsed TTL, changed kickoff, changed selection, changed quote, suspension or near-kickoff lock removes readiness. Preserve old observations as history. Recheck instead of guessing.
7. **Human optionally uses Book bet.** Only the operator UI generates the code. Paste the code and exact selection manifest into the local tool. A code is a reference to selections, not evidence that a wager was placed or that original prices remain available.
8. **Human reloads the code in Nigeria's official interface.** Compare every leg, period, line, outcome, current price and availability. Record the reload time and complete match result. Missing/changed legs block readiness; never silently substitute another market. If the operator displays expiry, record it; otherwise expiry is unknown.
9. **Record later outcomes separately.** Model label comes from validated finalized HT data. Operator settlement is manually verified where needed. An abandoned game's completed half might have a measurable label while its operator settlement differs; preserve both.

Suggested status fields are separate, rather than a misleading single “verified” flag:

`forecast_state = research | validated | abstained`

`market_state = unchecked | human_observed | rules_unverified | unavailable | stale | mismatch`

`code_state = none | pasted_unverified | human_reload_matched | mismatch | expired_or_unloadable`

`edge_state = untested | paper_tracking | insufficient_evidence | supported_in_test`

“Human observed at 09:35 WAT” is the UI wording; it must not imply continuous machine verification. A booking code can remain stored after its quotes have expired, but no current-price/readiness badge survives without a fresh check. Do not multiply individual probabilities into an accumulator win probability or advertise a “safe combined odds” target.

## 8. Risk controls

| Risk | Required control |
|---|---|
| Leakage or corrected historical records | As-of input snapshots, explicit retrospective label, conservative availability lag, frozen prospective ledger |
| Inaccurate community data | Schema checks, independent score sampling, quarantine conflicts; use HT score slots rather than suspect event arrays |
| Misidentified teams/markets | Stable IDs where available; human confirmation; competition/period/line checks; reject virtual and youth games |
| Too little data / promoted teams | Shrinkage, history thresholds, limited probability support and abstention |
| Drift and overconfidence | Rolling calibration monitoring, baseline comparison, model freeze/demotion and clear sample counts |
| Stale prices or fixture times | Timestamped observations, explicit TTL, kickoff version invalidation, no stale-price fallback |
| Selection bias | Log all candidates, attempted checks, unavailable markets, skipped windows and reasons |
| Accumulator exposure | Single-match research evaluation; code manifest has no modeled combined win probability; no forced leg count |
| Gambling harm | Paper-only default; no stake optimizer, Kelly/Martingale, loss chasing, deposit nudges or profit guarantees. If the user independently wagers, fixed personal loss/time limits and operator controls remain separate |
| Credentials and privacy | No SportyBet passwords, cookies, OTPs, phone numbers or payment details stored; redact screenshots; local data only; optional data keys kept outside source/export files |
| API abuse or accidental spend | Approved host/endpoint list, cached serial requests, quota hard stops, backoff, no billing-enabled fallback |
| False verification | Source and verifier labels; null for unknown fields; codes only from operator UI; no inferred bookings |
| Public redistribution | Local personal scope; source attribution; license review before database/model/data publication |

The interface should show a clear “No eligible matches” state, not manufacture candidates to satisfy a daily quota. Adult use only; respect self-exclusion and never offer an alternate-account workaround. SportyBet documents responsible-gaming and self-exclusion features. [Official responsible-gaming page](https://shop.sportybet.com/ng/help?nav=responsible-gaming).

Operational monitoring: retain per-run freshness, missingness, request errors and abstentions. For every newly finalized set, update evaluation without retraining mid-block. Review trailing 200 forecasts where available. A mean calibration gap above 0.05 triggers a review; persistent deterioration across two monthly reviews demotes the model. Severe schema/identity/leakage errors stop predictions immediately. Small samples remain “insufficient evidence,” not healthy by default.

## 9. Phased build plan and acceptance

These are implementation work packages, not authorization to start them. Times are rough active-development estimates for a single developer; prospective collection time is separate.

| Phase | Work and deliverable | Acceptance / next decision |
|---|---|---|
| **0. Close feasibility gates** | Review effective OpenLigaDB access terms; freeze Bundesliga scope; independently check 100 historical scores and a sample of upcoming fixtures; inspect Nigeria settlement rules and manual Book bet/reload flow without placing a wager; freeze evaluation protocol | GO research build only if access and required fields/semantics are supported. SportyBet automation remains disabled regardless of manual success |
| **1. Data foundation** (~2–4 days) | One documented adapter, raw snapshot store, source register, versioned SQLite records, audit report | Idempotent ingest; known duplicates/nulls/unknown result kinds are rejected; UTC/DST tests pass; provenance and correction versions retained |
| **2. Forecast research** (~3–5 days) | B0 and M1 first; as-of features; monthly walk-forward runner; held-out calibrator; model card. M2 only if needed | Temporal leakage assertions pass; frozen configurations reproduce outputs; failed release gates leave research status |
| **3. Local review interface** (~2–3 days) | Fixture/candidate view, probability evidence, manual SportyBet observation form, quote expiry, code manifest/register, CSV export | No wager capability; wrong period/line/team and stale evidence fail closed; code cannot become reload-matched without explicit human check |
| **4. Prospective paper operation** (minimum 12 weeks and 200 forecasts) | Immutable forecasts at fixed horizon, all-check ledger, freshness/error monitoring and paper outcomes | Forecast operational gate passes or remain research-only. No profit claim from hit rate |
| **5. Selection-value assessment** (at least 300 valid paper selections) | Quoted-price return report, calibration of selected subset, uncertainty and sensitivity analysis | Pass predeclared evidence gate or mark edge unproven. This is not permission to automate wagers |
| **6. Optional expansion** | Add one league at a time, or an operator-authorized connector if one becomes freely available | Independent source/rights/field/calibration gates; supported API contract and explicit permission before any SportyBet automation |

### Necessary acceptance scenarios

- A valid 0–0 HT result is a negative label; absent HT stays unknown. First-half stoppage-time goals count when present in the final HT score.
- Reordering result arrays changes nothing. Unknown result semantics, duplicate IDs and HT greater than regular-time score are quarantined.
- A new/promoted team does not acquire lower-league form by name similarity.
- A postponed match preserves prior fixture/forecast versions; rescheduling invalidates market observations. Same-kickoff results never leak between fixtures.
- Loading a historical backtest with future observations deliberately inserted fails the availability assertions.
- A finished match lacking a finalized usable label is pending/excluded, never automatically a loss or a void.
- “Over 0.5” under full-time or team goals fails the exact-market contract. Live/virtual markets fail eligibility.
- Quota/timeout/empty-response/schema failure cannot turn cached data into a fresh successful verification.
- A changed quote, stale timestamp, incorrect code manifest or missing reload leg blocks readiness. No partial silently altered slip is accepted.
- Every displayed probability traces to data, feature, model and calibrator versions; missing model means null probability.
- The application has no SportyBet credentials, wager endpoint or automatic outbound booking mutation.

## 10. Outstanding feasibility questions and final recommendation

Unresolved: effective OpenLigaDB access-terms text; independent score correctness beyond basic consistency checks; current kickoff/status reliability; authenticated free-tier entitlements for optional providers; exact current Nigeria settlement edge cases; manual code expiry/login/load behavior; and any operator-authorized free third-party API. No model skill, calibration quality or profitable selection strategy has been demonstrated.

**Proceed only with a Bundesliga-first, local, paper-research MVP after the phase-0 checks. Preserve manual SportyBet verification and code capture as the supported integration boundary. Do not build automatic odds scraping, unattended code creation, automated wagering, or a product promising profitable predictions.**

Research and this written design are complete. Application implementation, fitting, backtesting and wagering were intentionally not performed.
