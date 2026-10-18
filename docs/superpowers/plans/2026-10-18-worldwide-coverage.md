# Worldwide League Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development only if the user chooses delegation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the existing app to actually admitted worldwide free feeds, with Top 20/50 selection controls and league-specific probability evidence that cannot be bypassed to fill a list.

**Architecture:** Keep live worldwide data in a separate append-only store and preserve the Bundesliga research pipeline. Provider adapters share one validated event format and request budget. Ship fixture discovery as the first independently usable milestone; the dependent history/model milestone adds shadow evaluation and releases no numerical probability without league-specific evidence.

**Tech Stack:** Existing pinned Python, Streamlit, NumPy and scikit-learn; Python standard-library urllib, sqlite3, hashlib, json, datetime and zoneinfo. No new package or paid service.

**Spec:** `docs/superpowers/specs/2026-10-18-worldwide-coverage-design.md`, approved by the user on 18 October 2026. User-facing copy: `outputs/worldwide-expansion-design.md` in the parent workspace.

## Global Constraints

- “Zero subscriptions, legitimate documented interfaces, no unsupported scraping, no fabricated probabilities and no automated wagering remain binding constraints.”
- “Preserve all existing snapshots, score corrections, original code archives and backtest reports byte-for-byte.”
- “Today is the default window; Tomorrow and Next 7 days remain separate choices.”
- “Top 20 means at most 20 eligible estimates, not a promise of 20 winners or even 20 available estimates every day.”
- “Credentials go in Streamlit Secrets, never Git, browser code, CSV exports, logs or chat.”
- Use the approved five-season maximum history, 500 training observations spanning two years, later 500 calibration observations with 100 of each class, minimum 10 prior league games per team and at least 24-hour historical availability lag.
- Existing Bundesliga model release stays false. Unknown HT remains unknown. No Football-Data.co.uk ingestion, unreviewed TheSportsDB adapter, bookmaker client, staking, paid upgrade or new scheduler.
- Free tokens are user-supplied through Streamlit Secrets as FOOTBALL_DATA_TOKEN and API_FOOTBALL_KEY. Do not search unrelated files for credentials or print their values. Missing credentials do not block coding/tests or the existing feed, but block authenticated live acceptance for that provider.
- Existing suitable clean `research/offline` checkout may be reused; inspect repository status and attached worktrees before execution. Do not overwrite user changes. Runtime/private data stays ignored.

## Review Focus

1. Provider returns HTTP 200 with an error envelope, an inaccessible current season, or a partial page: show the reason and never claim complete coverage (Task 2).
2. Reruns, parallel sessions and Cloud restarts exhaust a shared quota: fail closed on unknown remaining allowance and reserve requests atomically, rather than resetting a fictitious daily allowance (Task 1).
3. Two providers describe the same game differently, or reuse numeric IDs: keep provider IDs distinct and select one authority per mapped competition; no duplicate ranked selection (Tasks 1 and 3).
4. Delayed or revised scores arrive after the forecast: keep forecast input versions fixed and score only after an actually observed completed result, without rewriting past predictions (Tasks 4 and 6).
5. Only 7 eligible estimates exist, a league has fixtures but no HT history, or a candidate was tuned after its test: show the actual count, missing probability reasons, and unreleased status (Tasks 3 and 5).

## Files and interfaces

Create `worldwide_store.py` (private append-only snapshots, observations and request accounting), `providers.py` (documented read-only clients/normalizers), `worldwide.py` (catalog, authority selection, date filtering and row selection), `worldwide_research.py` (history validation and chronological evaluation), and `worldwide_forecasts.py` (shadow records and evidence checks). Add corresponding five test modules. Keep `live.py`, `features.py`, `backtest.py`, `challenger.py`, `poisson_model.py`, `forecast.py` and frozen evidence unchanged unless a demonstrated compatibility defect needs a separately tested fix.

Modify `app.py`, `tests/test_app_contracts.py`, README and deployment instructions only for the new flow. Create `config/worldwide-sources.json`, `config/worldwide-protocol.json`, `docs/worldwide-coverage.md` and `docs/worldwide-acceptance.md`. Do not add unconfigured future provider packages or frontend frameworks.

