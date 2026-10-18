# Worldwide First-Half Goals Engine — expansion specification

Date: 18 October 2026. Status: proposed specification for user review; no worldwide deployment claimed.

## Intended result

Expand the existing Bundesliga app to discover football fixtures worldwide. Offer Top 20, Top 50 and All eligible games, with Nigeria kickoff times and estimated first-half Over 0.5 probabilities wherever supported by adequate evidence. Today is the default window; Tomorrow and Next 7 days remain separate choices. A short day is not padded with invented fixtures, duplicate games or invented percentages. Top 20 means at most 20 eligible estimates, not a promise of 20 winners or even 20 available estimates every day.

The user approved the multi-league direction with the amendment “add other leagues from all around the world.” This document captures that wider scope. Zero subscriptions, legitimate documented interfaces, no unsupported scraping, no fabricated probabilities and no automated wagering remain binding constraints.

## Coverage and source decisions

Use a small provider registry and discover actual competition/season entitlements. A region or league name in this specification is a coverage target, not proof that a current free feed exists.

| Region | Requested coverage targets | Initial status |
|---|---|---|
| Europe | Premier League, Championship, Bundesliga, La Liga, Serie A, Ligue 1, Eredivisie, Portugal; other entitled senior leagues | Bundesliga current feed exists; other feeds require a free account and checks |
| South America | Brazil, Argentina, Colombia, Chile and other supported leagues | Brazil listed in football-data.org free coverage; remaining leagues conditional |
| North/Central America | USA/Canada MLS, Mexico and other supported senior leagues | Candidate global provider coverage; current free-season access unverified |
| Africa | Nigeria, South Africa, Egypt, Morocco, Tunisia and other supported senior leagues | Candidate global provider coverage; current free-season access and HT history unverified |
| Asia | Japan, South Korea, China, Saudi Arabia and other supported leagues | Candidate global provider coverage; current free-season access and HT history unverified |
| Oceania | Australia, New Zealand and other supported leagues | Candidate global provider coverage; current free-season access and HT history unverified |

Source choices, reviewed against official pages:

1. **Keep OpenLigaDB** for the existing Bundesliga feed, including its license attribution and independent frozen research. No new rights are inferred for unrelated endpoints or competitions.
2. **football-data.org free plan** is the first expansion provider. Its official coverage lists eight domestic leagues including Brazil, alongside international competitions; pricing lists 12 competitions, delayed scores/schedules, fixtures and 10 requests/minute. Registration and a token are required. Verify available seasons and actual non-null HT results with the configured free token. The match schema's existence does not establish free historical depth. Do not enable paid add-ons.
3. **API-Football direct free plan** is the candidate worldwide provider: advertised 100 requests/day and all competitions/endpoints, with explicitly limited available seasons. An account/key is required. Inspect the authenticated account's entitlements and returned season errors before enabling any current league. An old allowed season does not imply current fixtures are accessible. Do not equate direct and RapidAPI plan terms. No automatic paid upgrade.
4. **TheSportsDB** remains an investigation candidate for additional fixture discovery. Do not use it as an HT training source without verified field definitions, actual coverage, permitted usage and data checks. Do not combine its fixtures with another source using fuzzy names alone.
5. **Football-Data.co.uk is excluded from automated ingestion/training** under its currently published restriction on automated bots/scrapers/AI and data-training products. Public CSV links do not override that restriction. Reconsider only with explicit provider permission applicable to this use.

Official references:

- https://www.football-data.org/coverage
- https://www.football-data.org/pricing
- https://docs.football-data.org/general/v4/policies.html
- https://docs.football-data.org/general/v4/match.html
- https://www.api-football.com/pricing
- https://www.api-football.com/terms
- https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide
- https://www.thesportsdb.com/api.php
- https://www.football-data.co.uk/data.php

## Two separate eligibility decisions

**Fixture coverage:** the source permits this access; the free account admits the current competition/season; the response has valid competition, team and event identities, a timezone-aware kickoff, a non-started status and an acceptable retrieval age. Otherwise show the unavailable provider/competition and reason, with no stale fixture advertised as current.

