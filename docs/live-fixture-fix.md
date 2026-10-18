# Streamlit live fixture repair — 2026-10-18

The deployed app was deliberately offline and a fresh checkout contained no ignored local SQLite database. This produced an empty fixture screen. The repair loads the documented public OpenLigaDB `getmatchdata/bl1/{season}` endpoint without a key, separately from the frozen research database. No historical corrections or evaluation artifacts are overwritten.

OpenLigaDB's official homepage explicitly offers free, unauthenticated automatic retrieval for applications and websites, and labels the data ODbL 1.0. Its official sample repository documents this exact season endpoint. This supports a narrow go decision for read-only fixture retrieval; the previously unreadable general terms page is not claimed to have been reviewed. Source: https://www.openligadb.de/ and https://github.com/OpenLigaDB/OpenLigaDB-Samples . Attribution and license links remain in the app.

The app caches both success and failure for five minutes across sessions. Requests identify the project, have a 15-second timeout and a two-megabyte limit, and validate league, season, unique identities, timezone, names and score semantics. Failures show an error and no current games; old saved fixtures are never presented as current. Fetch time is displayed, not misrepresented as the provider's last update time. Started and finished matches are excluded. Today/tomorrow use Nigeria's calendar day. Coverage remains Bundesliga only.

The fixture table includes each team's latest ten completed games in the current feed season, showing the count with a first-half goal and the number with usable HT scores. This is descriptive community data, not a probability, calibrated forecast, verified selection or guarantee. Empty denominators stay unknown. No historical correction is silently applied to a revised live source response.

Tracked research reports are used when a fresh Cloud deployment lacks the local reports directory. Manual personal-record forms and histories are disabled by default on shared deployments; only a private local installation should enable `FH_ENGINE_ENABLE_MANUAL_RECORDS=1`. This is not an authentication system. Streamlit local files are not durable personal storage.

Go: live fixture discovery, Nigeria times, descriptive first-half counts, CSV export. No-go: validated current-match probabilities, verified SportyBet markets/odds, automatic booking codes, wagering. The existing prospective validation and SportyBet evidence gates remain pending. Enabling a data feed does not pass those gates.
