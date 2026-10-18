# Worldwide expansion acceptance — 18 October 2026

Implemented: separate worldwide snapshot/budget store; documented football-data.org/API-Football direct clients; common event identities; fresh prematch filters; source/setup diagnostics; daily Top20/50 ranking boundary; scoped historical importer; frozen chronological count-model evaluation; immutable private T−60 shadow observations and revised result settlements; CLI entry points. Existing Bundesliga model/results and raw snapshots are preserved.

Local configured key presence only was checked: neither FOOTBALL_DATA_TOKEN nor API_FOOTBALL_KEY is present in the designated environment/project secrets. The missing-key CLI and UI do not send authenticated requests. Actual additional competitions, current-season access, HT completeness, quotas and non-European live delivery are pending authenticated checks. The advertised source catalog is not delivery evidence.

The extra sources are adapters ready for configuration, not a claim that every worldwide league is live. Brazil is a first free-tier candidate. API-Football competitions also need reviewed senior competition identities. No global free-data completeness or guaranteed twenty games per day is claimed. First-half percentages remain unavailable pending league-specific model/prospective validation; the initial wider models are shadow research.

The complete project suite passes81tests. Tests cover storage versions/IDs, digest mismatch, request accounting across connections, provider schema/status/HT semantics, sanitized HTTP errors, unknown quotas, missing-key no-request behavior, partial responses, Nigeria dates, selection limits, UI behavior, immutable research inputs/selection seals and forecast timing/settlement revisions. Final fixes include requested historical season metadata, invalid revisions superseding old usable records, concurrent cached imports and selection time after retrieval. Frozen challenger report SHA256 remains4952f38dfb2d8fe83cb5a818198d8e9e02884e1f1ee567baece8c68186cee62d.

One independent review began and identified the historical API-Football season-completion defect. That finding was reproduced in a failing test and fixed. The reviewer then hit a usage limit before completing the remaining audit. Root completed targeted checks and regression tests; this is not represented as a completed independent review. No repeat independent review is claimed.

## Run locally

Commands use the project environment and print sanitized statuses, never tokens:

```powershell
.venv/Scripts/python.exe worldwide_research.py catalog --provider football_data
.venv/Scripts/python.exe worldwide_research.py import-history --provider football_data --competition 2013 --seasons 2021 2022 2023 2024 2025
.venv/Scripts/python.exe worldwide_research.py evaluate --provider football_data --competition 2013 --run brazil-v1
.venv/Scripts/python.exe worldwide_research.py shadow --provider football_data --competition 2013 --run brazil-v1
```

The import is conditional on actual free historical access. An unavailable season remains unavailable. Evaluation creates a new run directory and refuses overwrite. Shadow collection requires an earlier sealed league selection, enough observed training/calibration data, reviewed real senior fixtures and actual invocation in the55–65minutes-before-kickoff window. It does not run unattended. No scheduling or model release is claimed by these commands.

## Streamlit configuration

From share.streamlit.io, select the app's overflow menu → Settings → Secrets. Insert the issued free keys using FOOTBALL_DATA_TOKEN and optionally API_FOOTBALL_KEY, then Save. These are root TOML entries, not a [secrets] table. Do not expose values in chat, screenshots or Git. Source diagnostics in the deployed app show whether each configured source actually returned valid fixtures. See https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings .

Go: reviewed adapters, tests and honest source/setup UI. Conditional: authenticated worldwide fixture acceptance after free credentials and competition review. No-go: public numerical probabilities until prospective evidence; SportyBet odds/readiness, booking-code generation and wagering remain unverified/excluded.
