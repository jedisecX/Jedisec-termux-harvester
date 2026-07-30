import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "la_downloads")  # kept name for continuity with earlier runs
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "harvester.db")

MAX_PAGES = 18
MAX_CONSECUTIVE_EMPTY = 3       # stop paging a query after this many empty pages in a row
RESOLVE_WORKERS = 6             # concurrent HEAD/GET link-resolution workers per results page
                                 # (kept modest -- tune down further on a slow mobile connection)
MAX_CONCURRENT_DOWNLOADS = 3    # simultaneous file downloads

# Incremental mode: bail out of a query early once this many resolved
# candidates in a row turn out to already be known documents.
INCREMENTAL_KNOWN_STREAK = 5
