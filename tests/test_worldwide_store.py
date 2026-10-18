import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timedelta, timezone
from pathlib import Path

from worldwide_store import connect_worldwide, observations, reserve_request, save_feed

NOW = datetime(2026, 10, 18, 8, tzinfo=timezone.utc)


class StoreTests(unittest.TestCase):
    def test_simultaneous_cached_feed_import_is_idempotent(self):
        raw=b'one response';barrier=Barrier(8)
        feed=dict(provider='fd',events=[],rejections=[],observed_at=NOW.isoformat(),
                  snapshot_hash=hashlib.sha256(raw).hexdigest())
        def save(_):
            db=connect_worldwide(self.path)
            try:
                barrier.wait(timeout=10)
                return save_feed(db,feed,raw)
            finally:db.close()
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(len(set(executor.map(save,range(8)))),1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feeds').fetchone()[0],1)

    def test_rejected_revision_supersedes_old_usable_record(self):
        def feed(raw, minute, events, rejections):
            return dict(provider='fd',snapshot_hash=hashlib.sha256(raw).hexdigest(),events=events,
                rejections=rejections,observed_at=(NOW+timedelta(minutes=minute)).isoformat())
        old=dict(event_id='fd:1',competition_id='fd:9',observed_at=NOW.isoformat(),target=1,quality='structurally_valid')
        save_feed(self.db,feed(b'old',0,[old],[]),b'old')
        save_feed(self.db,feed(b'new',1,[],[dict(event_id='fd:1',reason='invalid_event')]),b'new')
        latest=observations(self.db,'fd:9',NOW+timedelta(minutes=1))[0]
        self.assertIsNone(latest['target'])
        self.assertEqual(latest['quality'],'quarantined')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'worldwide.sqlite'
        self.db = connect_worldwide(self.path)
        self.addCleanup(self.db.close)

    def test_append_only_versions_and_provider_ids(self):
        def save(provider, minute):
            raw = json.dumps([provider, minute]).encode()
            row = dict(event_id=f'{provider}:123', competition_id=f'{provider}:1',
                       observed_at=(NOW+timedelta(minutes=minute)).isoformat())
            feed = dict(provider=provider, observed_at=row['observed_at'], events=[row], rejections=[],
                        snapshot_hash=hashlib.sha256(raw).hexdigest())
            return save_feed(self.db, feed, raw)
        a = save('one',0)
        self.assertEqual(save('one',0), a)
        save('one',1); save('two',0)
        self.assertEqual(len(observations(self.db,'one:1',NOW)),1)
        self.assertEqual(observations(self.db,'one:1',NOW)[0]['observed_at'],NOW.isoformat())
        self.assertEqual(len(observations(self.db,'two:1',NOW)),1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feeds').fetchone()[0],3)

    def test_atomic_last_allowance_and_reopen_does_not_reset(self):
        other = connect_worldwide(self.path)
        self.addCleanup(other.close)
        allowance = dict(remaining=1, reset_at=(NOW+timedelta(minutes=1)).isoformat(),
                         observed_at=NOW.isoformat(), minute_limit=10, reserve=0)
        self.assertTrue(reserve_request(self.db,'fd',NOW,allowance))
        self.assertFalse(reserve_request(other,'fd',NOW,allowance))
        self.assertFalse(reserve_request(self.db,'new',NOW,{}))
        self.assertFalse(reserve_request(self.db,'fd',NOW+timedelta(minutes=2),allowance))

    def test_digest_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            save_feed(self.db,dict(provider='a',snapshot_hash='bad',events=[],rejections=[],observed_at=NOW.isoformat()),b'[]')


if __name__ == '__main__': unittest.main()
