import csv
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from collect import date_from_text, parse_astmh_meetings, parse_cards
from selection import select_items
from public_feed import public_sections


class ConferenceTests(unittest.TestCase):
    def source(self, name):
        return next(s for s in json.loads((ROOT/'config/sources.json').read_text()) if s['name']==name)

    def test_month_first_range_uses_start(self):
        for value in ('April 26-30, 2027','November 18 – 22, 2026'):
            self.assertEqual(date_from_text(value), '2027-04-26' if value.startswith('April') else '2026-11-18')
        self.assertEqual(date_from_text('April 26-30'), '')

    def test_astmh_cards_keep_news_and_event_dates_separate(self):
        news='<div class="md:flex-row gap-5"><div><a href="/annual-meeting/exhibitors"></a></div><div><h6>Meeting research exhibitors</h6><p class="mt-auto">18 Nov 2026</p></div></div>'
        event='<div class="w-full sm:flex-row"><div><div class="flex flex-col"><span>02</span><span>Dec 2026</span></div><a href="/events/cme"></a></div><div><h3>CME deadline</h3></div></div>'
        n=parse_cards(news,self.source('ASTMH News'))[0]
        e=parse_cards(event,self.source('ASTMH Events'))[0]
        self.assertEqual((n['published_date'],n['event_date']),('2026-11-18',''))
        self.assertEqual((e['published_date'],e['event_date']),('','2026-12-02'))

    def test_astmh_archive_uses_next_meeting_not_page_posted_date(self):
        html='<main>Posted 14 October 2025 <p>2026 Annual Meeting November 18 – 22, 2026</p><p>2027 Annual Meeting November 7-11, 2027</p><p>2028 Annual Meeting October 18-22, 2028</p></main>'
        with patch('collect.TODAY','2026-11-23'):
            result=parse_astmh_meetings(html,self.source('ASTMH Annual Meetings'))
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['event_date'],'2027-11-07')
        self.assertEqual(result[0]['published_date'],'')
        with self.assertRaises(ValueError):
            parse_astmh_meetings('<main>Empty page</main>',self.source('ASTMH Annual Meetings'))

    def test_manual_conferences_respect_horizon_and_public_selection(self):
        with (ROOT/'config/manual_links.csv').open(encoding='utf-8',newline='') as f:
            rows=list(csv.DictReader(f))
        today=dt.date(2026,11,23)
        events=select_items(rows,today)['event']
        self.assertTrue(any('MIM' in r['title'] for r in events))
        self.assertFalse(any('ECTMIH' in r['title'] or 'EPIDEMICS' in r['title'] for r in events))
        upcoming=next(s for s in public_sections(rows,today) if s['id']=='upcoming')
        self.assertTrue(any('MIM' in r['title'] for r in upcoming['items']))
        for label in ('ECTMIH','EPIDEMICS'):
            item=next(r for r in rows if label in r['title'])
            self.assertEqual(item['published_date'],'')
            self.assertIn(item,select_items(rows,dt.date(2027,7,1))['event'])
            future=next(s for s in public_sections(rows,dt.date(2027,7,1)) if s['id']=='upcoming')
            self.assertTrue(any(label in r['title'] for r in future['items']))


if __name__=='__main__':
    unittest.main()
