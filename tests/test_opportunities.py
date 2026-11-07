import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from opportunities import build_scan, evergreen_selection

TODAY = dt.date(2026, 11, 7)
BACKLOG = json.loads((Path(__file__).resolve().parents[1] / 'config/evergreen_backlog.json').read_text(encoding='utf-8'))


class OpportunityTests(unittest.TestCase):
    def test_backlog_keeps_requested_topics(self):
        names = {record['id'] for record in BACKLOG}
        self.assertTrue({'r-packages-2026', 'who-snt-process', 'stratification-targeting-tailoring',
                         'turtle-logo', 'professional-lessons', 'website-introduction'} <= names)
        self.assertEqual(len({record['id'] for record in BACKLOG}), len(BACKLOG))
        self.assertLessEqual(len(evergreen_selection(BACKLOG, TODAY)), 5)
        self.assertNotIn('published', [r['status'] for r in evergreen_selection(BACKLOG, TODAY)])

    def test_timely_suggestions_are_questions_not_claims(self):
        public = {'sections': [{'id': 'this_week', 'items': [{
            'title': 'Malaria vaccine trial announcement', 'url': 'https://example.org/a',
            'date': '2026-11-06', 'publisher': 'Example', 'topic': 'Vaccines & immunisation'
        }]}]}
        scan = build_scan(public, BACKLOG, TODAY)
        t = scan['lanes']['timely'][0]
        self.assertEqual(t['best_channel'], 'Personal profile')
        self.assertEqual(t['status'], 'unreviewed_discovery_lead')
        self.assertIn('?', t['core_angle_for_review'])
        self.assertEqual(len(scan['lanes']['evergreen']), 5)

    def test_private_and_finished_backlog_entries_are_not_suggested(self):
        backlog=[dict(record,status=status) for record,status in zip(BACKLOG,
            ['private','do_not_publish','ignored','published','archived','rejected'])]
        self.assertEqual(evergreen_selection(backlog,TODAY),[])


if __name__ == '__main__':
    unittest.main()
