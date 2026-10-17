import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from publish import START, END, embed_briefing, release_notes


class PublishingTests(unittest.TestCase):
    def test_embed_preserves_manual_sections_and_is_idempotent(self):
        readme = '# Project\n\nManual introduction\n' + START + '\nOld\n' + END + '\nManual footer\n'
        briefing = '# Briefing\n\n## News\n- [Item](https://example.org/)\n'
        result = embed_briefing(readme, briefing, 1)
        self.assertIn('### Briefing\n\n#### News', result)
        self.assertIn('- [Item](https://example.org/)', result)
        self.assertTrue(result.startswith('# Project\n\nManual introduction'))
        self.assertTrue(result.endswith('\nManual footer\n'))
        self.assertNotIn('\nOld\n', result)
        self.assertIn('**1 source error(s)**', result)
        self.assertEqual(embed_briefing(result, briefing, 1), result)

    def test_bad_markers_fail_without_overwriting_manual_readme(self):
        for readme in ('No markers', START + START + END, END + START):
            with self.assertRaises(ValueError):
                embed_briefing(readme, '# Briefing', 0)

    def test_release_includes_full_briefing_summary_and_coverage_gaps(self):
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