Common event dictionary: `event_id` (`provider:source_event_id`), `provider`, `source_event_id`, `competition_id` (`provider:source_competition_id`), `season_id`, `country`, `region`, `home_id`, `away_id` (provider-qualified), `home`, `away`, `kickoff` (aware UTC ISO), `status`, `ht_home`, `ht_away`, `ft_home`, `ft_away`, `target`, `observed_at`, `snapshot_hash`, `source_url`, `classification`, `quality`. `classification` is reviewed senior real football or unknown; `target` is integer 0/1 only for structurally valid explicit completed HT/FT, otherwise None. Raw snapshots retain rejected rows with sanitized reasons.

Feed dictionary: `provider`, `state`, `events`, `rejections`, `observed_at`, `source_url`, `snapshot_hash`, `quota`, `complete`, `reason`. Allowed states: `ready`, `missing_key`, `access_denied`, `season_unavailable`, `quota_exhausted`, `quota_unknown`, `source_unavailable`, `invalid_response`. `ready` alone does not imply model readiness. Never put a token or raw authentication error body in this dictionary.

## Milestone A: wider fixture discovery

### Task 1: private snapshot storage and bounded request accounting

**Files:** Create `worldwide_store.py`, `tests/test_worldwide_store.py`.

**Interfaces:** `connect_worldwide(path: Path) -> sqlite3.Connection`; `save_feed(db, feed: dict, raw: bytes) -> str` returns snapshot digest; `observations(db, competition_id: str, as_of: datetime) -> list[dict]`; `reserve_request(db, provider: str, now: datetime, allowance: dict) -> bool`. Allowance holds provider-confirmed remaining/reset timestamps and local minute ceiling; secrets are never stored.

- [ ] Write failing tests: same digest is idempotent; changed payload is a new version; `observations(..., as_of=T)` excludes rows observed after T; two providers' event `123` do not collide; malformed rows are quarantined; two independent SQLite connections cannot spend the last allowance twice; expired/absent provider budget returns False; reopening an empty database does not grant 100 requests; raw/private records never enter export helpers.
- [ ] Run `.venv/Scripts/python.exe -m unittest tests.test_worldwide_store -v`; expect import/missing-function failure before implementation.
- [ ] Implement isolated tables in `data/worldwide.sqlite`, UTC version queries, digest validation and transactions with `BEGIN IMMEDIATE` for reservations. A provider quota header/status response can establish remaining allowance; fresh authentication checks are rate-limited separately and not granted an invented fixture budget. Maintain provider cooldowns and a safety reserve of 10 requests/day for API-Football; reserve at most 90 for application data. Unknown server quota or an ambiguous reset blocks application requests. A missing durable Cloud file triggers a fresh authoritative check, not a quota reset claim.
- [ ] Run this test module; expect all pass. Commit only this module/tests with `feat: preserve worldwide snapshots and request budgets`.

### Task 2: official provider clients and current-season entitlement checks

**Files:** Create `providers.py`, `config/worldwide-sources.json`, `tests/test_providers.py`.

**Interfaces:** `read_json(provider: str, path: str, params: dict, token: str, now: datetime, db) -> tuple[dict, dict]` returns sanitized parsed payload and response/quota metadata; `catalog(provider: str, token: str|None, now: datetime, db) -> dict`; `fixtures(provider: str, token: str|None, start: date, end: date, competitions: list[dict], now: datetime, db) -> list[dict]` returns feed dictionaries. `normalize_event(provider: str, raw: dict, observed_at: datetime, metadata: dict) -> dict` produces the common event format.

