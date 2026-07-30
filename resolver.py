from urllib.parse import urlparse
import requests

# Hosts that are the search engine's own UI/nav/ad chrome, not results.
# Filtered out before we bother navigating to anything.
SEARCH_ENGINE_DOMAINS = ('yahoo.com', 'bing.com', 'duckduckgo.com', 'google.com', 'msn.com', 'microsoft.com')

def resolve_pdf_url(session, headers, url):
    """Navigate to a raw search-result href and return the final,
    redirect-resolved URL if (and only if) it actually is a PDF.

    This is the de-obfuscation step: every search engine wraps outbound
    links in some kind of tracking/redirect param (Yahoo's /RU=.../RK=,
    Google's /url?q=, DuckDuckGo's uddg=, Bing's click-trackers).
    Regex-unwrapping those params gets you *a* URL, but frequently still
    a redirect rather than the document itself -- which pools duplicate
    or broken entries under what look like distinct links. Resolving by
    actually requesting the URL and keying off the final response.url
    fixes both problems at once.
    """
    try:
        netloc = urlparse(url).netloc.lower()
        if not netloc or any(d in netloc for d in SEARCH_ENGINE_DOMAINS):
            return None

        r = None
        try:
            r = session.head(url, headers=headers, timeout=12, allow_redirects=True)
            if r.status_code >= 400 or (
                'content-length' not in r.headers and 'content-type' not in r.headers
            ):
                r = None
        except requests.RequestException:
            r = None

        if r is None:
            r = session.get(url, headers=headers, timeout=15, allow_redirects=True, stream=True)
            r.close()

        final_url = r.url
        ctype = r.headers.get('content-type', '').lower()
        if final_url.lower().split('?')[0].endswith('.pdf') or 'pdf' in ctype:
            return final_url
    except Exception:
        pass
    return None
