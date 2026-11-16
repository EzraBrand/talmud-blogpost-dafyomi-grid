import csv
import tempfile
import unittest
from pathlib import Path
from build_blogpost_dafyomi_db import supplement_recent_posts


class RecentPostsTests(unittest.TestCase):
    def test_series_reposts_and_drafts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'posts.csv'
            with path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['post_id', 'post_date', 'is_published', 'title'])
                writer.writerows([
                    ['1.old', '2026-10-01', 'true', 'Pt1 Study (Sanhedrin 26a-b)'],
                    ['2.new', '2026-11-04', 'true', 'Pt1 Study (Sanhedrin 26a-b)'],
                    ['3.part-two', '2026-11-05', 'true', 'Pt2 Study (Sanhedrin 26a-b)'],
                    ['4.draft', '', 'false', 'Draft (Sanhedrin 26a-b)'],
                    ['5.mishnah', '2026-11-06', 'true', 'Mishnah (Mishnah Sanhedrin 1:1)'],
                ])
            calendar = {('Sanhedrin', 26): '2032-06-15'}
            rows = supplement_recent_posts([], path, calendar, '2026-10-01')
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['blogpost title'], 'Study')
            self.assertEqual([p['label'] for p in rows[0]['part_links']], ['Pt1', 'Pt2'])
            self.assertTrue(rows[0]['part_links'][0]['url'].endswith('/new'))
            self.assertEqual(rows[0]['__date_iso'], '2032-06-15')
            supplement_recent_posts(rows, path, calendar, '2026-10-01')
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]['part_links']), 2)
