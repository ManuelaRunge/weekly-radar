"""Conservative RIDA Radar collection: discovered links are leads, NOT verified news."""
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
from selection import LOOKBACK_DAYS, excluded, parse_date
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
import requests
import feedparser
from bs4 import BeautifulSoup

ROOT=pathlib.Path(__file__).resolve().parents[1]
TODAY=dt.datetime.now(dt.timezone.utc).date().isoformat()
HEADERS={"User-Agent":"RIDARadar/0.1 (personal research news monitor; no scraping authentication)"}

def clean_url(url):
    parts=urlsplit(url)
    query=urlencode([(k,v) for k,v in parse_qsl(parts.query) if not k.lower().startswith('utm_')])
    # WER is a multi-article issue: article anchors identify distinct resources.
    host=(parts.hostname or '').lower()
    fragment=parts.fragment if host=='www.who.int' and re.fullmatch(r'/publications/journals/weekly-epidemiological-record/wer[\d-]+/?',parts.path) else ''
    return urlunsplit((parts.scheme,parts.netloc,parts.path,query,fragment))

def record(title,url,source,category,method,**kw):
    url=clean_url(url)
    if re.search(r'\bSNT\b|subnational[ -]tailoring', title, re.I):category='snt'
    return dict(id=hashlib.sha256(url.encode()).hexdigest()[:16],title=title.strip()[:220],url=url,source=source,category=category,method=method,first_seen=TODAY,published_date=kw.get('published_date',''),event_date=kw.get('event_date',''),notes=kw.get('notes',''),verification='unverified',editorial_status='inbox')

def date_from_text(text):
    text=str(text).strip()
    iso=re.search(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)',text)
    if iso and parse_date(iso.group()):return iso.group()
    match=re.search(r'\b\d{1,2} [A-Za-z]+ \d{4}\b',text)
    if match:
        for fmt in ('%d %B %Y','%d %b %Y'):
            try:return dt.datetime.strptime(match.group(),fmt).date().isoformat()
            except ValueError:pass
    return ''


def url_dates(link):
    # WHO news URLs explicitly encode the publication date (not event dates).
    if (urlsplit(link).hostname or '').endswith('who.int'):
        match=re.search(r'/news/(?:item|detail)/(\d{2})-(\d{2})-(\d{4})-',link)
        if match:
            date=f'{match[3]}-{match[2]}-{match[1]}'
            if parse_date(date):return {'published_date':date}
        match=re.search(r'/events/detail/(\d{4})/(\d{2})/(\d{2})/',link)
        if match:
            date='-'.join(match.groups())
            if parse_date(date):return {'event_date':date}
    return {}


def page_dates(anchor, link):
    dates=url_dates(link)
    if dates:return dates
    # Use explicit card metadata only, never arbitrary dates in link titles.
    for card in (anchor,anchor.parent,anchor.parent.parent if anchor.parent else None):
        if card is None:continue
        nodes=card.select('time, .timestamp, .sf-publications-item__date, .sf-list-vertical__date')
        if len(nodes)==1:
            node=nodes[0]
            date=date_from_text(node.get('datetime') or node.get_text(' ',strip=True))
            if date:return {'event_date' if '/events/' in link else 'published_date':date}
    return {}


def collect_outbreaks(s):
    response=requests.get('https://www.who.int/api/emergencies/diseaseoutbreaknews',
        params={'sf_provider':'dynamicProvider372','sf_culture':'en','$top':100,
                '$orderby':'PublicationDateAndTime desc',
                '$select':'Title,TitleSuffix,OverrideTitle,UseOverrideTitle,ItemDefaultUrl,PublicationDateAndTime'},
        headers=HEADERS,timeout=40)
    response.raise_for_status()
    results=[]
    for entry in response.json()['value']:
        title=(entry.get('OverrideTitle') if entry.get('UseOverrideTitle') else '') or entry['Title']
        if entry.get('TitleSuffix'):title+=' — '+entry['TitleSuffix']
        link=s['url'].rstrip('/')+'/item/'+entry['ItemDefaultUrl'].lstrip('/')
        results.append(record(title,link,s['name'],s['category'],'who_outbreaks',
            published_date=date_from_text(entry.get('PublicationDateAndTime','')),
            notes='Publication date from WHO outbreak listing; claims require review.'))
    return results


def wer_issue_links(soup, base_url):
    links=[]
    for anchor in soup.select('a[href]'):
        link=urljoin(base_url,anchor['href'])
        parts=urlsplit(link)
        if parts.hostname=='www.who.int' and re.fullmatch(r'/publications/journals/weekly-epidemiological-record/wer[\d-]+/?',parts.path):
            link=urlunsplit((parts.scheme,parts.netloc,parts.path.rstrip('/'),'',''))
            if link not in links:links.append(link)
    return links


def parse_wer_issue(soup, issue_url, source):
    date_node=soup.select_one('.wer-panel-issue-meta')
    publication=date_from_text(date_node.get_text(' ',strip=True)) if date_node else ''
    if not publication:raise ValueError(f'WER issue has no explicit publication date: {issue_url}')
    age=(dt.date.fromisoformat(TODAY)-dt.date.fromisoformat(publication)).days
    if not 0 <= age <= LOOKBACK_DAYS:return []
    results=[]
    for heading in soup.select('.wer-block h2'):
        title=heading.get_text(' ',strip=True)
        if not title:continue
        anchor=heading.get('id')
        if not anchor:
            marker=heading.find_previous_sibling(class_='wer-anchor')
            anchor=marker.get('id') if marker else None
        if not anchor:continue
        results.append(record(title,issue_url+'#'+anchor,source['name'],source['category'],'who_wer',
            published_date=publication,notes='Original WER HTML article; publication date from issue metadata. Claims require review.'))
    if not results:raise ValueError(f'WER issue has no article headings: {issue_url}')
    return results


