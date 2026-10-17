"""Conservative RIDA Radar collection: discovered links are leads, NOT verified news."""
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
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
    return urlunsplit((parts.scheme,parts.netloc,parts.path,query,''))

def record(title,url,source,category,method,**kw):
    url=clean_url(url)
    return dict(id=hashlib.sha256(url.encode()).hexdigest()[:16],title=title.strip()[:220],url=url,source=source,category=category,method=method,first_seen=TODAY,published_date=kw.get('published_date',''),event_date=kw.get('event_date',''),notes=kw.get('notes',''),verification='unverified',editorial_status='inbox')

def collect_source(s):
    r=requests.get(s['url'],headers=HEADERS,timeout=20)
    r.raise_for_status()
    results=[]
    if s['method']=='feed':
        parsed=feedparser.parse(r.content)
        for entry in parsed.entries[:30]:
            date=entry.get('published','') or entry.get('updated','')
            results.append(record(entry.get('title','Untitled'),entry.get('link',s['url']),s['name'],s['category'],'feed',notes=f'Feed date (unverified): {date}'))
    else:
        soup=BeautifulSoup(r.text,'html.parser')
        for node in soup(['script','style','nav','footer','header']): node.decompose()
        # Collect links as discovery candidates. Never infer publication dates from link text.
        seen=set()
        for a in soup.select('main a[href], article a[href], a[href]'):
            title=a.get_text(' ',strip=True)
            link=clean_url(urljoin(s['url'],a.get('href','')))
            if not (12 <= len(title) <= 180) or not link.startswith('https://') or link in seen: continue
            if any(x in link.lower() for x in ['mailto:','/privacy','/contact','/terms','javascript:']):continue
            seen.add(link)
            results.append(record(title,link,s['name'],s['category'],'page'))
            if len(results)>=50:break
    return results

def run():
    previous=ROOT/'data'/'items.json'
    existing={x['id']:x for x in json.loads(previous.read_text())} if previous.exists() else {}
    errors=[]
    for source in json.loads((ROOT/'config'/'sources.json').read_text()):
        try:
            for item in collect_source(source):
                if item['id'] not in existing:existing[item['id']]=item
        except Exception as exc:
            errors.append({'source':source['name'],'error':str(exc)[:250]})
    with (ROOT/'config'/'manual_links.csv').open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            item=record(row['title'],row['url'],row['source'],row['category'],'manual',published_date=row['published_date'],event_date=row['event_date'],notes=row['notes'])
            if item['id'] not in existing:existing[item['id']]=item
    (ROOT/'data').mkdir(exist_ok=True)
    previous.write_text(json.dumps(sorted(existing.values(),key=lambda x:x['first_seen'],reverse=True),indent=2,ensure_ascii=False)+'\n')
    (ROOT/'data'/'errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    print(f'{len(existing)} total candidates; {len(errors)} source errors')
if __name__=='__main__':run()
