import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import collect
from brief import render_briefing
from funder_sources import gates_news, keyword_match, worldbank_news
from selection import select_items


class FunderSourcesTests(unittest.TestCase):
    def test_financing_and_health_groups_exclude_unrelated_announcements(self):
        groups=[['financ','grant','million','budget','funding'],['health','maternal','vaccine']]
        self.assertTrue(keyword_match('Country receives $20 million for maternal health',groups))
        self.assertTrue(keyword_match('Domestic health budget increases',groups))
        self.assertFalse(keyword_match('Foundation commits $20 million to farming',groups))
        self.assertFalse(keyword_match('Vaccine research findings released',groups))
        self.assertFalse(keyword_match('Said the health minister',groups))

    def test_card_filter_uses_source_summary_and_explicit_date(self):
        html='<div class="feed__text"><time datetime="2026-10-22T11:27:50+00:00">22 October 2026</time><p><a href="/country-update">Country immunisation update</a></p><div class="feed-description">New financing for vaccines</div></div>'
        source=dict(name='Gavi',url='https://www.gavi.org/news',category='health-financing',method='cards',
                    item_selector='.feed__text',title_selector='p > a',date_selector='time',summary_selector='.feed-description',keyword_groups=[['financ']])
        with patch.object(collect.requests,'get',return_value=Mock(text=html)):
            records=collect.collect_source(source)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['published_date'],'2026-10-22')
        self.assertIn('financing',records[0]['notes'])

    def test_feed_summary_financing_is_not_missed(self):
        content=b'<rss version="2.0"><channel><item><title>Country health update</title><link>https://example.org/news</link><pubDate>Fri, 23 Oct 2026 10:54:38 GMT</pubDate><description>New grant approved for health services</description></item></channel></rss>'
        source=dict(name='Funder',url='https://example.org/feed',category='health-financing',method='feed',keyword_groups=[['grant']])
        with patch.object(collect.requests,'get',return_value=Mock(content=content)):
            records=collect.collect_source(source)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['published_date'],'2026-10-23')

    def test_gates_uses_publisher_listing_configuration_and_dates(self):
        listing=Mock(text='''<div data-model='{"url":"/api/dynamiccontentlisting"}' data-query='{"listingId":"current-id"}'></div>''')
        response=Mock()
        response.json.return_value={'results':[dict(title='Foundation commits $100 million to maternal health',contentUrl='/ideas/media-center/press-releases/2026/10/health',date='Oct 12, 2026',body='')]}
        source=dict(name='Gates Foundation',url='https://www.gatesfoundation.org/ideas/media-center',category='health-financing')
        with patch('funder_sources.requests.get',side_effect=[listing,response]) as get:
            records=gates_news(source,{},collect.record,collect.date_from_text)
        self.assertEqual(records[0]['published_date'],'2026-10-12')
        self.assertTrue(records[0]['url'].startswith('https://www.gatesfoundation.org/'))
        self.assertEqual(get.call_args.kwargs['params']['listingId'],'current-id')

    def test_worldbank_extracts_national_financing_and_secure_original_link(self):
        listing=Mock(text='<div data-url="https://search.worldbank.org/api/v2/news?format=xml&amp;rows=5&amp;lang_exact=English"></div>')
        response=Mock()
        response.json.return_value={'documents':{'id':dict(title={'cdata!':'Country receives health financing'},url='http://www.worldbank.org/en/news/press-release/2026/10/13/health',lnchdt='2026-10-13T09:00:00Z',content_1000={'cdata!':'$80 million grant for national health services'})}}
        source=dict(name='World Bank',url='https://www.worldbank.org/en/topic/health/news',category='health-financing')
        with patch('funder_sources.requests.get',side_effect=[listing,response]) as get:
            records=worldbank_news(source,{},collect.record,collect.date_from_text)
        self.assertEqual(records[0]['published_date'],'2026-10-13')
        self.assertTrue(records[0]['url'].startswith('https://'))
        self.assertIn('national health',records[0]['notes'])
        self.assertEqual(get.call_args.kwargs['params']['format'],'json')

    def test_financing_uses_existing_recency_sections_only(self):
        items=[dict(title='Health financing grant',url='https://example.org/grant',source='Funder',category='health-financing',published_date='2026-10-23'),
               dict(title='Old financing grant',url='https://example.org/old',source='Funder',category='health-financing',published_date='2026-08-01')]
        today=dt.date(2026,10,24)
        groups=select_items(items,today)
        self.assertEqual(len(groups['last_7_days']),1)
        text=render_briefing(items,today)
        self.assertIn('](https://example.org/grant) (Funder)',text)
        self.assertNotIn('Old financing grant',text)
        self.assertNotIn('## Health financing',text)
        self.assertNotIn('## Funders',text)

    def test_configured_funders_use_existing_news_category_rules(self):
        root=Path(__file__).resolve().parents[1]
        sources=json.loads((root/'config/sources.json').read_text(encoding='utf-8'))
        funders=[source for source in sources if source['category']=='health-financing']
        self.assertEqual({source['name'] for source in funders},{'The Global Fund','Gavi, the Vaccine Alliance','World Bank','Gates Foundation','Wellcome'})
        self.assertTrue(all(source.get('keyword_groups') for source in funders))


if __name__=='__main__':
    unittest.main()
