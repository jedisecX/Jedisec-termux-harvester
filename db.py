import sqlite3
import threading
import time
import config

DB_LOCK = threading.Lock()
_CONN = sqlite3.connect(config.DB_PATH, check_same_thread=False)
_CONN.row_factory = sqlite3.Row
FTS5_AVAILABLE = True


def _init():
    global FTS5_AVAILABLE
    with DB_LOCK:
        _CONN.execute("""CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            sha256 TEXT UNIQUE,
            state TEXT,
            agency_code TEXT,
            agency_name TEXT,
            engine TEXT,
            host TEXT,
            filepath TEXT,
            filesize INTEGER,
            downloaded_at TEXT,
            ocr_used INTEGER DEFAULT 0,
            text_extracted INTEGER DEFAULT 0
        )""")
        _CONN.execute("""CREATE TABLE IF NOT EXISTS duplicate_urls (
            url TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL,
            canonical_document_id INTEGER NOT NULL,
            discovered_at TEXT
        )""")
        _CONN.execute("""CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            entity_text TEXT NOT NULL,
            entity_type TEXT NOT NULL
        )""")
        _CONN.execute("CREATE INDEX IF NOT EXISTS idx_entities_text ON entities(entity_text)")
        _CONN.execute("CREATE INDEX IF NOT EXISTS idx_entities_doc ON entities(document_id)")
        _CONN.execute("""CREATE TABLE IF NOT EXISTS agency_runs (
            state TEXT NOT NULL,
            agency_code TEXT NOT NULL,
            agency_name TEXT,
            last_run_at TEXT,
            docs_found INTEGER DEFAULT 0,
            docs_new INTEGER DEFAULT 0,
            PRIMARY KEY (state, agency_code)
        )""")
        try:
            _CONN.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
                              USING fts5(document_id UNINDEXED, title, content, tokenize='porter')""")
        except sqlite3.OperationalError:
            FTS5_AVAILABLE = False
            _CONN.execute("""CREATE TABLE IF NOT EXISTS documents_fts_fallback (
                document_id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT
            )""")
        _CONN.commit()


_init()

# ------------------------------------------------------------------
# documents / fingerprinting
# ------------------------------------------------------------------

def fingerprint_exists(sha256):
    """Returns the existing document id if this SHA-256 has already been
    saved (regardless of what URL it came from), else None."""
    with DB_LOCK:
        row = _CONN.execute("SELECT id FROM documents WHERE sha256 = ?", (sha256,)).fetchone()
    return row["id"] if row else None


def url_known(url):
    """True if this exact URL has already been downloaded OR already
    resolved to a duplicate of something we have."""
    with DB_LOCK:
        row = _CONN.execute("SELECT 1 FROM documents WHERE url = ?", (url,)).fetchone()
        if row:
            return True
        row = _CONN.execute("SELECT 1 FROM duplicate_urls WHERE url = ?", (url,)).fetchone()
        return row is not None


def insert_document(url, sha256, state, agency_code, agency_name, engine, host, filepath, filesize):
    with DB_LOCK:
        cur = _CONN.execute("""
            INSERT INTO documents (url, sha256, state, agency_code, agency_name, engine, host,
                                    filepath, filesize, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (url, sha256, state, agency_code, agency_name, engine, host, filepath, filesize,
              time.strftime('%Y-%m-%d %H:%M:%S')))
        _CONN.commit()
        return cur.lastrowid


def insert_duplicate(url, sha256, canonical_document_id):
    with DB_LOCK:
        _CONN.execute("""
            INSERT OR IGNORE INTO duplicate_urls (url, sha256, canonical_document_id, discovered_at)
            VALUES (?, ?, ?, ?)
        """, (url, sha256, canonical_document_id, time.strftime('%Y-%m-%d %H:%M:%S')))
        _CONN.commit()


def mark_processed(document_id, ocr_used, text_extracted):
    with DB_LOCK:
        _CONN.execute("UPDATE documents SET ocr_used = ?, text_extracted = ? WHERE id = ?",
                       (int(ocr_used), int(text_extracted), document_id))
        _CONN.commit()


def get_document(document_id):
    with DB_LOCK:
        row = _CONN.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    return dict(row) if row else None

# ------------------------------------------------------------------
# entities / relationships
# ------------------------------------------------------------------

def insert_entities(document_id, ents):
    if not ents:
        return
    with DB_LOCK:
        _CONN.executemany(
            "INSERT INTO entities (document_id, entity_text, entity_type) VALUES (?, ?, ?)",
            [(document_id, text, etype) for text, etype in ents]
        )
        _CONN.commit()


