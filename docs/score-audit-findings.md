# Fixed 100-match score audit

Reviewed 17 October 2026. **All 100 selected half-time scores were corroborated against separate official club or Bundesliga publications. No new half-time disagreements were found and no score corrections were added.** This is a completed assisted desk review, not a second human's sign-off or a certification of independent upstream data collection.

| Check | Result |
|---|---:|
| Original selected matches retained | 100 / 100 |
| Unique identities reviewed | 100 |
| Officially corroborated HT scores | 100 |
| New HT disagreements | 0 |
| Unresolved HT scores in this sample | 0 |
| Previously missing reference HT fields now corroborated | 17 / 17 |
| Explicit HT score or interval narrative | 49 |
| HT derived from valid-goal timeline | 40 |
| HT derived from a completed, played 0-0 result | 11 |

The evidence ledger contains the actual reviewed score, source URL, evidence kind, review basis, review date and retrieval mode for every selected match. The CSV joins that evidence to the unchanged original sample. `score-audit-summary.json` records counts and SHA-256 identities of the original sample, ledger and CSV.

## Method and interpretation

The sample remains the original deterministic, season-stratified 50 zero-goal / 50 nonzero-goal sample across 2018–19 to 2025–26. No inconvenient row was replaced. Identity was checked using home-away ordering, competition season and matchday or a dated club report. Scores are stored in home-away order even when an away-club report describes its own winning score first. This checks HT results, not a fresh historical kickoff-time or postponement audit.

An explicit interval score was preferred. Where only a valid-goal timeline was available, the reviewed period boundary and complete scoring sequence determined the HT score. A first-half stoppage-time goal belongs to the first half; a goal at minute 47 after restart belongs to the second. Own goals count. Dismissals, missed penalties and disallowed goals do not count. For 11 completed matches independently shown as played 0-0, HT 0-0 is a stated logical derivation, not an invented missing source field. No awarded-score indication was observed in those match centres.

Examples of the evidence:

- Bayern–Bremen, 20 April 2019: the [official Bayern report](https://fcbayern.com/en/news/matchreports/2019/04/match-report-bundesliga-md30-fc-bayern---werder-bremen-200419) explicitly records HT 0-0.
- Union–Köln, 13 March 2021: the [official Union report](https://www.fc-union-berlin.de/de/matchcenter-yIur80uWs2dLddOullKS90WIC) places Duda's goal in first-half stoppage time and Kruse's equaliser after restart, supporting HT 0-1. The club's prose says 45+1 and the league timeline says 45+2; that minute discrepancy does not change the period or HT score.
- Hoffenheim–Dortmund, 26 April 2025: the [official league timeline](https://www.bundesliga.com/en/bundesliga/matchday/2024-2025/31/tsg-hoffenheim-vs-borussia-dortmund/liveticker) records HT 0-1, a saved penalty and a disallowed Hoffenheim goal. Those events were distinguished from valid goals.
- Union–Freiburg, 18 May 2024: the [official Freiburg report](https://www.scfreiburg.com/aktuell/nachrichten/profis/2023/24/niederlage-in-koepenick-sc-landet-auf-rang-10/) explicitly gives HT 0-0; it supplied the evidence when the English league page lookup failed.

87 retained authority checks used retrieved official-page text; 13 used official report text exposed through the search index. These 13 retain the weaker retrieval classification. Search snippets may be stale or truncated; they are not represented as separately archived full reports. One old Fortuna archive redirected to a general news page, so its match-centre evidence was replaced with the readable league timeline. Full copyrighted articles were not copied into the repository, and no unsupported scrape or training-data feed was created.

## What passed and what remains blocked

**PASS, limited scope:** fixed-sample official-publication corroboration. The existing policy key `independent_score_audit_passed` now refers only to this documented scope; the app labels it accordingly. It does not certify a fully independent original data-collection chain, a blind review, a human review, or all 2,448 historical rows. The reviewer could see the source scores, so this is an unblinded comparison.

The earlier 83 dataset agreements plus 17 missing fields are preserved as historical source-comparison states. The 17 missing fields were not filled into the reference archive; separate authority evidence now corroborates them. Likewise, the previously identified 20 population-level disagreements and their correction ledger remain unchanged. None of those 20 was in this fixed sample, so the new zero-disagreement finding does not contradict the known wider source errors.

The sample's deliberate 50/50 outcome allocation and within-season selection do not justify a pooled population error-rate estimate or prove a predictive edge. Shared upstream feeds cannot be ruled out just because publications have different domains. The ledger is available for a separate human review.

**NO-GO for operational predictions remains:** the frozen v1 model did not outperform the league baseline, lacks sufficient final-period evidence for its release rule, and has no prospective validation or legitimate historical SportyBet price record. Current fixture checks, effective live-access conditions and Nigeria settlement/workflow verification remain pending. The retrospective report, source snapshots, old correction ledger and model parameters were not rewritten, retuned or rerun.
