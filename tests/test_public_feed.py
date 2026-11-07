import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from public_feed import build_public_feed, canonical_url, public_sections, safe_url, topic_score

TODAY = dt.date(2026, 11, 7)


def example(title, days_ago=1, **fields):
    data = {
        'title': title,
        'url': 'https://www.who.int/news/item/01-11-2026-' + str(len(title)) + '-' + title.lower().replace(' ', '-'),
        'published_date': (TODAY - dt.timedelta(days=days_ago)).isoformat(),
        'event_date': '',
        'source': 'WHO Headlines',
        'category': 'global-health',
        'verification': 'unverified',
        'editorial_status': 'inbox',
        'notes': 'PRIVATE editorial note – not for publication',
        'first_seen': TODAY.isoformat(),
    }
    data.update(fields)
    return data


class PublicFeedTests(unittest.TestCase):
    def test_url_checks_and_tracking_removal(self):
        self.assertTrue(safe_url('https://www.who.int/news/a'))
        self.assertFalse(safe_url('javascript:alert(1)'))
        self.assertFalse(safe_url('http://example.org/a'))
        self.assertFalse(safe_url('https://user:pass@example.org/item'))
        self.assertTrue(safe_url('https://www.who.int/events/detail/meeting-(mpag)'))
        self.assertFalse(safe_url('https://example.org:invalid/item'))
        self.assertEqual(canonical_url('https://example.org/a?utm_source=x&v=2#section'),
                         'https://example.org/a?v=2#section')

    def test_scope_date_filter_and_private_fields(self):
        items = [
            example('Malaria vaccine assessment', 0),
            example('Neglected tropical diseases report', 9),
            example('Malaria report from a month ago', 18),
            example('Malaria report outside the news window', 31),
            example('Malaria report with unknown date', published_date='', first_seen=TODAY.isoformat()),
            example('Celebrity health concert', 0),
            example('Upcoming malaria webinar', 50, published_date='', event_date='2026-12-01'),
        ]
        feed = build_public_feed(items, TODAY)
        sections = {s['id']: s['items'] for s in feed['sections']}
        self.assertEqual([v['title'] for v in sections['this_week']], ['Malaria vaccine assessment'])
        self.assertEqual({v['title'] for v in sections['previous_week']}, {'Neglected tropical diseases report','Malaria report from a month ago'})
        self.assertEqual([v['title'] for v in sections['upcoming']], ['Upcoming malaria webinar'])
        data = str(feed)
        self.assertNotIn('PRIVATE editorial note', data)
        self.assertNotIn('first_seen', data)
        self.assertNotIn('why_it_fits', data)
        self.assertNotIn('Malaria report outside the news window', data)

    def test_duplicate_urls_and_titles(self):
        same = example('Malaria disease surveillance')
        variants = [same, dict(same, url=same['url'] + '?utm_source=mail'),
                    dict(same, url='https://www.who.int/other/path')]
        selected = public_sections(variants, TODAY)[0]['items']
        self.assertEqual(len(selected), 1)

    def test_wer_issue_anchors_not_deduplicated(self):
        a = example('Global leishmaniasis surveillance report')
        a['url'] = 'https://www.who.int/publications/journals/weekly-epidemiological-record/wer101-44#leishmaniasis'
        b = example('Multi-country cholera surveillance report')
        b['url'] = 'https://www.who.int/publications/journals/weekly-epidemiological-record/wer101-44#cholera'
        self.assertEqual(len(public_sections([a, b], TODAY)[0]['items']), 2)

    def test_editorial_exclusions(self):
        items = [example('Malaria policy analysis', editorial_status='private'),
                 example('Malaria model guidance', editorial_status='ignored'),
                 example('Malaria surveillance', verification='rejected')]
        self.assertFalse(public_sections(items, TODAY)[0]['items'])

    def test_relevance_prefers_domain_knowledge_over_generic_headline(self):
        self.assertGreater(topic_score(example('Malaria transmission modelling report')),
                           topic_score(example('Global health update')))
        self.assertEqual(topic_score(example('Highlighted signals and events')), 0)

    def test_who_priority_financing_and_valid_parenthesized_event_links(self):
        who=example('Global health policy update', source='WHO Headlines')
        specialist=example('Malaria transmission modelling report',url='https://malvax.org/news',source='MalVax')
        financing=example('Domestic budget allocation approved',url='https://example.org/finance',source='Funder',category='health-financing')
        event=example('Malaria programme webinar',event_date='2026-12-01',url='https://www.who.int/events/meeting-(mpag)')
        feed=public_sections([specialist,who,financing,event],TODAY)
        self.assertEqual(feed[0]['items'][0]['publisher'],'WHO Headlines')
        self.assertIn('Domestic budget allocation approved',[i['title'] for i in feed[0]['items']])
        self.assertEqual(len(feed[2]['items']),1)

    def test_malformed_url_is_excluded_before_ranking(self):
        malformed=example('Malaria report',url='https://[broken')
        self.assertFalse(public_sections([malformed],TODAY)[0]['items'])


if __name__ == '__main__':
    unittest.main()
