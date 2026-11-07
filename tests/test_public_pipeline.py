import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import opportunities
import public_feed
import publish


class PublicPipelineTests(unittest.TestCase):
    def test_offline_generators_produce_feed_planning_readme_and_notes(self):
        today=dt.datetime.now(dt.timezone.utc).date()
        items=[dict(title='Malaria surveillance report',url='https://www.who.int/report',source='WHO News',
                    category='malaria',published_date=today.isoformat(),notes='EDITORIAL NOTE DO NOT EXPORT',
                    first_seen=today.isoformat(),editorial_status='inbox',verification='unverified')]
        backlog=json.loads((Path(__file__).resolve().parents[1]/'config/evergreen_backlog.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for folder in ('data','output','config'):(root/folder).mkdir()
            (root/'data/items.json').write_text(json.dumps(items),encoding='utf-8')
            (root/'data/errors.json').write_text('[]',encoding='utf-8')
            (root/'config/evergreen_backlog.json').write_text(json.dumps(backlog),encoding='utf-8')
            briefing='# RIDA Radar – briefing\n\n- Full source-linked inbox item\n'
            (root/'output/latest.md').write_text(briefing,encoding='utf-8')
            (root/'README.md').write_text('# Project\n'+publish.START+'\nOld\n'+publish.END+'\nManual footer\n',encoding='utf-8')
            with patch.object(public_feed,'ROOT',root),patch.object(opportunities,'ROOT',root),patch.object(publish,'ROOT',root),contextlib.redirect_stdout(io.StringIO()):
                public_feed.main()
                opportunities.main()
                publish.main()
            feed=json.loads((root/'output/public.json').read_text(encoding='utf-8'))
            record=feed['sections'][0]['items'][0]
            self.assertEqual(set(record),{'title','url','date','publisher','topic'})
            self.assertNotIn('EDITORIAL NOTE',json.dumps(feed))
            scan=json.loads((root/'output/opportunity_scan.json').read_text(encoding='utf-8'))
            self.assertEqual(len(scan['lanes']['timely']),1)
            self.assertEqual(len(scan['lanes']['evergreen']),5)
            readme=(root/'README.md').read_text(encoding='utf-8')
            self.assertIn('Selected links',readme)
            self.assertIn('(WHO News)',readme)
            self.assertIn('<summary>Full source-linked briefing</summary>',readme)
            self.assertIn('Full source-linked inbox item',readme)
            self.assertIn('Manual footer',readme)
            self.assertIn(briefing,(root/'output/release_notes.md').read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