- [ ] Write failing mocked-response tests: missing token makes no request; TLS redirect to a different host does not carry a token; 401/403/429 and 200-error envelopes become distinct feed states; retry headers are honored without a blocking retry loop; null HT never yields target=0; 0–0 explicit HT remains a negative example; booleans/negative scores, naive kickoff and mixed competition/season are quarantined; live/postponed/abandoned/awarded games never become prematch candidates; pagination errors mark `complete=False`; tokens are absent from every failure string, exception and stored metadata.
- [ ] Run `.venv/Scripts/python.exe -m unittest tests.test_providers -v`; expect failure before implementation.
- [ ] Implement fixed HTTPS hosts `api.football-data.org/v4` and `v3.football.api-sports.io`; no arbitrary URLs or dynamic auth redirects. Use 15-second timeouts, 2MB response bounds, at most one attempt per request, response-header cooldowns and rate-limited subsequent user retries. Cache catalogs for 24 hours, fixtures/failures for 5 minutes and finished historical responses for 24 hours. Reserve before each actual request, including pagination. Do not truncate pages and claim a full league.
- [ ] football-data.org: use documented `/competitions`, `/competitions/{id}` and date-filtered `/matches`; authenticate using X-Auth-Token. Restrict the initial domestic candidate codes to PL, ELC, BL1, PD, SA, FL1, DED, PPL and BSA according to current published free coverage, and verify actual permission per competition/season. Correct the specification's count typo: this list contains nine domestic leagues, not eight. Catalog visibility alone is not a successful fixture entitlement check. Use X-RequestsAvailable/X-RequestCounter-Reset and cap to 10 requests/minute. No paid add-on endpoint.
- [ ] API-Football direct: use documented `/status`, `/leagues` and date/league/season-filtered `/fixtures`, authenticate using x-apisports-key. Confirm active Free subscription, available season and actual fixture access; do not infer current access from `current=true` or a historical league catalog. Inspect `errors` even on HTTP 200. Use documented provider quota headers/status. If authenticated samples do not establish quota/reset or season access, keep provider unavailable and document the precise result. No paid signup or terms acceptance by the agent.
- [ ] Country targets include all six regions from the approved specification, using source-provided IDs and country metadata. Reviewed senior classification and region mapping live in the source config; unknown competitions remain unavailable for ranking until reviewed. Do not infer senior/women/youth identity from names alone. Returned documented free entitlements, not an arbitrary country filter, determine active coverage.
- [ ] Run tests; expect all pass. Commit `feat: add entitlement-aware free football provider clients`.

### Task 3: worldwide finder and deployed fixture view

**Files:** Create `worldwide.py`, `tests/test_worldwide.py`; modify `app.py`, `tests/test_app_contracts.py`, README; create `docs/worldwide-coverage.md`.

**Interfaces:** `collect_feeds(tokens: dict, now: datetime, start: date, end: date, db) -> list[dict]`; `select_fixtures(feeds: list[dict], now: datetime, window: str, regions: list[str], competitions: list[str]) -> list[dict]`; `rank_estimates(rows: list[dict], limit: int|None) -> list[dict]`. Ranking rows add `probability`, `probability_state`, `probability_reason`, `model_id`, `sample_sizes`, `generated_at`. Initially probability is None and reason is `league_model_unvalidated`. `rank_estimates` accepts only `probability_state='released'` with finite 0<=p<=1 and deterministic probability/kickoff/event-ID ordering.

- [ ] Write failing tests for Nigeria midnight, tomorrow boundaries, UTC season changes, no fixtures, partial provider failure, duplicate source IDs and exactly seven released rows under a Top-20 limit. Fixtures without estimates must remain visible in All fixtures. Mixed available/unavailable providers must not crash the page or claim absent countries as active. AppTest must show current Bundesliga when both tokens are missing, Top 20/50/All controls, Today default and no invented probabilities. Personal-record histories remain hidden by default.
- [ ] Run `.venv/Scripts/python.exe -m unittest tests.test_worldwide tests.test_app_contracts -v`; expect failure for new behavior.
- [ ] Adapt the existing Bundesliga feed to the common event schema in the collector without changing its historical normalizer. Prefer OpenLigaDB for Bundesliga, football-data.org for its other admitted mapped leagues, API-Football only for remaining admitted reviewed competitions. Configure one authority per mapped competition; never merge by fuzzy names. Exclude unknown/ambiguous mappings from ranked selection, label them clearly in provider diagnostics. Eliminate repeated same-provider event IDs.
- [ ] Read secrets only server-side, with missing-key handling. Add All fixtures / Eligible estimates views, region/league selectors and Today/Tomorrow/Next 7 days. Preserve 14/30-day options only if the selected provider legitimately supports them within quota; otherwise give the supported-window explanation. Fetch an expanded UTC date envelope, then filter exact WAT dates locally. Top-20 selection is per Nigeria calendar day; a 7-day view shows separate daily groups rather than hiding other days behind one global cap.
- [ ] Show all required row metadata and a detail expander for sample/model provenance. Export the visible rows with existing CSV formula protection and attribution/retrieval fields. Show source coverage and failure reasons in plain language; no raw secret-bearing messages. Keep Backtest/Data audit/manual guards and report fallback intact. List actually live countries separately from coverage targets.
- [ ] Run tests and the full existing suite. Commit `feat: show worldwide fixtures and honest estimate coverage`.

## Milestone B: league-specific history and shadow probability evidence

### Task 4: immutable historical inputs and scoped fitting identities

**Files:** Extend `providers.py`, `worldwide_store.py`; create `worldwide_research.py`, `tests/test_worldwide_research.py`.

