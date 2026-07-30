from urllib.parse import unquote, urlparse, parse_qs
from bs4 import BeautifulSoup
from .base import SearchEngine


def _extract_ddg_url(href):
    """DuckDuckGo's HTML endpoint wraps outbound links in /l/?uddg=<encoded>."""
    if 'uddg=' in href:
        qs = parse_qs(urlparse(href).query)
        if 'uddg' in qs:
            return unquote(qs['uddg'][0])
    return href


class DuckDuckGoEngine(SearchEngine):
    name = "duckduckgo"

    def search(self, session, headers, query, page):
        data = {'q': query, 's': page * 30, 'kl': 'us-en'}
        r = session.post('https://html.duckduckgo.com/html/', data=data, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        urls = []
        for a in soup.find_all('a', class_='result__a', href=True):
            urls.append(_extract_ddg_url(a['href']))
        return urls