def entities_for_document(document_id):
    with DB_LOCK:
        rows = _CONN.execute(
            "SELECT entity_text, entity_type FROM entities WHERE document_id = ? "
            "ORDER BY entity_type, entity_text", (document_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def related_by_entities(document_id, limit=10):
    """Documents connected to this one by shared named entities, ranked
    by how many entities they have in common."""
    with DB_LOCK:
        rows = _CONN.execute("""
            SELECT e2.document_id AS document_id, COUNT(*) AS overlap
            FROM entities e1
            JOIN entities e2 ON e1.entity_text = e2.entity_text AND e1.document_id != e2.document_id
            WHERE e1.document_id = ?
            GROUP BY e2.document_id
            ORDER BY overlap DESC
            LIMIT ?
        """, (document_id, limit)).fetchall()
    results = []
    for row in rows:
        doc = get_document(row["document_id"])
        if doc:
            results.append({"document": doc, "shared_entities": row["overlap"]})
    return results

# ------------------------------------------------------------------
# full-text index / search
# ------------------------------------------------------------------

def index_fts(document_id, title, content):
    with DB_LOCK:
        if FTS5_AVAILABLE:
            _CONN.execute("DELETE FROM documents_fts WHERE document_id = ?", (document_id,))
            _CONN.execute("INSERT INTO documents_fts (document_id, title, content) VALUES (?, ?, ?)",
                          (document_id, title, content))
        else:
            _CONN.execute("""
                INSERT INTO documents_fts_fallback (document_id, title, content) VALUES (?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET title = excluded.title, content = excluded.content
            """, (document_id, title, content))
        _CONN.commit()


def search_fts(query, limit=50):
    with DB_LOCK:
        if FTS5_AVAILABLE:
            rows = _CONN.execute("""
                SELECT document_id, title, snippet(documents_fts, 2, '[', ']', '...', 12) AS snippet
                FROM documents_fts WHERE documents_fts MATCH ? LIMIT ?
            """, (query, limit)).fetchall()
        else:
            like = f"%{query}%"
            rows = _CONN.execute("""
                SELECT document_id, title, substr(content, 1, 200) AS snippet
                FROM documents_fts_fallback WHERE content LIKE ? OR title LIKE ? LIMIT ?
            """, (like, like, limit)).fetchall()
    results = []
    for row in rows:
        doc = get_document(row["document_id"])
        if doc:
            results.append({"document": doc, "title": row["title"], "snippet": row["snippet"]})
    return results

# ------------------------------------------------------------------
# agency run tracking (drives incremental scheduling)
# ------------------------------------------------------------------

def get_last_run(state, agency_code):
    with DB_LOCK:
        row = _CONN.execute(
            "SELECT last_run_at FROM agency_runs WHERE state = ? AND agency_code = ?",
            (state, agency_code)
        ).fetchone()
    return row["last_run_at"] if row else None


def record_agency_run(state, agency_code, agency_name, docs_found, docs_new):
    with DB_LOCK:
        _CONN.execute("""
            INSERT INTO agency_runs (state, agency_code, agency_name, last_run_at, docs_found, docs_new)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(state, agency_code) DO UPDATE SET
                last_run_at = excluded.last_run_at,
                docs_found = excluded.docs_found,
                docs_new = excluded.docs_new,
                agency_name = excluded.agency_name
        """, (state, agency_code, agency_name, time.strftime('%Y-%m-%d %H:%M:%S'), docs_found, docs_new))
        _CONN.commit()

# ------------------------------------------------------------------
# dashboard stats
# ------------------------------------------------------------------

def stats():
    with DB_LOCK:
        total_docs = _CONN.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
        total_dupes = _CONN.execute("SELECT COUNT(*) c FROM duplicate_urls").fetchone()["c"]
        total_entities = _CONN.execute("SELECT COUNT(*) c FROM entities").fetchone()["c"]
        ocr_docs = _CONN.execute("SELECT COUNT(*) c FROM documents WHERE ocr_used = 1").fetchone()["c"]
        by_state = _CONN.execute("""
            SELECT state, COUNT(*) c, SUM(filesize) bytes FROM documents GROUP BY state ORDER BY c DESC
        """).fetchall()
        recent_runs = _CONN.execute("""
            SELECT state, agency_code, agency_name, last_run_at, docs_found, docs_new
            FROM agency_runs ORDER BY last_run_at DESC LIMIT 15
        """).fetchall()
    return {
        "total_documents": total_docs,
        "total_duplicate_content_skipped": total_dupes,
        "total_entities": total_entities,
        "ocr_documents": ocr_docs,
        "by_state": [dict(r) for r in by_state],
        "recent_runs": [dict(r) for r in recent_runs],
    }
