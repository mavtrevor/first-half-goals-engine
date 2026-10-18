# Delivery and review record

Updated 2026-10-18: current Bundesliga fixture retrieval is enabled through the documented OpenLigaDB read-only API. Fresh Streamlit Cloud deployments need no local database to find games or read bundled reports. See `live-fixture-fix.md` for the narrow source-access ruling, caching, validation and shared-deployment restrictions. This supersedes the earlier offline-only access ruling below. Operational probabilities, bookmaker verification, booking-code generation and automated wagering remain disabled. No profitable-edge claim is justified.

## Scope rulings and costs

1. Saved OpenLigaDB evidence supports offline construction; unresolved effective access conditions block a live adapter. Cost: saved fixtures can be stale.
2. Offline construction and retrospective research proceeded while the independent score audit remains pending. Cost: estimates may change after that audit; no operational release is allowed.
3. The projectless workspace had no existing repository, so a dedicated local repository was initialized. Cost: its original local history is separate from the GitHub initialization; GitHub receives a complete reviewed snapshot.
4. A project-local Python environment reuses installed numerical packages, with pinned versions documented. Cost: reproduction requires the recorded runtime/dependencies. No paid services were introduced.
5. The 48-hour legacy experiment is explicitly feature-lag-only because its label split still used 24 hours. Cost: it cannot substantiate a full 48-hour sensitivity claim. Frozen files are preserved, not overwritten.

## Final independent review

Four P2 findings were addressed in one fix pass: reject changed correction provenance for identical snapshot bytes; apply availability lag to future label splits; reject unsupported protocol fields/settings; archive effective inputs and code before future experiments. Regression tests demonstrated the failures before fixes. All 34 tests pass, including UI smoke tests. Streamlit emits the expected bare-mode ScriptRunContext warning under its test harness.

The original v1 source/manifest and legacy sensitivity report retain their historical provenance limitations, described in README. No new archive is claimed to have generated old results. Subsequent assisted desk review corroborated all100fixed-sample HT scores against separate official publications, with no new score changes; see score-audit-findings.md for retrieval and independence limits. Provider permissions, current Nigeria settlement rules and prospective validation remain unresolved.

## Challenger stage, 18 October 2026

Poisson v2 was implemented under the user's next instruction to proceed and run once as nested retrospective research. Its582outer predictions improve descriptively on the baseline, but paired baseline intervals span zero. The296match comparison to v1 also depends on block length. See challenger-v2-results.md for the actual numbers and limitations. No operational prediction was released.

Rulings: reuse the existing isolated research checkout and authorized private-repository workflow (cost: separate local/remote histories); use a declared two-year minimum training span for early inner folds (cost: fitting procedures differ from v1); preserve all inspected seasons as exploratory (cost: future evidence still requires time). Full protocol, effective inputs and generating code were archived before fitting. Team-effect fallback applied on143of582predictions.

The one fresh final review found calibration-candidate failure coupling, incomplete on-screen uncertainty disclosure, and missing fixture-ID validation in the direct inference helper. All three were fixed with failing-then-passing regression checks; the fixture-ID issue was treated as an important validation-boundary requirement despite the current runner already supplying valid IDs. The final suite passes48tests; no review minors remain deferred. Original frozen successful-case results were not overwritten or rerun.

Review limits stand: prospective performance/profitability, provider rights, upstream collection independence and empirical count-independence assumptions remain unproven. Those uncertainties keep release blocked. Frozen hash verification, tests and browser inspection establish implementation evidence, not predictive or legal validation.

The GitHub delivery excludes `.venv/`, private SQLite databases, personal observations/code references, logs and secrets. Public historical inputs and fixed research reports are included under `evidence/`; design documents are under `docs/design/`.

Headroom's configured local proxy was unavailable. Work continued using bounded direct inspection; it did not transparently proxy all tool traffic. No unsupported scraping, bookmaker endpoint calls or automatic wagering were used.
