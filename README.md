# JediSec Multi-State PDF Harvester (Plugin Edition)

## Layout
```
config.py           global settings (paths, concurrency, page limits)
headers.py          rotating User-Agent / Accept-Language / Referer pool
resolver.py         link de-obfuscation: navigates raw search hrefs, keys
                     off the final redirect-resolved URL
fingerprint.py       SHA-256 helpers (streamed during download)
downloader.py        threaded downloader: fingerprinting, magic-byte check,
                     per-host folders, hands off to the OCR/index pipeline
harvest.py            ties engines + resolver + downloader together per query
db.py                SQLite: documents, dedup, entities, FTS5 search index,
                     agency run history
harvester.py          CLI: interactive multi-state menu, or headless via
                     --all / --state / --incremental
scheduler.py          thin wrapper for unattended incremental runs

engines/              search-backend PLUGINS (yahoo, duckduckgo, bing, google)
agencies/             state PLUGINS (louisiana, texas, mississippi)
processing/            extract_text.py, ocr.py, entities.py, index.py
webapp/               Flask dashboard + full-text search + document view
```

## Adding a search engine
Drop a new file in `engines/`, subclass `SearchEngine` from `engines/base.py`,
set a `name`, implement `search(session, headers, query, page) -> list[str]`.
It's auto-registered on next run -- nothing else to touch.

## Adding a state
Drop a new file in `agencies/`, define `RAW = {code: (name, query), ...}`
(same shape Louisiana uses) and `STATE = build_state("XX", "State Name", RAW)`.
Auto-registered on next run.

## Running it
```
python3 harvester.py                      # interactive matrix menu
python3 harvester.py --state LA           # sweep one state, no menu
python3 harvester.py --all                # sweep every state/agency
python3 harvester.py --incremental --all  # only fetch new-since-last-run docs
python3 scheduler.py --interval-hours 6   # loop forever (prefer cron/Termux:Boot instead)
python3 webapp/app.py                     # dashboard + search at :5000
```

## Runs numpy-free, built for Termux
Nothing in this stack requires numpy or a compiled ML dependency:
- **Search + download**: requests, beautifulsoup4 (`html.parser`, no lxml), tqdm -- all pure Python.
- **Text extraction**: `pypdf` -- pure Python, no C extensions. (Deliberately not pdfplumber:
  it pulls in pypdfium2, a compiled binary with no reliable Android/aarch64 wheel.)
- **Entity extraction**: `processing/entities.py` is a pure-Python, stdlib-`re`-only
  gazetteer/regex tagger. No spaCy, no numpy/thinc/blis. spaCy's dependency chain is the
  part of a "smart" pipeline that actually breaks on Termux -- there's no Android wheel for
  numpy/thinc/blis, so pip tries to compile from source against toolchains Termux doesn't
  ship. This tagger trades some precision for installing instantly everywhere.
- **OCR (optional)**: pdf2image + pytesseract are themselves pure-Python subprocess wrappers,
  but they shell out to real Poppler/Tesseract binaries and pull in Pillow (which does have
  C extensions).

### Termux setup
```
pkg update && pkg install python tesseract poppler python-pillow
pip install --break-system-packages requests beautifulsoup4 tqdm flask pypdf pdf2image pytesseract
```
Use `pkg install python-pillow` rather than `pip install pillow` -- Termux ships a
precompiled Pillow built against its own libjpeg/zlib, so pip would otherwise try (and
likely fail) to build it from source.

If you want the harvester to write into shared/external storage instead of Termux's
private app storage, run `termux-setup-storage` once first.

`config.py` keeps `RESOLVE_WORKERS` and `MAX_CONCURRENT_DOWNLOADS` modest (6 and 3) by
default with mobile data/battery in mind -- tune both down further if you're on a slow
or metered connection.

## What "incremental" actually means here
None of the search engines expose reliable publish dates, so true
"only newly published documents" isn't something we can ask for directly.
The honest approximation: every document is fingerprinted (SHA-256) and
its URL recorded, so a normal re-run already never re-downloads anything.
`--incremental` goes further and bails out of a query early once it hits
several already-known documents in a row, on the assumption you've paged
back into old territory -- saving the search-engine requests, not just
the download.