**Probability coverage:** sufficient clean HT history, distinct team identities, known first-half score semantics, a chronologically tested league model, calibration evidence, current-model provenance and no release-gate failure. A league may qualify for fixture coverage but fail this second decision. These games stay in All fixtures with Probability unavailable and a specific reason; they must not appear as ranked probability selections.

No unknown half-time result becomes 0–0. Full-time Over 0.5, team totals, virtual matches, youth fixtures and betting odds for full-time Over 2.5 are never substituted for the requested senior match first-half Over 0.5 target. Women's senior competitions require their own explicit competition eligibility and evidence rather than a silent exclusion or a shared men's model.

## Interface

- Retain the simple game-finder view. Add country/region and league filters, Today/Tomorrow/Next 7 days, and Top 20/Top 50/All eligible estimates.
- Offer All fixtures separately so worldwide fixture discovery remains usable even while prediction coverage is incomplete.
- A row shows fixture, country/league, Nigeria kickoff, estimated FH Over 0.5 probability if released, evidence status, source retrieval time and SportyBet status. Sample sizes and model version are available in a detail expander. Probabilities are rounded to whole percentages, not implausible precision.
- Display the available count before the selected limit. Empty results explain whether there are no fixtures, insufficient history, unvalidated models, exhausted quota, inaccessible season or an unavailable provider.
- Sort released estimates by probability, then kickoff and stable event identity for deterministic ties. Do not rank sample frequencies as calibrated predictions or assign a blanket percentage to unknown teams. Source quality is displayed separately from probability.
- Do not use “safe,” “sure,” “guaranteed” or “profit” labels. Estimated event likelihood does not establish value at the offered price.
- SportyBet availability/odds stay unverified unless separately checked by the existing legitimate manual workflow. No bookmaker integration is inferred from wider football coverage.

## Data boundary

Add provider adapters beside, rather than inside, the frozen Bundesliga research pipeline. Preserve all existing snapshots, score corrections, original code archives and backtest reports byte-for-byte. New live data never overwrites corrected historical labels.

Normalize events with provider, source_event_id, competition_id, season_id, source_team_ids, country, senior/real competition classification, kickoff_utc, source status, HT scores if explicit, FT scores if known, observed_at, source_url and payload digest. Composite provider IDs prevent collisions between unrelated numeric IDs. Cross-provider identity mappings require reviewed competition/team mappings; ambiguous matches stay separate and cannot produce duplicate ranked selections. If identity is uncertain, abstain rather than infer from display names.

Validate status and score types, duplicates, kickoff timezone, season, team identity and HT<=FT where applicable. Handle postponed, cancelled, abandoned and live games explicitly. Store rejected rows with reasons; do not quietly drop zero-goal halves. Keep private records and credentials separate from public research artifacts.

## Probability and evidence design

Reuse the existing count-model and calibration components where compatible, with separate league-specific fit/calibration records. The Bundesliga candidate's results do not validate another league, and its own operational gate remains closed.

Before fitting each new league, freeze its protocol: a five-season maximum history window, at least 500 eligible training games spanning two years, a distinct later calibration window with at least 500 observations and 100 examples of each class, and at least 10 prior eligible league games per team. These conservative starting requirements may leave leagues unavailable under free historical limits. Do not reduce them after viewing poor results merely to fill the list. Any later protocol revision is separately versioned and evaluated on a new untouched period.

Use the existing attack/defence Poisson candidate for home and away first-half counts; derive the event estimate as 1-exp(-(lambda_home+lambda_away)). Choose regularization and identity/positive-slope sigmoid calibration in earlier inner time folds using log loss, before a later outer evaluation. A failed calibration is reported and handled by the predeclared protocol, never by inventing an estimate. Do not assume unseen-team coefficients establish enough history for release.

Chronological feature/result availability is reconstructed with at least a 24-hour lag in historical tests; newly observed records must actually precede the forecast cutoff. Do not use today's completed result, final odds, revised future information or the target fixture's outcome in its features. Forecasts generated now are labeled generated-now; do not claim a T−60 forecast was issued in the past. Pending fixtures can receive their frozen operational forecast only at the declared supported timing.

