from bs4 import BeautifulSoup
from .base import SearchEngine


class BingEngine(SearchEngine):
    name = "bing"

    def search(self, session, headers, query, page):
        params = {'q': query, 'first': page * 10 + 1}
        r = session.get('https://www.bing.com/search', params=params, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        urls = []
        for li in soup.find_all('li', class_='b_algo'):
            a = li.find('a', href=True)
            if a:
                urls.append(a['href'])
        return urls
