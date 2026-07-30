from urllib.parse import unquote
from bs4 import BeautifulSoup
from .base import SearchEngine


class GoogleEngine(SearchEngine):
    name = "google"

    def search(self, session, headers, query, page):
        params = {'q': query, 'start': page * 10, 'num': 10}
        r = session.get('https://www.google.com/search', params=params, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        urls = []
        for a in soup.find_all('a', href=True):
            h = a['href']
            if h.startswith('/url?q='):
                urls.append(unquote(h.split('/url?q=')[1].split('&')[0]))
            elif h.startswith('http'):
                urls.append(h)
        return urls
