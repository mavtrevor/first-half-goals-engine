# Phase 0 findings and current build decision

Date: 17 October 2026, Africa/Lagos. Scope: read-only investigation and planning following approval to proceed. No application, model, training run, backtest, SportyBet automation or wager was created.

## Decision

**HOLD application implementation until the remaining feasibility gates pass.** The initial structural data checks were insufficient to establish label correctness. The new audit found specific errors and a missingness bias that the implementation must address.

## Work completed

Compared all 2,448 previously downloaded OpenLigaDB Bundesliga matches from 2018–19 through 2025–26 with the corresponding openfootball JSON season files. Matching used explicit reviewed team-name aliases and home/away identities within each season, never fuzzy name matching. All identities matched uniquely; dates agreed for every pair.

| Comparison outcome | Matches |
|---|---:|
| Both HT and FT scores agree | 2,302 |
| Half-time score disagrees | 20 |
| Reference lacks an explicit half-time score | 126 |
| Total | 2,448 |

The two archives agree on 2,302 of the 2,322 pairs with comparable HT results. This is agreement between separately published datasets, not proof of independent original collection or perfect accuracy. No inference that the other 126 rows are correct is warranted.

All 20 disagreements were reviewed against official league or club reports/timelines. Those reports support the openfootball half-time score in each disputed case. **Fifteen corrections change whether the first half had a goal.** The remaining five change the score counts, which would also affect scoring/conceding features.

Examples:

- Bayern–Darmstadt, 28 October 2023: OpenLigaDB recorded HT 1–0; the official club report confirms HT 0–0 and eight goals after the restart. [Official report](https://fcbayern.com/en/news/matchreports/2023/10/match-report-bundesliga-md9-fc-bayern-v-sv-darmstadt-281023).
- Leverkusen–Freiburg, 21 December 2024: OpenLigaDB recorded HT 0–0; Schick's first-half stoppage-time goal made it 1–0 at the interval. [Official league report](https://www.bundesliga.com/en/bundesliga/news/bayer-leverkusen-sport-club-freiburg-match-report-highlights-matchday-15-schick-wirtz-30199).
- Mainz–Köln, 24 August 2025: OpenLigaDB recorded HT 0–1; the league report lists the game's only goal in second-half stoppage time, supporting HT 0–0. [Official league report](https://www.bundesliga.com/en/bundesliga/news/mainz-cologne-match-report-highlights-matchday-1-33674).

The correction ledger contains every disputed match, original/corrected scores, authority URL, review basis and original snapshot hash. It is **proposed correction data**, not a mutation of the source or an implemented override pipeline. The official evidence was reviewed through search-indexed report text; no league website was crawled as a bulk training feed. Original snapshots remain unchanged. Any future correction loader must verify the source snapshot and original score before applying an override; changed upstream records require review.

## Missingness is not random

Of the reference archive's 126 absent HT fields, **125 are matches recorded as 0–0 at full time in OpenLigaDB**. Filtering training rows to only those with explicit HT fields in both datasets would therefore disproportionately discard goalless halves. Keep these records visible as missing corroboration. Do not label them as disagreements, silently invent a reference HT value or selectively drop them without reporting the bias.

A reproducible 100-match desk-audit sample was generated across all eight seasons, balanced between 50 source-recorded zero-goal halves and 50 source-recorded nonzero halves. Selection uses a fixed SHA-256 ordering of `phase0-sample-2026-10-17:<match_id>` within season/target strata. Seasons 2018–21 contribute 13 each (six zero, seven nonzero); 2022–23 contribute 12 each (seven zero, five nonzero); 2024–25 contribute 12 each (six zero, six nonzero). It does not filter by agreement or change the sample to replace inconvenient rows.

The sample contains 83 agreeing source pairs and 17 with absent reference HT fields. None of the 20 full-population discrepancies happens to be in this sample. This illustrates why a small sample alone was insufficient. **The originally proposed independent manual 100-match audit is not declared passed:** dataset comparison is supplementary evidence, and 17 sample rows still lack explicit reference HT corroboration. Official-report review of all 20 discrepancies is additional work, not a replacement claim for that gate.

## Gate status

| Gate | Result | Required next evidence |
|---|---|---|
| Bundesliga scope accepted | PASS | User's instruction to proceed |
| Documented API and data license identified | PASS for identification | OpenLigaDB homepage states public API and ODbL; preserve attribution |
| Effective API access conditions reviewed | PENDING | Linked terms/license pages still returned navigation/cookie content with no substantive terms; a readable current text is needed |
| Basic historical schema/score checks | PASS only for earlier stated checks | Does not establish independent correctness |
| Cross-source historical review | DISCREPANCIES IDENTIFIED AND EVIDENCED | Apply reviewed corrections only after build approval; preserve all raw data and quality states |
| Independent 100-match manual audit | PENDING | Complete independent corroboration without substituting the selected sample |
| Current fixture kickoff/status accuracy | PENDING | Check a recorded sample against an authoritative current schedule; do not treat cached future times as confirmed |
| Nigeria exact market and settlement rules | PENDING | Read current official Nigeria provisions, including interruption/resumption and stoppage time |
| Manual Book bet / reload behavior | PENDING | A human must confirm the Nigeria UI workflow without placing a wager; capture expiry/login behavior if shown |
| Automatic SportyBet integration | NO-GO | No supported free third-party integration established |
| Implementation plan | READY FOR REVIEW | Plan review required before implementation; unresolved feasibility gates remain separate |

OpenLigaDB's privacy policy additionally describes automated API clients and requests an informative application User-Agent with contact information. This supports designing an identified client, but does not substitute for the unreadable access conditions. Do not fabricate a contact address. [Official privacy policy](https://www.openligadb.de/Privacy), [homepage](https://www.openligadb.de/), [linked access terms](https://www.openligadb.de/nutzungsbedingungen).

SportyBet Nigeria's public help pages again yielded JavaScript shells in direct retrieval. Other countries' rules were not substituted. No authenticated pages, private endpoints, browser automation or code-creation action was used. [Nigeria sports help](https://www.sportybet.com/ng/help?nav=sports).

## Deliverables

- `cross-source-score-comparison.csv`: all 2,448 comparisons, including missing-reference records and disagreement flags.
- `verified-score-corrections.json`: 20 authority-supported corrections; 15 target changes; none applied.
- `100-match-audit-sample.csv`: fixed 100-match sample and current corroboration status.
- `first-half-goals-implementation-plan.md`: proposed files, interfaces, tests and release gates.

The runtime inspection found Python 3.14, NumPy and scikit-learn already installed; Streamlit and pytest were absent. No packages were installed. The proposed build uses standard-library unittest rather than adding pytest, and a project-local environment for any required UI dependency. Compatible versions still require verification during the approved build.

Headroom's MCP compression was attempted, but its configured local proxy remained unreachable and saved no tokens. Focused source reads were used instead. No API credentials, payments or messages to providers were involved.

**Next step:** review the implementation plan and close the pending data-access, independent score, fixture and Nigeria workflow gates. A plan approval does not itself establish provider rights or validate model probabilities.
