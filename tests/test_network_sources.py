import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from brief import render_briefing
from collect import date_from_text, parse_cards
from newsletter_ai import shortlist


class NetworkSourceTests(unittest.TestCase):
    def test_all_requested_domains_are_configured(self):
        root=Path(__file__).resolve().parents[1]
        sources=json.loads((root/'config/sources.json').read_text(encoding='utf-8'))
        hosts={urlsplit(source['url']).hostname for source in sources}
        self.assertTrue({'www.ammnet.org','www.measles-analytics.org','www.vaccineimpact.org',
                         'tb-mac.org','dndi.org','cema-africa.uonbi.ac.ke'} <= hosts)

    def test_ammnet_event_uses_title_and_full_event_date(self):
        html='<a class="event-card" href="/seminars/elimination"><div class="event-date">November 3, 2026</div><div class="card-title">Malaria elimination seminar</div><p>'+('Long description '*50)+'</p></a>'
        source=dict(name='AMMnet',url='https://www.ammnet.org/',category='events',
                    item_selector='a.event-card',title_selector='.card-title',date_selector='.event-date',date_type='event')
        result=parse_cards(html,source)[0]
        self.assertEqual(result['title'],'Malaria elimination seminar')
        self.assertEqual(result['event_date'],'2026-11-03')
        self.assertEqual(result['published_date'],'')

    def test_dndi_date_and_title_survive_nested_card_layout(self):
        html='<div class="ae_data elementor"><span>News</span><div>9 Oct 2026</div><section><h2><a href="https://dndi.org/news/2026/test/">New treatment research</a></h2></section></div>'
        source=dict(name='DNDi',url='https://dndi.org/',category='ntds',
                    item_selector='.ae_data.elementor',title_selector='h2 a')
        result=parse_cards(html,source)[0]
        self.assertEqual(result['published_date'],'2026-10-09')
        self.assertEqual(result['url'],'https://dndi.org/news/2026/test/')

    def test_explicit_date_ranges_use_start_and_missing_year_is_not_guessed(self):
        self.assertEqual(date_from_text('10 - 13 Nov 2026'),'2026-11-10')
        self.assertEqual(date_from_text('November 3, 2026'),'2026-11-03')
        self.assertEqual(date_from_text('14 Sept. at 14:00 BST'),'')

    def test_missing_card_layout_is_reported(self):
        with self.assertRaises(ValueError):
            parse_cards('<main>No cards</main>',dict(item_selector='.event-card',title_selector='.card-title'))

    def test_briefing_puts_publishers_in_parentheses_and_normalizes_dashes(self):
        today=dt.date(2026,10,17)
        items=[dict(title='Research\u2014update',url='https://example.org/news',source='VIMC',published_date='2026-10-16'),
               dict(title='Event\u2014training',url='https://example.org/event',source='AMMnet Events',publisher='AMMnet',event_date='2026-11-03')]
        text=render_briefing(items,today)
        self.assertNotIn('\u2014',text)
        self.assertIn('[Research\u2013update](https://example.org/news) (VIMC)',text)
        self.assertIn('[Event\u2013training](https://example.org/event) (AMMnet)',text)

    def test_newsletter_packet_normalizes_archived_titles(self):
        today=dt.datetime.now(dt.timezone.utc).date().isoformat()
        records=shortlist([dict(title='News\u2014update',source='Network\u2014publisher',url='https://example.org/news',published_date=today)])
        self.assertEqual(records[0]['title'],'News\u2013update')
        self.assertEqual(records[0]['source'],'Network\u2013publisher')


if __name__=='__main__':
    unittest.main()
