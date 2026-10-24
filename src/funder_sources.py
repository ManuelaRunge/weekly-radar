"""Public funder listing APIs used by the publishers' own news pages."""
import json
from urllib.parse import parse_qsl, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup


def keyword_match(text, groups):
    """Match at least one word stem from each configured topic group."""
    import re
    return all(any(re.search(r'\b'+re.escape(term),text,re.I) for term in group) for group in groups)


def plain(value):
    if isinstance(value,dict):value=value.get('cdata!','')
    return BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True)


def gates_news(source, headers, make_record, parse_date):
    response=requests.get(source['url'],headers=headers,timeout=30)
    response.raise_for_status()
    soup=BeautifulSoup(response.text,'html.parser')
    node=next((node for node in soup.select('[data-model][data-query]')
               if 'dynamiccontentlisting' in node['data-model']),None)
    if node is None:raise ValueError('Gates news listing configuration not found')
    endpoint=urljoin(source['url'],json.loads(node['data-model'])['url'])
    if urlsplit(endpoint).hostname!='www.gatesfoundation.org':raise ValueError('Unexpected Gates listing host')
    params=json.loads(node['data-query'])
    params.update(perPage=100,sortBy='date',sortOrder='desc')
    response=requests.get(endpoint,params=params,headers=headers,timeout=30)
    response.raise_for_status()
    entries=response.json()['results']
    if not entries:raise ValueError('Gates news listing returned no entries')
    return [make_record(plain(entry['title']),urljoin(source['url'],entry['contentUrl']),
                        source['name'],source['category'],'gates_news',
                        published_date=parse_date(entry.get('date','')),
                        notes=plain(entry.get('body',''))[:1000]) for entry in entries]


def worldbank_news(source, headers, make_record, parse_date):
    response=requests.get(source['url'],headers=headers,timeout=30)
    response.raise_for_status()
    soup=BeautifulSoup(response.text,'html.parser')
    node=next((node for node in soup.select('[data-url]')
               if 'search.worldbank.org/api/v2/news?' in node['data-url']),None)
    if node is None:raise ValueError('World Bank health-news API configuration not found')
    parts=urlsplit(node['data-url'])
    if parts.hostname!='search.worldbank.org':raise ValueError('Unexpected World Bank listing host')
    params=dict(parse_qsl(parts.query))
    params.update(format='json',rows=100,srt='lnchdt',order='desc')
    response=requests.get('https://search.worldbank.org'+parts.path,params=params,headers=headers,timeout=30)
    response.raise_for_status()
    documents=response.json()['documents']
    if not documents:raise ValueError('World Bank health-news API returned no entries')
    results=[]
    for entry in documents.values():
        url=entry.get('url','')
        if url.startswith('http://www.worldbank.org/'):url='https://'+url[len('http://'):]
        # Preserve the explicitly supplied launch date, never first_seen.
        results.append(make_record(plain(entry.get('title')),url,source['name'],source['category'],
            'worldbank_news',published_date=parse_date(entry.get('lnchdt','')),
            notes=plain(entry.get('content_1000'))[:1000]))
    return results
