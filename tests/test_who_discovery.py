import datetime as dt
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import collect
from selection import select_items

TODAY='2026-10-17'
ANNOUNCEMENT='WHO Pandemic Hub sets ambitious goal to detect new outbreaks within 24 hours'
NEWS_URL='https://www.who.int/news/item/12-10-2026-who-pandemic-hub-sets-ambitious-goal-to-detect-new-outbreaks-within-24-hours'
REPORT='Elimination of human onchocerciasis: progress report, 2025–2026'
ISSUE='https://www.who.int/publications/journals/weekly-epidemiological-record/wer101-40'
ANCHOR='onchocerciasis-elimination-of-human-onchocerciasis-progress-report-2025-2026'


class WHOResourceDiscoveryTests(unittest.TestCase):
    def test_headlines_catches_hub_announcement_and_follows_recent_pages(self):
        first=Mock(text=f'<main><a href="{NEWS_URL}" aria-label="{ANNOUNCEMENT}">12 October 2026 News release {ANNOUNCEMENT}</a></main>')
        second=Mock(text='<main><a href="/news/item/16-09-2026-earlier-announcement">Earlier announcement</a></main>')
        source=dict(name='WHO Headlines',url='https://www.who.int/news-room/headlines',category='global-health',method='who_headlines')
        with patch.object(collect,'TODAY',TODAY),patch.object(collect.requests,'get',side_effect=[first,second]) as get:
            records=collect.collect_source(source)
        self.assertEqual(get.call_count,2)
        self.assertEqual(get.call_args_list[1].args[0],source['url']+'/2')
        result=select_items(records,dt.date.fromisoformat(TODAY))['last_7_days']
        self.assertEqual([(i['title'],i['url'],i['published_date']) for i in result],[(ANNOUNCEMENT,NEWS_URL,'2026-10-12')])

    def test_wer_report_uses_issue_date_and_distinct_original_article_anchor(self):
        listing=Mock(text=f'<a href="{ISSUE}">HTML</a><a href="{ISSUE}/">Duplicate link</a>')
        issue=Mock(text=f'<div class="wer-panel-issue-meta">9 October 2026</div>'
            f'<div class="wer-block"><h2 id="{ANCHOR}">{REPORT}</h2></div>'
            '<div class="wer-block"><h2 id="dengue-global-dengue-update">Global dengue update</h2></div>')
        source=dict(name='WHO Weekly Epidemiological Record',url='https://www.who.int/publications/journals/weekly-epidemiological-record',category='global-health',method='who_wer')
        with patch.object(collect,'TODAY',TODAY),patch.object(collect.requests,'get',side_effect=[listing,issue]) as get:
            records=collect.collect_source(source)
        self.assertEqual(get.call_count,2)
        self.assertEqual(len(records),2)
        self.assertNotEqual(records[0]['id'],records[1]['id'])
        self.assertEqual(records[0]['url'],ISSUE+'#'+ANCHOR)
        self.assertEqual(records[0]['published_date'],'2026-10-09')
        landing=collect.record(REPORT,'https://www.who.int/publications/i/item/who-wer10140-290-297','WHO NTD','ntds','page',published_date='2026-10-09')
        chosen=select_items([landing]+records,dt.date.fromisoformat(TODAY))['last_30_days']
        reports=[i for i in chosen if i['title']==REPORT]
        self.assertEqual(len(reports),1)
        self.assertEqual(reports[0]['url'],ISSUE+'#'+ANCHOR)

    def test_old_issue_is_not_mistaken_for_recent_discovery(self):
        soup=BeautifulSoup(f'<div class="wer-panel-issue-meta">1 January 2025</div><div class="wer-block"><h2 id="report">{REPORT}</h2></div>','html.parser')
        with patch.object(collect,'TODAY',TODAY):
            self.assertEqual(collect.parse_wer_issue(soup,ISSUE,dict(name='WHO WER',category='global-health')),[])

    def test_wer_legacy_layout_uses_separate_article_anchors(self):
        soup=BeautifulSoup('<div class="wer-panel-issue-meta">25 September 2026</div>'
            '<div class="wer-block"><span class="wer-anchor" id="cholera"></span><h2>Cholera annual report</h2>'
            '<p>Text</p><span class="wer-anchor" id="plague"></span><h2>Human plague report</h2></div>','html.parser')
        with patch.object(collect,'TODAY',TODAY):
            records=collect.parse_wer_issue(soup,ISSUE,dict(name='WHO WER',category='global-health'))
        self.assertEqual([i['url'] for i in records],[ISSUE+'#cholera',ISSUE+'#plague'])

    def test_undated_issue_fails_instead_of_inventing_a_date(self):
        with self.assertRaises(ValueError):
            collect.parse_wer_issue(BeautifulSoup('<h2 id="report">Report</h2>','html.parser'),ISSUE,dict(name='WHO WER',category='global-health'))

    def test_only_wer_article_fragments_are_preserved(self):
        self.assertEqual(collect.clean_url(ISSUE+'?utm_source=test#'+ANCHOR),ISSUE+'#'+ANCHOR)
        self.assertEqual(collect.clean_url('https://example.org/article#navigation'),'https://example.org/article')


if __name__=='__main__':
    unittest.main()
