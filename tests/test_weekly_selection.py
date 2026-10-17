import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import collect
from newsletter_ai import shortlist
from selection import item_kind, select_items
from bs4 import BeautifulSoup

TODAY = dt.date(2026, 10, 17)


def item(title, age=0, source='MalVax', **extra):
    result = dict(title=title, url='https://example.org/' + title,
                  source=source, category='news', published_date=(TODAY-dt.timedelta(days=age)).isoformat(),
                  first_seen=TODAY.isoformat(), method='page')
    result.update(extra)
    return result


class WeeklySelectionTests(unittest.TestCase):
    def test_date_boundaries_and_no_first_seen_fallback(self):
        for age, expected in ((0, 'last_7_days'), (7, 'last_7_days'),
                              (8, 'last_30_days'), (30, 'last_30_days'),
                              (31, None), (-1, None)):
            self.assertEqual(item_kind(item('news', age), TODAY), expected)
        for publication in ('', 'invalid', '2026-02-30'):
            self.assertIsNone(item_kind(item('unknown', published_date=publication), TODAY))

    def test_recency_groups_and_who_priority(self):
        groups=select_items([item('MalVax-new',0),item('WHO-new',6,'WHO News'),
                             item('WHO-old',8,'WHO Disease Outbreak News')],TODAY)
        self.assertEqual([i['title'] for i in groups['last_7_days']],['WHO-new','MalVax-new'])
        self.assertEqual([i['title'] for i in groups['last_30_days']],['WHO-old'])

    def test_events_are_chronological_and_not_recycled_as_news(self):
        groups=select_items([item('later',200,event_date='2027-01-31'),
                             item('sooner',200,event_date='2026-10-20'),
                             item('expired',0,event_date='2026-10-16'),
                             item('too-far',0,event_date='2027-10-17')],TODAY)
        self.assertEqual([i['title'] for i in groups['event']],['sooner','later'])
        self.assertFalse(groups['last_7_days'])

    def test_removed_trackers_cannot_reappear_from_archive(self):
        for source in ('malariasimulation releases','OpenMalaria releases'):
            self.assertIsNone(item_kind(item('release',source=source),TODAY))

    def test_packet_uses_same_rules_and_keeps_calendar(self):
        today=dt.datetime.now(dt.timezone.utc).date()
        news=[item('news'+str(n),published_date=today.isoformat()) for n in range(100)]
        event=item('calendar',event_date=(today+dt.timedelta(days=2)).isoformat())
        stale=item('stale',published_date=(today-dt.timedelta(days=31)).isoformat(),method='manual')
        packet=shortlist(news+[event,stale],max_items=9)
        self.assertLessEqual(len(packet),9)
        self.assertIn('calendar',[i['title'] for i in packet])
        self.assertNotIn('stale',[i['title'] for i in packet])
        self.assertEqual(len(shortlist(news,max_items=1)),1)


class CollectionTests(unittest.TestCase):
    def test_outbreak_timestamp_and_original_who_publication_date(self):
        self.assertEqual(collect.date_from_text('2026-10-15T16:00:00Z'),'2026-10-15')
        response=Mock(content=b'''<rss version="2.0"><channel><title>WHO</title>
        <item><title>Old article reissued</title><link>https://www.who.int/news/item/27-08-2020-old-news</link>
        <pubDate>Sat, 10 Oct 2026 18:16:58 +0000</pubDate></item></channel></rss>''')
        with patch.object(collect.requests,'get',return_value=response):
            records=collect.collect_source(dict(url='https://www.who.int/feed',method='feed',name='WHO News',category='global-health'))
        self.assertEqual(records[0]['published_date'],'2020-08-27')
        self.assertIsNone(item_kind(records[0],TODAY))

    def test_source_feed_publication_date_and_snt_topic(self):
        response=Mock(content=b'''<rss version="2.0"><channel><title>Test</title>
        <item><title>Malaria subnational tailoring update</title><link>https://example.org/snt</link>
        <pubDate>Wed, 07 Oct 2026 18:16:58 +0000</pubDate></item></channel></rss>''')
        with patch.object(collect.requests,'get',return_value=response):
            records=collect.collect_source(dict(url='https://example.org/feed',method='feed',name='SNT',category='malaria'))
        self.assertEqual(records[0]['published_date'],'2026-10-07')
        self.assertEqual(records[0]['category'],'snt')

    def test_explicit_page_dates(self):
        anchor=BeautifulSoup('<div><time datetime="2026-10-12">12 October 2026</time><a>News</a></div>','html.parser').a
        self.assertEqual(collect.page_dates(anchor,'https://example.org/news'),{'published_date':'2026-10-12'})
        self.assertEqual(collect.page_dates(anchor,'https://www.who.int/news-room/events/detail/2026/10/27/meeting'),{'event_date':'2026-10-27'})
        self.assertEqual(collect.page_dates(anchor,'https://www.who.int/news/item/15-10-2026-update'),{'published_date':'2026-10-15'})

    def test_manual_dates_and_editorial_state_survive_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config').mkdir()
            (root/'data').mkdir()
            (root/'config'/'sources.json').write_text('[{"name":"Test"}]',encoding='utf-8')
            (root/'config'/'manual_links.csv').write_text(
                'title,url,source,category,published_date,event_date,notes\n'
                'SNT \u2192 training,https://example.org/event,WHO,events,,2026-11-01,Manual\n',encoding='utf-8')
            old=collect.record('Old','https://example.org/event','Test','events','page')
            old.update(first_seen='2026-09-01',editorial_status='saved')
            (root/'data'/'items.json').write_text(json.dumps([old]),encoding='utf-8')
            with patch.object(collect,'ROOT',root),patch.object(collect,'collect_source',return_value=[old]):
                collect.run()
                collect.run()
            result=json.loads((root/'data'/'items.json').read_text(encoding='utf-8'))
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['event_date'],'2026-11-01')
            self.assertEqual(result[0]['first_seen'],'2026-09-01')
            self.assertEqual(result[0]['editorial_status'],'saved')
            self.assertEqual(result[0]['title'],'SNT \u2192 training')


if __name__ == '__main__':
    unittest.main()