def collect_wer(source):
    response=requests.get(source['url'],headers=HEADERS,timeout=20)
    response.raise_for_status()
    pending=wer_issue_links(BeautifulSoup(response.text,'html.parser'),source['url'])
    if not pending:raise ValueError('WER listing returned no HTML issue links')
    seen=set()
    results=[]
    while pending and len(seen)<source.get('issue_limit',6):
        link=pending.pop(0)
        if link in seen:continue
        seen.add(link)
        response=requests.get(link,headers=HEADERS,timeout=20)
        response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        articles=parse_wer_issue(soup,link,source)
        results.extend(articles)
        # Recent issue pages expose older editions absent from the landing page.
        if articles:
            pending.extend(url for url in wer_issue_links(soup,link) if url not in seen and url not in pending)
    return results


def collect_headlines(source):
    results={}
    cutoff=dt.date.fromisoformat(TODAY)-dt.timedelta(days=LOOKBACK_DAYS)
    for page in range(1,source.get('max_pages',5)+1):
        url=source['url'].rstrip('/')+(f'/{page}' if page>1 else '')
        candidates=collect_source(dict(source,method='page',url=url))
        news=[i for i in candidates if '/news/item/' in urlsplit(i['url']).path and parse_date(i['published_date'])]
        if not news:raise ValueError(f'WHO headlines page returned no dated news: {url}')
        results.update((i['id'],i) for i in news)
        if min(dt.date.fromisoformat(i['published_date']) for i in news)<=cutoff:break
    return list(results.values())


def collect_source(s):
    if s['method']=='who_outbreaks':return collect_outbreaks(s)
    if s['method']=='who_wer':return collect_wer(s)
    if s['method']=='who_headlines':return collect_headlines(s)
    r=requests.get(s['url'],headers=HEADERS,timeout=20)
    r.raise_for_status()
    results=[]
    if s['method']=='feed':
        parsed=feedparser.parse(r.content)
        if not parsed.entries:raise ValueError('Feed returned no entries; check source URL or format')
        for entry in parsed.entries[:s.get('limit',100)]:
            date=entry.get('published','') or entry.get('updated','')
            parsed_date=entry.get('published_parsed')
            publication=dt.date(*parsed_date[:3]).isoformat() if parsed_date else ''
            link=entry.get('link',s['url'])
            # WHO's feed can reissue old news with a new feed timestamp. Prefer
            # the original publication date encoded in the canonical news URL.
            publication=url_dates(link).get('published_date') or publication
            results.append(record(entry.get('title','Untitled'),link,s['name'],s['category'],'feed',published_date=publication,notes=f'Source feed date: {date}; original WHO URL date takes precedence when present; claims require review.'))
    else:
        soup=BeautifulSoup(r.text,'html.parser')
        for node in soup(['script','style','nav','footer','header']): node.decompose()
        # Collect discovery candidates with dates only where explicitly provided.
        seen=set()
        container=soup.find('main') or soup
        for a in container.select('a[href]'):
            title=a.get('aria-label') or a.get_text(' ',strip=True)
            link=clean_url(urljoin(s['url'],a.get('href','')))
            if not (12 <= len(title) <= 180) or not link.startswith('https://') or link in seen: continue
            if title.lower().startswith(('skip to','learn more','view all','read more')):continue
            if any(x in link.lower() for x in ['mailto:','/privacy','/contact','/terms','javascript:']):continue
            seen.add(link)
            results.append(record(title,link,s['name'],s['category'],'page',**page_dates(a,link)))
            if len(results)>=s.get('limit',100):break
    return results

def run():
    previous=ROOT/'data'/'items.json'
    existing={x['id']:x for x in json.loads(previous.read_text(encoding='utf-8'))} if previous.exists() else {}
    errors=[]
    for source in json.loads((ROOT/'config'/'sources.json').read_text(encoding='utf-8')):
        try:
            for item in collect_source(source):
                if excluded(item):continue
                if item['id'] not in existing:existing[item['id']]=item
                elif existing[item['id']].get('method')!='manual':
                    # Refresh source metadata while retaining first_seen and review state.
                    for field in ('title','source','category','method','published_date','event_date','notes'):
                        if item[field]:existing[item['id']][field]=item[field]
        except Exception as exc:
            errors.append({'source':source['name'],'error':str(exc)[:250]})
    with (ROOT/'config'/'manual_links.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            item=record(row['title'],row['url'],row['source'],row['category'],'manual',published_date=row['published_date'],event_date=row['event_date'],notes=row['notes'])
            if item['id'] not in existing:
                existing[item['id']]=item
            else:
                # Manual metadata takes precedence over a discovered link, while
                # preserving its first-seen date and any editorial review state.
                for field in ('title','source','category','method','published_date','event_date','notes'):
                    if item[field]:existing[item['id']][field]=item[field]
    (ROOT/'data').mkdir(exist_ok=True)
    previous.write_text(json.dumps(sorted(existing.values(),key=lambda x:x['first_seen'],reverse=True),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (ROOT/'data'/'errors.json').write_text(json.dumps(errors,indent=2)+'\n',encoding='utf-8')
    print(f'{len(existing)} total candidates; {len(errors)} source errors')
if __name__=='__main__':run()
