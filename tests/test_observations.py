import copy
import unittest
from datetime import timedelta

import data
import observations
from tests.test_data import NOW


def fixture():
    return {'match_id': 7, 'home': 'Home', 'away': 'Away', 'snapshot_hash': 'one',
            'kickoff': (NOW+timedelta(hours=1)).isoformat(), 'finished': False,
            'kickoff_confirmed': False, 'observed_at': NOW.isoformat()}


def observation():
    return dict(match_id=7, home='Home', away='Away', country='NG', period='1H',
                statistic='goals', scope='match_total', line=0.5, side='over', odds=1.4,
                market_status='active', event_type='real_senior_football', event_id='example-test-event',
                observed_at=NOW.isoformat(), kickoff=fixture()['kickoff'], fixture_hash='one',
                rules_verified=False, human_identity_confirmed=True,
                evidence_note='Synthetic test observation only')


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.db = data.connect(':memory:')
        self.addCleanup(self.db.close)

    def test_wrong_market_country_live_virtual_and_nonfinite_odds_rejected(self):
        for key, value in [('country', 'GH'), ('period', 'FT'), ('line', 1.5), ('scope', 'home_team'),
                           ('statistic', 'corners'), ('side', 'under'), ('odds', float('nan')),
                           ('odds', float('inf')), ('odds', True), ('odds', 1),
                           ('event_type', 'virtual'), ('market_status', 'live')]:
            with self.subTest(key=key, value=value):
                wrong = dict(observation(), **{key: value})
                with self.assertRaises(ValueError): observations.record_observation(self.db, wrong, NOW)

    def test_human_entry_does_not_certify_rules_or_current_price(self):
        saved = observations.record_observation(self.db, observation(), NOW)
        self.assertEqual(saved['verifier_type'], 'human')
        self.assertEqual(observations.observation_state(saved, fixture(), NOW), 'rules_unverified')
        self.assertEqual(observations.observation_state(saved, fixture(), NOW+timedelta(minutes=5)), 'stale')
        changed = dict(fixture(), snapshot_hash='changed')
        self.assertEqual(observations.observation_state(saved, changed, NOW), 'mismatch')

    def test_future_observation_and_near_kickoff_are_not_fresh(self):
        with self.assertRaises(ValueError):
            observations.record_observation(self.db, dict(observation(), observed_at=(NOW+timedelta(seconds=1)).isoformat()), NOW)
        saved = observations.record_observation(self.db, observation(), NOW)
        near = dict(fixture(), kickoff=(NOW+timedelta(minutes=5)).isoformat())
        self.assertNotEqual(observations.observation_state(saved, near, NOW), 'human_observed')

    def test_booking_is_unverified_until_exact_explicit_human_reload(self):
        leg = {k: observation()[k] for k in ('match_id', 'country', 'period', 'statistic', 'scope', 'line', 'side')}
        booking = {'code': 'TEST12', 'country': 'NG', 'selection_manifest': [leg]}
        saved = observations.record_booking(self.db, booking, NOW)
        self.assertEqual(saved['code_state'], 'pasted_unverified')
        self.assertIsNone(saved['expiry_if_displayed'])
        loaded = dict(booking, human_reloaded=True, reloaded_at=NOW.isoformat(), reloaded_manifest=[leg])
        self.assertEqual(observations.record_booking(self.db, loaded, NOW)['code_state'], 'human_reload_matched')
        altered = dict(leg, line=1.5)
        self.assertEqual(observations.record_booking(self.db, dict(loaded, reloaded_manifest=[altered]), NOW)['code_state'], 'mismatch')
        with self.assertRaises(ValueError):
            observations.record_booking(self.db, dict(booking, code='<script>'), NOW)
