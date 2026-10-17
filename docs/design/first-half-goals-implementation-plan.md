# First-Half Goals Research MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Implementation is not yet authorized by this document and remains subject to feasibility gates and user plan review.

**Goal:** Build a local Bundesliga research application with auditable forecasts, temporal evaluation and manual SportyBet Nigeria observation/code records.

**Architecture:** One Python application, versioned SQLite records, immutable source snapshots, a frozen model/calibrator pair and a local Streamlit interface. Approved football API reads are the only automated external access; SportyBet observations and code provenance are entered by a human.

**Tech Stack:** Python, SQLite, NumPy, scikit-learn, Streamlit, standard-library unittest. Use a project-local environment, no paid services and no separate frontend.

**Spec:** `outputs/first-half-goals-feasibility-and-design.md`, supplemented by `outputs/phase-0-findings.md`. The addendum takes precedence for current gate status and identified data defects.

## Global constraints

- No application code, scaffolding, model fitting or dependency installation before plan review and the phase-0 gates below.
- Personal local use, initially Bundesliga (`bl1`) only; display Africa/Lagos and persist timezone-aware UTC.
- No paid data, paid trials, cloud hosting, LLM prediction API or billing-enabled fallback.
- No SportyBet scraping, undocumented endpoint access, browser automation, login, credentials, deposits or wagering.
- No fabricated probabilities, historical odds, booking codes, freshness or verification status.
- Missing HT is unknown; raw snapshots and prior forecast versions are immutable.
- Review all 20 known score corrections; handle all 126 reference-HT gaps visibly; do not selectively discard goalless draws.
- T−60 is the evaluation horizon; other forecast horizons are exploratory. Market TTL is at most five minutes; lock readiness five minutes before kickoff.
- Model, prospective operation and price-value release gates remain separate. Until passed, all model outputs retain research status and no profitable-edge claim is available.
- All product files will live under `outputs/first-half-goals-engine/`; intermediate research stays under `work/`. Do not create the product directory until execution starts.

## Review focus

1. A changed upstream score must not receive a stale correction merely because its match ID is unchanged; Task 1 tests original-score/hash binding.
2. Excluding missing reference HT fields must not silently remove goalless matches; Task 1 tests missingness reporting separately from label admission.
3. A changed kickoff or local DST conversion must not leave an observation apparently fresh; Tasks 1 and 5 test UTC handling and fixture-version invalidation.
4. A base model refitted after calibration must never reuse an incompatible calibrator; Task 3 tests the frozen pair's lineage.
5. A pasted booking code or missed paper-decision window must never become a verified slip or backfilled historical decision; Tasks 4 and 5 test these transitions.

## Task 0: Close feasibility gates

**Inputs:** phase-0 findings, fixed 100-match sample, source documentation and correction ledger.

**Outputs:** `docs/feasibility-acceptance.md` inside the future product, prepared only once the evidence exists. It records source/terms versions, reviewed independent sample, current fixture checks, Nigeria rules and manual-code workflow outcomes. Pending evidence is not marked accepted.

- [x] Compare all 2,448 historical records across the two published archives.
- [x] Research all 20 discrepancies against official league/club evidence and save proposed corrections.
- [x] Generate the fixed 100-match audit sample and expose missing-reference bias.
- [ ] Obtain readable effective OpenLigaDB API access conditions; confirm the intended identified, cached, low-frequency personal research client fits them. Record actual contact configuration without inventing an address.
- [ ] Complete independent manual checks for the selected 100 matches, retaining unresolved records and all evidence URLs; do not silently replace the 17 missing-reference sample rows.
- [ ] Compare at least ten current or upcoming fixture identities/times/statuses across the next available matchdays with an authoritative schedule; record provisional times instead of certifying them.
- [ ] Verify current Nigeria first-half market settlement rules and a human-operated Book bet/reload path without placing a wager. Record unavailable/login/expiry behavior truthfully.
- [ ] Confirm the proposed correction/quarantine and missingness policy does not introduce systematic bias. If a gate cannot be satisfied, keep the application build on hold and revise the scope explicitly rather than relaxing the gate.
- [ ] User reviews this implementation plan. Default recommendation: implement directly in this chat; no delegated work is necessary for this small application.

## Task 1: Auditable data foundation

**Create:** `data.py`, `schema.sql`, `tests/test_data.py`, `tests/fixtures/`, `config/source-policy.json`, `README.md`, `.gitignore` and `requirements.txt` in the product root.

**Interfaces:**

