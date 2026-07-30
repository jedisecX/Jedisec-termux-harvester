import re
from urllib.parse import unquote
from bs4 import BeautifulSoup
from .base import SearchEngine


class YahooEngine(SearchEngine):
    name = "yahoo"

    def search(self, session, headers, query, page):
        params = {'p': query, 'b': page * 10 + 1}
        r = session.get('https://search.yahoo.com/search', params=params, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        urls = []
        for a in soup.find_all('a', href=True):
            h = a['href']
            if '/RU=' in h:
                m = re.search(r'/RU=(.*?)/RK=', h)
                if m:
                    urls.append(unquote(m.group(1)))
            elif h.startswith('http'):
                urls.append(h)
        return urls