**Interfaces:** `import_history(db, provider: str, competition: dict, season_ids: list[str], token: str|None, now: datetime) -> dict`; `league_rows(db, competition_id: str, cutoff: datetime, mode: str) -> list[dict]`; `count_inputs(rows: list[dict], identity_map: dict, cutoff: datetime) -> tuple[list[dict], dict]`. Mode is `retrospective` or `observed`; identity map assigns deterministic local positive integers per competition to satisfy existing count-model interfaces and archives the reversible provider-qualified mapping.

- [ ] Write failing tests for mixed leagues/seasons, unavailable/partial history, minimum history, null HTs, unresolved score revisions and chronology: a corrected result observed after a prospective cutoff must not change the earlier input set. Target fixture outcome cannot affect its own features. Two providers' identically numbered teams map differently. An archive replay yields identical hashes, IDs and evidence.
- [ ] Run `.venv/Scripts/python.exe -m unittest tests.test_worldwide_research -v`; expect failure before implementation.
- [ ] Import only expressly allowed history seasons through the same rate-limited clients. No historical-publication timestamp is invented from a result's kickoff. Retrospective reconstructions apply 24-hour lag and explicitly retain the reconstruction label; observed mode requires actual observed_at<=cutoff, finished status and a structurally valid result. Missing or contested score evidence blocks affected labels. Capture code/protocol/input hashes before fitting and reject existing run directories. Five-season history bounds and minimum per-team history apply within the same league only.
- [ ] Run tests, then commit `feat: archive scoped worldwide half-time research inputs`.

### Task 5: frozen per-league protocol and chronological evaluation

**Files:** Extend `worldwide_research.py`; create `config/worldwide-protocol.json`; extend `tests/test_worldwide_research.py`.

**Interfaces:** `evaluate_league(rows: list[dict], protocol: dict, output: Path) -> dict`; `assess_evidence(report: dict) -> dict`. Report includes scope, protocol/input hashes, inner selection seals, outer monthly predictions, baseline comparisons, weekly/fortnightly uncertainty, calibration diagnostics, per-day Top-20 cohort metrics, exclusions, retrospective/prospective provenance and an always-false initial `operational_release`.

- [ ] Write failing tests for the spec's 500/730-day training, later 500/100-per-class calibration and 10 prior games/team; training/calibration overlap; future labels; missing negative halves; same-team IDs; wrong model/calibrator lineage; no unseen-team probability release; retuned or previously inspected evaluation periods. Top-20 evaluation must rank before inspecting outcomes, grouped by WAT date and preserving simultaneous kickoffs. Unsupported protocol changes must fail explicitly.
- [ ] Run the research test module; expect new tests to fail.
- [ ] Freeze a versioned protocol before inspecting any new league outcomes: five-year history, two-year calibration window, alpha grid [0.01,0.1,1], calibration [identity,sigmoid], T−60, 24-hour lag, monthly refits, seed42 and 1000 week/fortnight block resamples. Pick earlier inner development season and later outer season by available complete seasons, record that selection before fitting, and never label already examined data untouched. Minimum selection/test requirements that cannot be satisfied yield `insufficient_history`, not relaxed thresholds.
- [ ] Reuse `fit_counts`, `predict_counts`, existing metrics and block comparison helpers with the archived scoped integer mappings. Keep source event IDs beside every prediction. Fit each calibration candidate independently; exclude failed/incomplete candidates from selection, never from reported coverage. Save LL/Brier, class counts, reliability, slope/intercept and daily Top-20 coverage. Existing Bundesliga results remain unchanged.
- [ ] `assess_evidence` reports data/model limitations and always returns not released while prospective evidence and a separately preregistered league release protocol are absent. Do not invent a prospective performance threshold after seeing its outcomes: creating and approving that confirmatory protocol is an explicit later evidence step, not a hidden bool or this plan's claim of success.
- [ ] Run tests and commit `feat: evaluate worldwide league models without premature release`.

### Task 6: prospective shadow records and enforceable release boundary

**Files:** Create `worldwide_forecasts.py`, `tests/test_worldwide_forecasts.py`; extend `worldwide_store.py` and `app.py` for evidence status only.

**Interfaces:** `record_shadow(db, event: dict, pair: dict|None, inputs: dict, now: datetime) -> dict`; `settle_shadow(db, event: dict, result: dict, now: datetime) -> dict`; `public_estimate(shadow: dict, evidence: dict, now: datetime) -> dict`. Shadow records contain generated_at, supported T−60 window, source/input/model hashes and raw/calibrated estimates only when fitting/inference checks pass; abstentions contain no numeric estimates.

