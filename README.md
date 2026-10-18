# First-Half Goals Lab

The worldwide finder adds country/region/league filters, Today/Tomorrow/Next7days and Top20/Top50/All eligible estimates. [Worldwide source setup](docs/worldwide-coverage.md) explains the free provider keys and current access checks. Missing keys keep Bundesliga working; additional countries are not claimed live until authenticated verification. Initial wider probability models remain shadow research.

A Bundesliga fixture finder and research workbench. The Streamlit app retrieves current fixtures from OpenLigaDB's free documented API, displays Nigeria kickoff times and descriptive first-half goal counts, and includes the saved score audit and model evaluations.

**The model has not earned release.** Its frozen 2025–26 test was slightly worse than the earlier league goal-frequency baseline. Validated probabilities and SportyBet readiness remain locked. Nothing in this app creates a booking code, accesses a betting account or places a wager.

On Streamlit Cloud, use **Load current fixtures → When (Nigeria time)**. No API key, database import or secret is needed. The source is cached for five minutes. Coverage is Bundesliga only. See [live fixture repair and decisions](docs/live-fixture-fix.md). Personal record forms are disabled by default; enable `FH_ENGINE_ENABLE_MANUAL_RECORDS=1` only on a private local installation.

## Open the app

While the development server is running, open **http://127.0.0.1:8501**.

To start it later, open PowerShell in this folder and run:

```powershell
.\launch.ps1
```

On a fresh clone, create the Python environment as described below, then copy the supplied public research evidence to the private runtime folder and import it:

```powershell
Copy-Item -LiteralPath evidence -Destination data -Recurse
.\.venv\Scripts\python.exe research.py import
```

Copy only when `data/` does not exist. This import is optional for historical database exploration; current fixtures and bundled backtest reports work without it. The tracked `evidence/` folder contains public source snapshots and fixed experiments. `data/` stays excluded from Git because it also stores personal observations. The historical import itself uses no network.

If Windows blocks local script execution, do not weaken your execution policy. Run these commands instead:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Python 3.14.0 is the tested runtime. A new installation can create a local environment with `python -m venv .venv`, then install the free pinned packages with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. There are no subscriptions, accounts, API keys or paid services. Existing computer, power and internet costs are outside that claim. The application runs only while its local process is running.

## What is included

- Nine original OpenLigaDB season snapshots, 2018–19 through the in-progress 2026–27 season: 2,754 recorded fixtures, of which 2,494 were marked finished with structurally valid HT scores at retrieval.
- Twenty authority-supported score corrections, including fifteen binary target changes. Original bytes remain preserved. SQLite stores the effective corrected versions and correction provenance.
- The complete 2,448-match cross-source comparison and a fixed 100-match audit sample. All 100 sample half-time scores now have separate official-publication corroboration from an assisted desk review; this does not prove independent upstream collection. See [audit findings](docs/score-audit-findings.md) and the per-match evidence ledger in `evidence/independent-score-audit.json`.
- A frozen monthly development/holdout experiment, raw historical research predictions, baseline comparison and week/fortnight-block uncertainty.
- Forms for recording human observations and references to codes already created in SportyBet's official Nigeria interface. The app never invents or validates a code against SportyBet's servers.

The reference archive lacks explicit HT fields for 126 matches, including 125 recorded as 0–0 at full time. These matches were retained with their missing-corroboration status; dropping them would distort the sample.

## Read the evidence

`data/reports/v1/backtest.json` is the primary frozen experiment. Its selection seal records the model configuration chosen using 2024–25 development results before the 2025–26 sequential holdout was evaluated. `data/reports/v1/source-code/` preserves the code that generated this run; `run-manifest.json` records code, source and report hashes. Later fixes must not silently replace this evidence.

`docs/model-card.md` explains the result and limits. `docs/feasibility-acceptance.md` lists remaining operational gates. The optional 48-hour-lag run, if present, is a sensitivity check and does not replace the main test or choose a new production model.

The separate [Poisson challenger](docs/challenger-v2-results.md) uses nested chronological development folds and has modest descriptive improvements on the already inspected archive. Its baseline uncertainty still spans zero. See Backtest → Poisson challenger — exploratory; this does not unlock current-match probabilities. Its frozen report and pre-fit code/effective-input archive are under `evidence/reports/poisson-v2-exploratory/` (copied to `data/reports/` during fresh-clone setup).

The UI shows live retrieval and saved snapshot times in WAT. Community fixture times may change and are not SportyBet confirmations. A saved human quote expires after five minutes at most, or sooner when identity/kickoff/status changes. Human code reload matching is a historical record, not proof of current prices or an accepted wager.

## Commands

```powershell
# Validate the supplied offline archive and initialize/reuse the local database.
.\.venv\Scripts\python.exe research.py import
.\.venv\Scripts\python.exe research.py audit

# Run all tests.
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Run the sealed experiments only if their report directories do not exist.
.\.venv\Scripts\python.exe research.py backtest
.\.venv\Scripts\python.exe research.py backtest --run lag48-sensitivity

# Run the separately declared exploratory challenger only if its run directory does not exist.
.\.venv\Scripts\python.exe challenger.py
```

Existing experiment reports are protected against overwrite. To rerun research, preserve the original run and explicitly create a newly named protocol/version in the code; do not delete or retune a failed holdout. Importing the same bytes is idempotent. Changed upstream data needs a new snapshot and renewed correction review.

## Scope and data rights

### Review corrections and frozen evidence

The original `lag48-sensitivity` experiment used a 48-hour feature-history lag but a 24-hour training/calibration label lag. It is **feature-lag-only evidence**, not a full 48-hour availability test; its original JSON is preserved. Future runs apply the configured lag to both. Neither frozen result has been rerun or retuned.

The original v1 manifest/source archive was assembled after execution and omits effective-label hashes. The legacy sensitivity run has no contemporaneous code archive. These limitations cannot be repaired retroactively. New runs archive generating code, protocol, raw snapshot identities and effective normalized inputs before fitting. Changed corrections on repeated identical bytes now fail explicitly rather than silently retaining old labels. Unsupported protocol changes fail before fitting.

Contains information from [OpenLigaDB](https://www.openligadb.de/), made available under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The raw/effective database and supplied alteration ledger retain that data license; local code does not grant different rights over the source data. Reference comparison data comes from [openfootball](https://github.com/openfootball/football.json), which declares CC0. No crests, videos, private account details or scraped odds are included. Review license obligations before public redistribution; this delivery is for personal local use.

A narrow read-only fixture adapter is enabled based on the source's explicit automatic-retrieval offering and official endpoint documentation, reviewed 2026-10-18. The unreadable general terms page is not claimed as reviewed. Current Nigeria rules/workflow remain unverified. There is no switch that turns this research build into an automated betting system.

Keep the `data/` folder private; it stores any notes and code references you enter. Do not enter passwords, phone numbers, OTPs or payment details. No LLM produces probabilities. No profitable-edge claim, stake optimizer or accumulator win-probability estimate is provided. Adult personal research only.
