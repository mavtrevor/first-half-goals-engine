PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, season INTEGER NOT NULL,
  digest TEXT NOT NULL UNIQUE, observed_at TEXT NOT NULL, metadata TEXT NOT NULL,
  payload BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS matches (
  id INTEGER PRIMARY KEY, snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
  match_id INTEGER NOT NULL, season INTEGER NOT NULL, observed_at TEXT NOT NULL,
  record TEXT NOT NULL, UNIQUE(snapshot_id, match_id)
);
CREATE INDEX IF NOT EXISTS match_versions ON matches(match_id, observed_at, id);
CREATE TABLE IF NOT EXISTS forecasts (
  id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, generated_at TEXT NOT NULL,
  record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, entered_at TEXT NOT NULL,
  record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY, entered_at TEXT NOT NULL, record TEXT NOT NULL
);