- [ ] Write failing tests: a request outside 55–65 minutes before kickoff cannot masquerade as a T−60 observation; late-arriving inputs cannot enter a past forecast; a changed kickoff/model invalidates eligibility; repeated refresh preserves original forecast bytes; changed results append settlement revisions; no default/manual boolean, missing report or failed league report unlocks a public percentage. A shadow estimate exists privately while the main table still shows unavailable. Started/postponed fixtures are not eligible.
- [ ] Run `.venv/Scripts/python.exe -m unittest tests.test_worldwide_forecasts -v`; expect failure before implementation.
- [ ] Implement manual CLI collection via `worldwide_research.py shadow` and an explicit private-local action using the same constraints; no autonomous scheduler or public trigger for fitting large models. Collection only runs when the user invokes it; document that unattended prospective coverage needs a separately supported execution arrangement. No dependency on a Streamlit background thread remaining alive.
- [ ] Default public estimates remain unavailable. Expose no public runtime toggle to declare a league validated. Future release requires hashed retrospective and prospective records, a preregistered confirmatory protocol and explicit evidence review; report all currently missing requirements. Do not claim the implementation itself supplies prospective evidence or 20 released probabilities today.
- [ ] Run tests and commit `feat: preserve shadow forecasts and enforce league release evidence`.

### Task 7: live entitlement acceptance, review and publication

**Files:** Create `docs/worldwide-acceptance.md`; update README and coverage documentation. No secrets or personal runtime data are committed.

- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -v`; expect existing 53 and all new relevant tests pass. Verify frozen manifests/digests, no accidental `.venv`, data, SQLite, logs or secret files in tracked changes, and `git -c core.whitespace=cr-at-eol diff --check`. Do not rewrite frozen CRLF evidence to silence whitespace tooling.
- [ ] Inspect configured key presence without displaying values. If absent, complete all code, mock-based tests and review; give the user exact Streamlit Secrets names/setup instructions and leave authenticated acceptance explicitly pending. Account creation/terms acceptance belongs to the user; never accept paid upgrades. Missing keys do not justify abandoning implementable work.
- [ ] With user-configured free credentials, perform a quota-bounded catalog/entitlement check and one current non-European domestic feed request, preferring Brazil. Store sanitized access/HT-completeness findings privately and publish only non-sensitive aggregate evidence. A 403, old-only season or null HT history is a no-go for that capability, not a cue to bypass restrictions or guess. Record actual countries, fixture counts and retrieval times, not advertised catalog totals.
- [ ] Under the selected execution skill, run one fresh final review of the completed changes. Fix important findings with a failing regression followed by a passing suite. Review Focus items all have tests above; self-review scope includes token leakage, quota restarts, status mapping and probability claims. Avoid repetitive per-task reviews in native execution.
- [ ] Publish reviewed source to the already-authorized GitHub repository using a compare-and-swap branch update, preserving user commits. Let existing Streamlit auto-deployment rebuild. Verify its actual page: missing-key fallback, active source status, Nigeria date filters, count before limit, correct probabilities-unavailable reasons, source attribution and private-record protection. Save a screenshot in the parent outputs folder.
- [ ] Claim fixture expansion delivered only after at least one non-European current domestic league is visibly returned; otherwise report the exact provider/setup blocker while keeping Bundesliga working. Claim no released probability feature while prospective model gates remain pending. Record final commits, tests, live acceptance scope and unresolved evidence in the handoff.

## Execution decision and prerequisites

Recommended method: **Native** — implement in this session using the existing isolated branch, one tested task at a time, then one final independent review. The tasks share event/storage interfaces, so this avoids repeated context setup and overlapping edits. No implementation agent is spawned unless the user selects delegated execution; final review follows the chosen skill.

No provider account/key is required to approve this plan or complete the code/test milestones. Keys are required to verify additional live feeds and historical entitlements. More regions cannot honestly be promised if current free-season access is unavailable. A working worldwide fixture collector may precede numerical probabilities by a substantial prospective evidence period.

Self-review completed: approved spec sections map to Tasks1–7; all five Review Focus conditions have owning tests; common IDs, feed shape and function signatures match between tasks. Specification count correction (nine rather than eight listed domestic leagues) is a factual correction only, not an expansion to paid coverage. No product code, dependency, account or deployment has been changed while preparing this plan.
