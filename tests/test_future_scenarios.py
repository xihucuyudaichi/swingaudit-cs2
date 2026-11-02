import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from future_scenarios import simulate_future, upcoming_catalog
import research

TODAY = date(2026, 11, 1)


class FutureScenariosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = research.load_data()

    def body(self):
        return {'mode': 'future_events', 'year': '2026', 'events': [{
            'event_id': 'iem-beijing-2026', 'mvp_player': 'donk', 'players': [
                {'player_id': 'donk', 'rating': 1.5, 'maps': 12, 'team': 'Spirit', 'team_place': '亚军'},
                {'player_id': 'zywoo', 'rating': 1.3, 'maps': 10, 'team': 'Vitality', 'team_place': '冠军', 'evp': True}
            ]}]}

    def run_case(self, body):
        return simulate_future(self.data, body, TODAY)

    def test_append_math_no_mutation_mvp_not_champion_and_unchanged_others(self):
        snapshot = json.dumps(self.data, sort_keys=True)
        r = self.run_case(self.body())
        donk = next(p for p in self.data['seasons']['2026']['players'] if p['id'] == 'donk')
        row = next(p for p in r['rows'] if p['id'] == 'donk')
        expected = (sum(p['rating'] * p['maps'] for p in donk['events']) + 1.5 * 12) / (sum(p['maps'] for p in donk['events']) + 12)
        self.assertEqual(row['after_rating'], round(expected, 4))
        self.assertEqual(row['after_mvp'], row['before_mvp'] + 1)
        self.assertEqual(row['after_maps'], row['before_maps'] + 12)
        self.assertEqual(r['assumption_manifest'][0]['players'][0]['team_place'], '亚军')
        for p in r['rows']:
            if p['id'] not in ('donk', 'zywoo'):
                self.assertEqual(p['before'], p['after'])
                self.assertEqual(p['before_mvp'], p['after_mvp'])
        self.assertEqual(json.dumps(self.data, sort_keys=True), snapshot)

    def test_multiple_events_accumulate_and_repeat_is_deterministic(self):
        b = self.body()
        b['events'].append({**copy.deepcopy(b['events'][0]), 'event_id': 'pgl-major-singapore-2026'})
        r = self.run_case(b)
        p = next(p for p in r['rows'] if p['id'] == 'donk')
        self.assertEqual(p['after_mvp'], p['before_mvp'] + 2)
        self.assertEqual(p['after_maps'], p['before_maps'] + 24)
        self.assertEqual(r, self.run_case(b))

    def test_no_mvp_and_zero_rating_not_silently_defaulted(self):
        b = self.body(); b['events'][0]['mvp_player'] = ''
        b['events'][0]['players'][0]['rating'] = 0
        r = self.run_case(b)
        self.assertEqual(r['assumption_manifest'][0]['players'][0]['rating'], 0)
        self.assertTrue(all(p['before_mvp'] == p['after_mvp'] for p in r['rows']))

    def test_invalid_performance_and_duplicates_rejected(self):
        for field, values in [('rating', [-1, 4, True, '1.5', float('nan'), float('inf'), None]), ('maps', [0, -1, 51, 1.5, True, None])]:
            for val in values:
                with self.subTest(field=field, val=val):
                    b = self.body(); b['events'][0]['players'][0][field] = val
                    with self.assertRaises(ValueError): self.run_case(b)
        b = self.body(); b['events'].append(copy.deepcopy(b['events'][0]))
        with self.assertRaises(ValueError): self.run_case(b)
        b = self.body(); b['events'][0]['players'].append(copy.deepcopy(b['events'][0]['players'][0]))
        with self.assertRaises(ValueError): self.run_case(b)
        b = self.body(); b['events'][0]['mvp_player'] = 'm0nesy'
        with self.assertRaises(ValueError): self.run_case(b)

    def test_started_past_year_and_historical_name_rejected(self):
        b = self.body(); b['year'] = '2025'
        with self.assertRaises(ValueError): self.run_case(b)
        with self.assertRaises(ValueError): simulate_future(self.data, self.body(), date(2026, 11, 2))
        for name, start, end in [('Past event', '2026-10-01', '2026-10-02'), ('Today', '2026-11-01', '2026-11-05'), ('Reverse', '2026-12-10', '2026-12-01'), ('Next year', '2027-01-01', '2027-01-03'), ('IEM Cologne Major 2026', '2026-12-01', '2026-12-05')]:
            b = self.body(); b['events'][0].update(event_id='custom', name=name, start_date=start, end_date=end, tier='Major')
            with self.assertRaises(ValueError): self.run_case(b)
        self.assertNotIn('iem-beijing-2026', [e['id'] for e in upcoming_catalog(date(2026, 11, 2))['events']])

    def test_team_consistency_and_honor_sample(self):
        b = self.body(); b['events'][0]['players'][1]['team'] = 'Spirit'
        with self.assertRaises(ValueError): self.run_case(b)
        b = self.body(); b['events'][0]['players'][0]['team_place'] = '冠军'
        with self.assertRaises(ValueError): self.run_case(b)
        b = self.body(); b['events'][0]['players'][0]['maps'] = 2
        with self.assertRaises(ValueError): self.run_case(b)

    def test_custom_future_schedule_and_input_shape(self):
        b = self.body(); b['events'][0].update(event_id='custom', name='Test future cup', start_date='2026-12-20', end_date='2026-12-22', tier='Major')
        r = self.run_case(b)
        self.assertIsNone(r['assumption_manifest'][0]['source_url'])
        self.assertEqual(r['assumption_manifest'][0]['players'][0]['provenance'], 'user_assumption')
        for events in [[], None, 'bad', [None], [{}]]:
            b = self.body(); b['events'] = events
            with self.assertRaises(ValueError): self.run_case(b)

    def test_future_and_undated_records_excluded_from_baseline(self):
        data = copy.deepcopy(self.data)
        p = next(p for p in data['seasons']['2026']['players'] if p['id'] == 'donk')
        for end in ['2026-12-31', None]:
            p['events'].append({**p['events'][0], 'rating': 3, 'maps': 50, 'period_end': end})
        r = simulate_future(data, self.body(), TODAY)
        self.assertEqual(r['excluded_records'], 2)
        self.assertEqual(r['rows'], self.run_case(self.body())['rows'])


if __name__ == '__main__':
    unittest.main()