- `normalize_match(raw: dict, observed_at: datetime) -> dict`: validated IDs, UTC kickoff, result semantics, scores and quality state.
- `ingest_snapshot(db: sqlite3.Connection, payload: bytes, metadata: dict) -> int`: snapshot ID and append-only normalized versions.
- `resolve_result(raw_match: dict, override: dict | None, snapshot_hash: str) -> dict`: effective result plus original/override lineage.
- `refresh_bundesliga(db: sqlite3.Connection, season: int, now: datetime) -> dict`: approved documented API fetch or explicit cache/error status.

- [ ] Write failing unittest cases for shuffled result arrays, null/negative/noninteger/bool scores, HT above FT, duplicate IDs, missing UTC timezone, rejected redirects outside the approved host and an unsupported league.
- [ ] Add idempotent-ingest and transaction rollback tests; confirm a corrected upstream record cannot match an obsolete override. Explicitly test that the 126 missing-reference rows remain visible in quality reporting.
- [ ] Run `python -m unittest tests.test_data -v`; confirm the new cases fail before implementation.
- [ ] Implement the schema/contracts with raw SHA-256 snapshots, versioned aliases/results and original-score/hash-checked corrections. Keep provider errors separate from legitimate empty responses.
- [ ] Implement cached serial HTTP reads with application User-Agent, local one-request-per-second ceiling, at most three retries for retryable reads, bounded timeout and stricter provider limits if required. Never auto-fetch SportyBet.
- [ ] Verify tests pass; ingest the existing inspected snapshots through the same boundary and produce a data-quality report with all overrides and exclusions listed.
- [ ] Record compatible dependency versions, project-local setup and data attribution; no API credentials or generated data in source control. Use Git commits only if a repository is created for this product during approved execution.

## Task 2: Features and baseline

**Create:** `features.py`, `tests/test_features.py`.

**Consumes:** Task 1's append-only fixture/result records and effective result provenance.

**Produces:** `build_features(db: sqlite3.Connection, match_id: int, cutoff: datetime, mode: str) -> dict` and `league_baseline(history: list[dict]) -> float | None`.

- [ ] Write failing tests with simultaneous fixtures, a future result, a subsequently corrected result and a promoted team. Assert no contributing record violates the cutoff; insufficient history gives abstention.
- [ ] Assert baseline `(positives+1)/(matches+2)`, last-20 team histories, `k=10` default smoothing, fewer-than-ten team-history abstention and fewer-than-five venue-history prior fallback.
- [ ] Run `python -m unittest tests.test_features -v`; confirm failure before implementation.
- [ ] Implement only score-derived features and their contributing IDs/hashes. Retrospective mode uses the spec's conservative 24-hour lag, with 48-hour sensitivity available in evaluation; prospective mode uses actual observed timestamps.
- [ ] Rerun tests and inspect a representative feature provenance record. Empty warm-up history is never assigned a fabricated prior.

## Task 3: Model/calibration and chronological evaluation

**Create:** `model.py`, `backtest.py`, `tests/test_model.py`, `tests/test_backtest.py`, `config/evaluation-protocol.json`.

**Consumes:** `build_features(...)` and frozen eligible records.

**Produces:** `fit_pair(train_rows: list[dict], calibration_rows: list[dict], config: dict) -> dict`, `predict_pair(pair: dict, feature_row: dict) -> dict`, and `walk_forward(db: sqlite3.Connection, protocol: dict) -> dict`.

- [ ] Write failing tests for overlapping train/calibration/test periods, same-kickoff leakage, future labels, fewer than 500 calibration rows or 100 of either class, NaN probabilities and incompatible model/calibrator manifests.
- [ ] Test a shuffled input set gives the same date-defined folds and that failed evidence thresholds preserve research status. Test the final holdout configuration is sealed before its evaluation.
- [ ] Run `python -m unittest tests.test_model tests.test_backtest -v`; confirm intended failures.
- [ ] Implement B0 and regularized M1 logistic regression only, using train-only scaling, the small spec-defined development grids and identity-versus-sigmoid calibration. Defer Poisson M2 unless evidence justifies a challenger.
- [ ] Implement the spec's 2018–22 training start, 2022–24 calibration stream, monthly 2024–25 development and sealed sequential 2025–26 holdout. Each refit uses at least three and at most five years of available training history before the trailing 24-month calibration window.
- [ ] Produce log loss/Brier baseline comparisons, reliability/counts, intercept/slope, subgroup/coverage reports and paired week-block uncertainty with longer-block sensitivity. Save every experiment/configuration hash.
- [ ] Rerun tests and the actual retrospective backtest. Publish the actual report even when the baseline wins or promotion fails; never keep tuning on the final holdout. No ROI is calculated without legitimate recorded SportyBet quotes.

## Task 4: Forecast and paper-evaluation ledger

**Create:** `forecast.py`, `evaluation.py`, `tests/test_forecast.py`, `tests/test_evaluation.py`.