Evaluate monthly walk-forward forecasts against each league's earlier goal-frequency baseline. Report sample size, log loss, Brier score, reliability bins, calibration slope/intercept, coverage/abstention and week/fortnight block intervals. Assess calibration and performance by league and by high-probability bins; pooled averages do not release an individual league. Inspect the top-20 selection rule on genuinely out-of-sample forecasts as well as the complete forecast set.

Operational probability release requires a declared validation report and prospective evidence under the project protocol, not merely a fit or an in-sample score. Initial collection is a shadow run; probabilities stay unavailable in the main ranked selection view while release evidence is pending. If the user later requests an experimental research-estimate view, design that explicitly with clear status and provenance; do not silently relabel it as validated prediction output.

Do not calculate SportyBet ROI without actual time-matched FH-market prices and settlement evidence. Do not multiply all game probabilities into an accumulator success estimate without a justified dependence model. No automated staking or wagering is introduced.

## Zero-cost deployment and quota controls

Use the current Streamlit deployment and existing Python dependencies where possible. Provider requests are read-only and limited to documented hosts, with TLS verification, timeouts, response-size/schema validation and bounded retries honoring Retry-After. Credentials go in Streamlit Secrets, never Git, browser code, CSV exports, logs or chat.

Cache requests across sessions and avoid per-team/per-fixture calls for all worldwide games. Share date/competition responses, fetch finished results less frequently, cache failures and show quota status. Respect football-data.org's 10/minute free limit. For API-Football reserve a small part of 100/day for entitlement/health checks and admit only leagues/date requests fitting the remaining budget; do not claim every worldwide league fits a free daily quota. Shared free keys may also be used outside this app, so honor provider quota headers/errors rather than assuming all quota remains.

Streamlit reruns, multiple workers or restarts must not reset a supposed durable provider budget. Use provider-reported remaining quota and a persistent shared budget store if needed; if only ephemeral storage is available, use conservative cooldowns and fail closed when the budget cannot be established. No new paid database, paid API, paid scheduler or paid hosting is authorized.

Keep manual personal record forms disabled by default on the shared app. The public page must never reveal secret values or stored private observations.

## Acceptance and go/no-go

1. Existing Bundesliga discovery, report downloads and frozen experiment hashes remain intact.
2. Authenticated free-plan checks record admitted current competitions, allowed seasons, HT completeness and license/attribution requirements. A configured-but-empty or paid-only feed is not counted as added coverage.
3. At least one current non-European domestic league is returned and shown before claiming a delivered worldwide expansion. Brazil is the first documented free-tier candidate. Additional continents are listed only as live supported once verified.
4. Top 20/50 limits, Nigeria date boundaries, started-game exclusion, identity collisions, duplicate sources, null HT scores, errors, rate limits, cache behavior and missing-secret startup receive meaningful regression tests.
5. A fixture-only league is usable without numerical probability claims. Forecast release tests enforce abstention for insufficient/unvalidated history. No global blanket model or fabricated percentage bypasses a failed league gate.
6. Verify the actual deployed Streamlit page with the configured free account; show counts, active sources and retrieval times. Only then describe leagues as added to the live app.

**Go now:** specification and source/entitlement preparation; keep current Bundesliga functioning.

**Conditional go after specification and implementation-plan review:** authenticated free-provider adapters and worldwide fixture discovery for actually admitted leagues.

**No-go until proven:** all countries/leagues on zero-cost current feeds; 20 qualifying estimates every day; current-season API-Football access based only on an advertised free plan; numerical probability release without data/model gates; verified SportyBet odds/booking integration; automated wagers.

## Required user setup before authenticated live verification

Create a free football-data.org account for the initial expanded feed. For candidate worldwide coverage, also create an API-Football direct free account, with no paid subscription. The user must complete account terms acceptance themselves. Store issued tokens through Streamlit app settings → Secrets, using FOOTBALL_DATA_TOKEN and API_FOOTBALL_KEY as the proposed names once the adapters exist. Do not paste tokens into chat or commit them. No key is required to read or approve this document, and missing keys must leave the current Bundesliga feed functional.

Next design gate: user reviews this written specification. After approval, prepare the concrete implementation plan and execution choice required by the installed design workflow. No product-code changes or worldwide deployment occurred while preparing this specification.
