"""Private append-only worldwide observations and atomic provider budgets."""
import hashlib
import json
import sqlite3
from datetime import timedelta

from data import utc


def connect_worldwide(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS feeds (
        id INTEGER PRIMARY KEY, provider TEXT, digest TEXT, observed_at TEXT,
        record TEXT, payload BLOB, UNIQUE(provider,digest,observed_at));
      CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY, feed_id INTEGER REFERENCES feeds(id),
        event_id TEXT, competition_id TEXT, observed_at TEXT, record TEXT);
      CREATE INDEX IF NOT EXISTS event_versions ON events(event_id,observed_at,id);
      CREATE TABLE IF NOT EXISTS budgets (
        provider TEXT PRIMARY KEY, record TEXT);
      CREATE TABLE IF NOT EXISTS requests (provider TEXT, observed_at TEXT);
      CREATE TABLE IF NOT EXISTS shadows (
        event_id TEXT, kickoff TEXT, generated_at TEXT, record TEXT,
        PRIMARY KEY(event_id,kickoff));
      CREATE TABLE IF NOT EXISTS settlements (
        event_id TEXT, kickoff TEXT, observed_at TEXT, digest TEXT, record TEXT,
        UNIQUE(event_id,kickoff,digest));
    ''')
    return db


def save_feed(db, feed, raw):
    digest = hashlib.sha256(raw).hexdigest()
    if feed['snapshot_hash'] != digest:
        raise ValueError('Snapshot digest mismatch')
    observed = utc(feed['observed_at']).isoformat()
    record = json.dumps(feed, allow_nan=False, sort_keys=True)
    with db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT id,record FROM feeds WHERE provider=? AND digest=? AND observed_at=?',
                         (feed['provider'],digest,observed)).fetchone()
        if old:
            if old['record'] != record:
                raise ValueError('Changed normalization requires a new version')
            return digest
        sid = db.execute('INSERT INTO feeds(provider,digest,observed_at,record,payload) VALUES(?,?,?,?,?)',
                         (feed['provider'],digest,observed,record,raw)).lastrowid
        for row in feed['events']:
            if not row['event_id'].startswith(feed['provider']+':') or utc(row['observed_at']).isoformat() != observed:
                raise ValueError('Observation identity/time mismatch')
            db.execute('INSERT INTO events(feed_id,event_id,competition_id,observed_at,record) VALUES(?,?,?,?,?)',
                        (sid,row['event_id'],row['competition_id'],observed,json.dumps(row,allow_nan=False)))
        for rejected in feed.get('rejections',[]):
            event_id=rejected.get('event_id')
            if not isinstance(event_id,str) or not event_id.startswith(feed['provider']+':'):continue
            old=db.execute('SELECT record FROM events WHERE event_id=? ORDER BY observed_at DESC,id DESC LIMIT 1',
                           (event_id,)).fetchone()
            if old:
                row=dict(json.loads(old[0]),quality='quarantined',target=None,status='INVALID',
                         observed_at=observed,snapshot_hash=digest,reason='rejected_source_revision')
                db.execute('INSERT INTO events(feed_id,event_id,competition_id,observed_at,record) VALUES(?,?,?,?,?)',
                            (sid,event_id,row['competition_id'],observed,json.dumps(row,allow_nan=False)))
    return digest


def observations(db, competition_id, as_of):
    rows = db.execute('''SELECT record FROM (SELECT record,ROW_NUMBER() OVER(
      PARTITION BY event_id ORDER BY observed_at DESC,id DESC) AS rank
      FROM events WHERE competition_id=? AND observed_at<=?) WHERE rank=1''',
      (competition_id,utc(as_of).isoformat())).fetchall()
    return [json.loads(row[0]) for row in rows]


def reserve_request(db, provider, now, allowance):
    now = utc(now)
    db.execute('BEGIN IMMEDIATE')
    try:
        old = db.execute('SELECT record FROM budgets WHERE provider=?',(provider,)).fetchone()
        state = json.loads(old[0]) if old else {}
        incoming = dict(allowance)
        for value in (state, incoming):
            if value and (type(value.get('remaining')) is not int or value['remaining'] < 0
                          or utc(value['observed_at']) > now or utc(value['reset_at']) <= now):
                value.clear()
        # A reused/stale server observation cannot replenish a locally spent allowance.
        if incoming and (not state or utc(incoming['observed_at']) > utc(state['observed_at'])):
            state = incoming
        if not state or utc(state['reset_at']) <= now:
            return False
        count = db.execute('SELECT COUNT(*) FROM requests WHERE provider=? AND observed_at>?',
                           (provider,(now-timedelta(minutes=1)).isoformat())).fetchone()[0]
        if state['remaining'] <= state.get('reserve',0) or count >= state['minute_limit']:
            return False
        state['remaining'] -= 1
        db.execute('INSERT OR REPLACE INTO budgets VALUES(?,?)',(provider,json.dumps(state)))
        db.execute('INSERT INTO requests VALUES(?,?)',(provider,now.isoformat()))
        return True
    finally:
        db.commit()
