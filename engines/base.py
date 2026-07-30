class SearchEngine:
    """Plugin interface. Subclass this, set `name`, implement `search`.

    engines/__init__.py auto-discovers every module dropped in this
    package and registers any SearchEngine subclass it finds -- adding a
    new search backend is just adding a new file here, nothing else to
    wire up.
    """
    name = "base"  # override with a short slug (used in rotation / CLI selection)

    def search(self, session, headers, query, page):
        """Return a raw list of hrefs scraped off one results page.
        Not expected to be de-obfuscated/final -- resolver.py handles
        following redirects and unwrapping tracking params."""
        raise NotImplementedError
