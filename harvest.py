import csv
import time
import itertools
import threading
import queue as queue_mod
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

import config
import headers as headers_mod
import db
import engines
import resolver
import downloader
from downloader import DownloadThread


def get_pdf_links(query, name, enabled_engines=None, incremental=False):
    """Pull PDF links for a query, rotating across all enabled search
    engines page-by-page. Every raw result href is resolved by actually
    navigating to it (resolver.resolve_pdf_url), so obfuscated/tracking
    wrapper links collapse to their real, de-duplicated destination.

    In incremental mode, also bails out early once a run of resolved
    candidates in a row turn out to already be known documents --
    the practical stand-in for "only fetch newly published documents"
    given that these search engines don't expose reliable publish dates.
    """
    pdfs = {}  # resolved_url -> engine that found it
    s = requests.Session()
    consecutive_empty = 0
    consecutive_known = 0
    names = enabled_engines or engines.available_engines()
    engine_cycle = itertools.cycle(names)

    for p in range(config.MAX_PAGES):
        engine_name = next(engine_cycle)
        engine = engines.get_engine(engine_name)
        before = len(pdfs)

        try:
            raw_urls = engine.search(s, headers_mod.random_headers(), query, p)
        except Exception:
            raw_urls = []

        candidates = []
        seen_page = set()
        for u in raw_urls:
            if not u or not u.startswith('http'):
                continue
            if u in seen_page or u in pdfs:
                continue
            netloc = urlparse(u).netloc.lower()
            if any(d in netloc for d in resolver.SEARCH_ENGINE_DOMAINS):
                continue
            seen_page.add(u)
            candidates.append(u)

        page_known = 0
        if candidates:
            headers = headers_mod.random_headers()
            with ThreadPoolExecutor(max_workers=config.RESOLVE_WORKERS) as ex:
                futures = {ex.submit(resolver.resolve_pdf_url, s, headers, u): u for u in candidates}
                for fut in as_completed(futures):
                    resolved = fut.result()
                    if not resolved or resolved in pdfs:
                        continue
                    if incremental and db.url_known(resolved):
                        page_known += 1
                        continue
                    pdfs[resolved] = engine_name

        gained = len(pdfs) - before
        consecutive_empty = 0 if gained else consecutive_empty + 1
        consecutive_known = (consecutive_known + 1) if (incremental and page_known and not gained) else 0

        status = f"+{gained}" if gained else "empty"
        known_part = (f", {consecutive_known}/{config.INCREMENTAL_KNOWN_STREAK} known streak"
                      if incremental else "")
        print(f"  \033[93m[{name[:22]:22}] {engine_name:11} page {p+1:2} \u2192 {len(pdfs):4} PDFs "
              f"({status}, {consecutive_empty}/{config.MAX_CONSECUTIVE_EMPTY} empty streak{known_part})\033[0m")

        if consecutive_empty >= config.MAX_CONSECUTIVE_EMPTY:
            print(f"  \033[91m[{name[:22]:22}] {config.MAX_CONSECUTIVE_EMPTY} consecutive empty pages "
                  f"\u2014 moving to next agency.\033[0m")
            break
        if incremental and consecutive_known >= config.INCREMENTAL_KNOWN_STREAK:
            print(f"  \033[91m[{name[:22]:22}] hit {config.INCREMENTAL_KNOWN_STREAK} consecutive "
                  f"already-known documents \u2014 assuming we've caught up, moving to next agency.\033[0m")
            break

        time.sleep(2)

    return pdfs


def launch_downloads(pdfs, state_code, agency_code, agency_name):
    """pdfs: dict of resolved_url -> engine name (from get_pdf_links).
    Runs up to config.MAX_CONCURRENT_DOWNLOADS downloads at once, each
    with its own tqdm progress bar."""
    downloader.downloaded_count = 0
    downloader.failed_count = 0
    downloader.duplicate_content_count = 0

    position_pool = queue_mod.Queue()
    for i in range(config.MAX_CONCURRENT_DOWNLOADS):
        position_pool.put(i)

    csv_name = f"la_downloads_{state_code}_{agency_name.replace(' ', '_').replace('/', '_')}.csv"
    with open(csv_name, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['URL', 'Filename', 'Engine', 'Status'])
        sem = threading.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        threads = []
        for url, engine in pdfs.items():
            if db.url_known(url):
                w.writerow([url, '', engine, 'skipped_duplicate'])
                continue
            fn = url.rsplit('/', 1)[-1].split('?')[0] or f"doc_{abs(hash(url))}.pdf"
            w.writerow([url, fn, engine, 'queued'])
            t = DownloadThread(url, fn, sem, state_code, agency_code, agency_name, engine, position_pool)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    print(f"\n\033[92m{agency_name} complete \u2192 {downloader.downloaded_count} saved | "
          f"{downloader.failed_count} failed | "
          f"{downloader.duplicate_content_count} duplicate-content skipped\033[0m\n")

    db.record_agency_run(state_code, agency_code, agency_name,
                          docs_found=len(pdfs), docs_new=downloader.downloaded_count)
