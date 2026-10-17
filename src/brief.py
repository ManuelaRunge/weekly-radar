"""Create a source-linked review inbox; no generative AI or publication."""
import datetime as dt
import json
import pathlib
from selection import select_items
ROOT=pathlib.Path(__file__).resolve().parents[1]
items=json.loads((ROOT/'data'/'items.json').read_text(encoding='utf-8')) if (ROOT/'data'/'items.json').exists() else []
today=dt.datetime.now(dt.timezone.utc).date()
groups=select_items(items,today)

lines=[f'# RIDA Radar — briefing ({today.isoformat()})','', '> Discovery candidates only. Verify dates, claims, event status and LinkedIn permalinks before sharing.', '', 'News covers the previous 30 days, with the last 7 days first and WHO leading within each period. Upcoming events cover the next 180 days, soonest first. Undated leads remain in data/items.json and are excluded from recent news.']
for kind,heading,limit in (
    ('last_7_days','Priority updates — last 7 days',30),
    ('last_30_days','Other updates — 8–30 days ago',30),
    ('event','Upcoming events — by date',20),
):
    lines.extend(['',f'## {heading}'])
    for i in groups[kind][:limit]:
        date=i['event_date'] if kind=='event' else i['published_date']
        lines.append(f'- **{date}** [{i["title"]}]({i["url"]}) — {i["source"]}')
    if not groups[kind]:lines.append('No eligible dated items in this section.')
lines.extend(['','## LinkedIn posts to review','Add verified public LinkedIn post permalinks to `config/manual_links.csv`; do not guess publication dates.','','## RIDA publishing shortlist','Choose at most 1–3 items manually. Nothing is approved or published by this script.'])
(ROOT/'output').mkdir(exist_ok=True)
(ROOT/'output'/'latest.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Created output/latest.md')
