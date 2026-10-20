import unittest
from datetime import date, timedelta

import build_schedule_v2 as v2


class ScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = v2.TorahIndex()
        cls.rows = v2.build_rows()

    def portions(self, text):
        return {p['name'] for ref in self.index.refs(text) for p in self.index.portions_for(ref)}

    def test_unique_portions(self):
        self.assertEqual(len(self.index.portions), 54)
        self.assertEqual(self.index.verses['Genesis'][31], 33)
        self.assertEqual(self.index.verses['Numbers'][24], 19)

    def test_multi_portion_ranges_include_end(self):
        self.assertEqual(self.portions('Genesis 28-32'), {'Toldot', 'Vayetzei', 'Vayishlach'})
        self.assertEqual(self.portions('Genesis 28:10-32:33'), {'Vayetzei', 'Vayishlach'})
        self.assertEqual(self.portions('Deuteronomy 31-34'), {'Vayeilech', "Ha'azinu", 'Vezot Haberakhah'})

    def test_split_chapter_majority_and_disjoint_references(self):
        self.assertEqual(self.portions('Genesis 6'), {'Noach'})
        self.assertEqual(self.portions('Numbers 3 and 11'), {'Bamidbar', "Beha'alotcha"})
        self.assertEqual(self.portions('Genesis 4:7, 49:7; Exodus 17:9'), {'Bereshit', 'Vayechi', 'Beshalach'})

    def test_reject_invalid_or_non_torah_references(self):
        self.assertEqual(self.index.refs('Genesis 100; Genesis 1:99; Isaiah 38'), [])

    def test_recall_and_series_urls(self):
        jacob = [r for r in self.rows if r['type'] == 'Parasha' and r['title'].startswith('Jacob in Genesis 28-32')]
        self.assertTrue({'Vayetzei', 'Vayishlach'} <= {r['trigger'] for r in jacob})
        self.assertTrue(all(r['url'].startswith('https://www.ezrabrand.com/') for r in self.rows))
        ritual = [r for r in self.rows if r['type'] == 'Parasha' and r['title'].startswith('Tzitzit, Tefillin')]
        self.assertTrue({'Vaetchanan', "Sh'lach"} <= {r['trigger'] for r in ritual})

    def test_regions_and_lead_time(self):
        parasha = [r for r in self.rows if r['type'] == 'Parasha']
        self.assertTrue(any(r['dates']['israel'] != r['dates']['diaspora'] for r in parasha))
        for row in parasha:
            for region in ['israel', 'diaspora']:
                for event in row['dates'][region]:
                    reading, post = date.fromisoformat(event['reading']), date.fromisoformat(event['post'])
                    self.assertEqual(post.weekday(), 6)
                    self.assertTrue(1 <= (reading - post).days <= 7)
                    if reading.weekday() == 5:
                        self.assertEqual(reading - post, timedelta(days=6))

    def test_israel_reading_events_and_ranges(self):
        readings = v2.reading_events('israel')
        next_reading = next(e for e in readings if e['reading'] == '2026-10-24')
        self.assertEqual(next_reading['label'], 'Lech-Lecha')
        self.assertEqual(next_reading['chapter_range'], 'Gen 12–17')
        self.assertEqual(next_reading['parasha_range'], 'Genesis 12:1-17:27')
        text = v2.calendar_ics(self.rows, 'israel', 'Parasha')
        self.assertIn('UID:v2-israel-parasha-reading-2026-10-24@ezrabrand.com', text)
        self.assertIn('SUMMARY:Parashat Lech-Lecha (Gen 12–17)', text)
        self.assertEqual(v2.previous_sunday('2026-10-24'), '2026-10-18')
        self.assertEqual(v2.previous_sunday('2027-10-24'), '2027-10-17')

    def test_daf_preserves_index_and_includes_next_cycles(self):
        daf = [r for r in self.rows if r['type'] == 'Daf Yomi']
        self.assertEqual(len(daf), len(v2.source_posts()))
        self.assertTrue(any(len(r['dates']['israel']) > 1 for r in daf))
        for r in daf:
            self.assertTrue(all(d['post'] == d['reading'] for d in r['dates']['israel']))

    def test_calendar_union_deduplication_and_folding(self):
        def uids(text):
            return [l for l in text.split('\r\n') if l.startswith('UID:')]
        for region in ['israel', 'diaspora']:
            combined = v2.calendar_ics(self.rows, region)
            ids = uids(combined)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(set(ids), set(uids(v2.calendar_ics(self.rows, region, 'Parasha'))) | set(uids(v2.calendar_ics(self.rows, region, 'Daf Yomi'))))
            self.assertTrue(all(len(line.encode()) <= 75 for line in combined.split('\r\n')))
            self.assertIn('CATEGORIES:Parasha', combined)
            self.assertIn('CATEGORIES:Daf Yomi', combined)


if __name__ == '__main__':
    unittest.main()
