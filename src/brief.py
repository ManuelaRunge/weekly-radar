"""Create a private, source-linked review inbox; no generative AI or publication."""
import datetime as dt
import json
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
items=json.loads((ROOT/'data'/'items.json').read_text(encoding='utf-8')) if (ROOT/'data'/'items.json').exists() else []
today=dt.date.today()
recent=[]
upcoming=[]
for item in items:
    try:
        if item.get('published_date') and 0 <= (today-dt.date.fromisoformat(item['published_date'])).days <= 14:recent.append(item)
        if item.get('event_date') and today <= dt.date.fromisoformat(item['event_date']) <= today+dt.timedelta(days=180):upcoming.append(item)
    except ValueError:continue

lines=[f'# RIDA Radar — private briefing ({today.isoformat()})','', '> Discovery candidates only. Verify dates, claims, event status and LinkedIn permalinks before sharing.','','## Upcoming events']
for i in upcoming[:20]:lines.append(f'- **{i["event_date"]}** [{i["title"]}]({i["url"]}) — {i["source"]}')
lines.extend(['','## Dated updates (previous 14 days)'])
for i in recent[:30]:lines.append(f'- **{i["published_date"]}** [{i["title"]}]({i["url"]}) — {i["source"]}')
lines.extend(['','## Newly discovered links (check dates manually)'])
for i in items[:45]:
    if not i.get('published_date') and not i.get('event_date'):
        lines.append(f'- [{i["title"]}]({i["url"]}) — {i["source"]}; seen {i["first_seen"]}')
lines.extend(['','## LinkedIn posts to review','Add verified public LinkedIn post permalinks to `config/manual_links.csv`; do not guess publication dates.','','## RIDA publishing shortlist','Choose at most 1–3 items manually. Nothing is approved or published by this script.'])
(ROOT/'output').mkdir(exist_ok=True)
(ROOT/'output'/'latest.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Created output/latest.md')