**Consumes:** frozen pair and Task 2 feature snapshots; finalized Task 1 results.

**Produces:** `record_forecast(db: sqlite3.Connection, match_id: int, now: datetime) -> dict` and `evaluate_finalized(db: sqlite3.Connection, now: datetime) -> dict`.

- [ ] Write failing tests for no model, stale or unconfirmed fixture, missed T−60 ±5-minute paper window, duplicate paper decisions and post-kickoff entry. Null probability and explicit reasons are required where appropriate.
- [ ] Test outcomes append separately from model labels and operator settlement; unknown/disputed settlements remain pending, with no simulated loss/void conversion.
- [ ] Run `python -m unittest tests.test_forecast tests.test_evaluation -v`; confirm failure before implementation.
- [ ] Implement immutable forecast IDs, manifests, actual lead times, one paper decision per match and honest research/validated/abstained states. No retrospective forecast is represented as prospectively recorded.
- [ ] Implement actual quoted-price paper returns only, count all exclusions, retain raw observations and separate forecast/operation/value gate reports.
- [ ] Verify tests and generated ledger traces. Prospective release requires at least 12 weeks and 200 eligible frozen forecasts; value evidence needs at least 300 valid selections and the spec's uncertainty/calibration checks.

## Task 5: Manual SportyBet observations and code provenance

**Create:** `observations.py`, `tests/test_observations.py`.

**Consumes:** fixture version and saved forecast.

**Produces:** `record_observation(db: sqlite3.Connection, observation: dict, now: datetime) -> dict`, `observation_state(observation: dict, fixture: dict, now: datetime) -> str`, and `record_booking(db: sqlite3.Connection, booking: dict, now: datetime) -> dict`.

- [ ] Write failing tests for NG/country mismatch, swapped teams, full-time/team/corners markets, virtual/live events, non-0.5 lines, invalid/NaN odds, future observation time, TTL above five minutes, missing rules evidence and the five-minute kickoff lock.
- [ ] Test changed kickoff versions invalidate observations; a pasted code starts unverified; explicit human reload plus exact manifest match is required for reload-matched status. Unknown expiry stays unknown.
- [ ] Run `python -m unittest tests.test_observations -v`; confirm expected failure.
- [ ] Implement form-boundary validation and append-only records; store cropped evidence only under the data folder, with size/type checks, no client-controlled paths and no account details. If evidence media support is deferred, use a clearly labeled human observation record rather than pretending a screenshot exists.
- [ ] Implement the break-even and quoted-price research calculations from the spec. A 3% conservative sensitivity buffer remains a paper policy; missing uncertainty support cannot become an edge claim.
- [ ] Verify all transitions. A code may be retained when quotes expire, but no current-price/readiness badge survives without a fresh valid check. No probability multiplication for accumulators.

## Task 6: Local interface, full verification and handoff

**Create:** `app.py`, `tests/test_app_contracts.py`, `docs/model-card.md`, `docs/operator-checklist.md`, `docs/validation-report.md` and `launch.ps1`.

**Consumes:** Tasks 1–5's public functions; no duplicate inference or verification logic in UI code.

**Produces:** a local-only browser application and documented launch command.

- [ ] Write failing UI-contract tests for no fixtures, no eligible matches, absent trained model, expired quote, unavailable rules and unverified booking code. Require source age, research status, WAT times and explicit verifier wording.
- [ ] Run `python -m unittest tests.test_app_contracts -v`; confirm failure before implementation.
- [ ] Build fixture/candidate, data-quality, model-evidence and manual-observation views. Bind to loopback; keep framework CSRF protections; no public share link, telemetry-dependent service or SportyBet session integration.
- [ ] Install only compatible pinned free dependencies into the project-local environment. `launch.ps1` verifies the interpreter/environment and opens the local app without modifying global packages.
- [ ] Run `python -m unittest discover -s tests -v`, compile checks and the frozen retrospective evaluation; record exact results in the validation report.
- [ ] Inspect the actual browser interface at narrow and desktop widths, including keyboard labels, no-data/errors and stale-status states. Any UI test unable to run is explicitly reported rather than marked passed.
- [ ] Review the source for forbidden outbound hosts, secret storage and wager/code-generation mutations; verify CSV export and model lineage. Provide a source bundle, launch instructions, model card and honest remaining evidence requirements.

## Execution decision

This plan is ready for review; implementation has not started. Direct execution in this chat is recommended because one local application has closely shared interfaces and the data gates need careful sequential handling. User plan approval and the remaining feasibility evidence are separate requirements. Neither permits bypassing provider terms, substituting other-country settlement rules or advertising untested model performance.
