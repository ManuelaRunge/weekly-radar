"""Shared weekly selection rules for the briefing and newsletter packet."""
import datetime as dt
import re
from urllib.parse import urlsplit

LOOKBACK_DAYS = 30
PROMINENT_DAYS = 7
EVENT_HORIZON_DAYS = 180


def parse_date(value):
    try:
        return dt.date.fromisoformat(value) if value else None
    except (ValueError, TypeError):
        return None


def excluded(item):
    text = ' '.join(str(item.get(k, '')) for k in ('source', 'url')).lower()
    return 'malariasimulation' in text or 'openmalaria' in text


def source_rank(item):
    host = (urlsplit(item.get('url', '')).hostname or '').lower()
    if host == 'who.int' or host.endswith('.who.int') or item.get('source', '').startswith('WHO '):
        return 0
    if item.get('category') in ('snt', 'campaigns'):
        return 1
    if 'malvax' in item.get('source', '').lower() or host == 'www.malvax.org':
        return 3
    return 2


def item_kind(item, today):
    if excluded(item):
        return None
    title = str(item.get('title', '')).strip()
    if not title or not str(item.get('url', '')).startswith('https://'):
        return None
    if title.lower().startswith(('skip to', 'learn more', 'view all', 'access the', 'visit the page')):
        return None
    if item.get('event_date'):
        event = parse_date(item['event_date'])
        return 'event' if event and today <= event <= today + dt.timedelta(days=EVENT_HORIZON_DAYS) else None
    publication = parse_date(item.get('published_date'))
    if publication:
        age = (today - publication).days
        if 0 <= age <= PROMINENT_DAYS:
            return 'last_7_days'
        if PROMINENT_DAYS < age <= LOOKBACK_DAYS:
            return 'last_30_days'
    # first_seen is not a publication date. Undated leads stay in the archive.
    return None


def select_items(items, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    groups = {'last_7_days': [], 'last_30_days': [], 'event': []}
    for item in items:
        kind = item_kind(item, today)
        if kind:
            groups[kind].append(item)
    # WER reports can also appear in WHO topic listings. Prefer the original
    # issue article over a duplicate landing-page record, keeping the archive.
    for kind, candidates in groups.items():
        unique={}
        for item in candidates:
            key=(item.get('url'),)
            if source_rank(item)==0:
                key=('who',tuple(re.findall(r'\w+',item['title'].casefold())),item.get('published_date'),item.get('event_date'))
            if key not in unique or item.get('method')=='who_wer':unique[key]=item
        groups[kind]=list(unique.values())
    for kind in ('last_7_days', 'last_30_days'):
        groups[kind].sort(key=lambda i: (source_rank(i), -parse_date(i['published_date']).toordinal(), i['title']))
    groups['event'].sort(key=lambda i: (parse_date(i['event_date']), source_rank(i), i['title']))
    return groups
