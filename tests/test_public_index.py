import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from publish import START, END, embed_index, release_notes


class PublishingTests(unittest.TestCase):
    def test_index_preserves_surrounding_readme_and_is_idempotent(self):
        readme = '# Project\n\n[Manual link](https://example.org)\n' + START + '\nOld\n' + END + '\n[Footer](https://example.org)\n'
        feed = {'generated_date': '2026-11-07', 'sections': [
            {'title': 'This week', 'items': [{'title': 'Report', 'url': 'https://example.org/report'}]},
            {'title': 'Upcoming events', 'items': []},
        ]}
        result = embed_index(readme, feed)
        self.assertIn('## Selected links (2026-11-07)', result)
        self.assertIn('### This week\n\n- [Report](https://example.org/report)', result)
        self.assertIn('### Upcoming events', result)
        self.assertTrue(result.startswith('# Project'))
        self.assertTrue(result.endswith('[Footer](https://example.org)\n'))
        self.assertNotIn('\nOld\n', result)
        self.assertEqual(result, embed_index(result, feed))
        self.assertNotIn('source error(s)', result)

    def test_bad_markers_fail_without_overwriting_manual_readme(self):
        feed = {'generated_date': '2026-11-07', 'sections': []}
        for readme in ('No markers', START + START + END, END + START):
            with self.assertRaises(ValueError):
                embed_index(readme, feed)

    def test_full_briefing_attribution_and_parenthesized_urls_are_preserved(self):
        feed={'generated_date':'2026-11-07','sections':[{'title':'Upcoming events','items':[
            {'title':'Malaria [meeting]','url':'https://www.who.int/event-(mpag)','date':'2026-11-09','publisher':'WHO'}]}]}
        briefing='# Briefing\n\n## Upcoming events\n- Full source-linked event\n'
        readme='# Project\n'+START+'\nOld\n'+END+'\nFooter\n'
        result=embed_index(readme,feed,briefing,1)
        self.assertIn('[Malaria \\[meeting\\]](https://www.who.int/event-%28mpag%29) (WHO)',result)
        self.assertIn('**2026-11-09**',result)
        self.assertIn('<summary>Full source-linked briefing</summary>',result)
        self.assertIn('Full source-linked event',result)
        self.assertIn('**1 source error(s)**',result)
        self.assertEqual(result,embed_index(result,feed,briefing,1))

    def test_release_includes_full_briefing_and_coverage_gaps(self):
        now = dt.datetime(2026, 10, 17, 12, tzinfo=dt.timezone.utc)
        briefing = '# Briefing\n\n## News\n- Latest item\n'
        items = [dict(title='WHO update', source='WHO News', url='https://www.who.int/news/item/test',
                      published_date='2026-10-16')]
        errors = [dict(source='Blocked source', error='HTTP 403')]
        notes = release_notes(briefing, items, errors, now, 'radar-test', 'https://github.com/example/repo/actions/runs/1')
        self.assertIn(briefing, notes)
        self.assertIn('last 7 days: **1**', notes)
        self.assertIn('Tag: `radar-test`', notes)
        self.assertIn('coverage is incomplete', notes)
        self.assertIn('Blocked source', notes)
        self.assertIn('HTTP 403', notes)
        self.assertIn('[Workflow run]', notes)

    def test_successful_source_status_does_not_claim_verification(self):
        notes = release_notes('# Briefing\n', [], [], dt.datetime(2026, 10, 17, tzinfo=dt.timezone.utc))
        self.assertIn('without reported errors', notes)
        self.assertIn('verify original sources', notes)
        self.assertNotIn('coverage is incomplete', notes)


if __name__ == '__main__':
    unittest.main()
