import os
import re
import time
import threading
import requests
from urllib.parse import urlparse
from tqdm import tqdm

import config
import headers as headers_mod
import db
from fingerprint import StreamingSHA256
from processing.extract_text import extract_text
from processing.ocr import ocr_pdf
from processing.entities import extract_entities
from processing.index import index_document

lock = threading.Lock()
downloaded_count = failed_count = duplicate_content_count = 0


def sanitize_folder_name(netloc):
    """Turn a URL's netloc into a filesystem-safe folder name."""
    n = (netloc or 'unknown_host').lower()
    if n.startswith('www.'):
        n = n[4:]
    n = re.sub(r'[<>:"/\\|?*]', '_', n)
    n = n.strip('. ')
    return n or 'unknown_host'


class DownloadThread(threading.Thread):
    def __init__(self, url, filename, semaphore, state_code, agency_code, agency_name, engine, position_pool):
        super().__init__()
        self.url = url
        self.filename = filename
        self.semaphore = semaphore
        self.state_code = state_code
        self.agency_code = agency_code
        self.agency_name = agency_name
        self.engine = engine
        self.position_pool = position_pool

    def run(self):
        global downloaded_count, failed_count, duplicate_content_count
        with self.semaphore:
            time.sleep(0.3)
            position = self.position_pool.get()
            bar = None
            tmp_path = None
            try:
                r = requests.get(self.url, stream=True, timeout=40, headers=headers_mod.random_headers())
                r.raise_for_status()
                if 'pdf' not in r.headers.get('content-type', '').lower() and not self.url.lower().endswith('.pdf'):
                    return

                safe = re.sub(r'[<>:"/\\|?*]', '_', self.filename)
                if not safe.lower().endswith('.pdf'):
                    safe += '.pdf'

                # Folder named after the source URL's host, not the agency label.
                host_folder = sanitize_folder_name(urlparse(self.url).netloc)
                folder = os.path.join(config.DATA_DIR, host_folder)
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, safe)
                tmp_path = path + ".part"

                total = r.headers.get('content-length')
                total = int(total) if total and total.isdigit() else None
                desc = f"{host_folder[:18]:18} \u25b8 {safe[:24]}"
                bar = tqdm(total=total, unit='B', unit_scale=True, unit_divisor=1024,
                           desc=desc, position=position, leave=False, dynamic_ncols=True)

                hasher = StreamingSHA256()
                first_chunk = True
                magic_ok = True
                with open(tmp_path, 'wb') as f:
                    for c in r.iter_content(32768):
                        if not c:
                            continue
                        if first_chunk:
                            # Guard against slobber: HTML error pages saved
                            # with a fake .pdf name still fail this check.
                            magic_ok = c[:5] == b'%PDF-'
                            first_chunk = False
                            if not magic_ok:
                                break
                        f.write(c)
                        hasher.update(c)
                        bar.update(len(c))

                if not magic_ok:
                    os.remove(tmp_path)
                    with lock:
                        failed_count += 1
                    return

                sha = hasher.hexdigest()
                existing_id = db.fingerprint_exists(sha)
                if existing_id:
                    # Byte-identical to something we already have, just
                    # served from a different URL/host -- record the
                    # mapping, don't store the file twice.
                    os.remove(tmp_path)
                    db.insert_duplicate(self.url, sha, existing_id)
                    with lock:
                        duplicate_content_count += 1
                    return

                filesize = os.path.getsize(tmp_path)
                with lock:
                    os.replace(tmp_path, path)
                    downloaded_count += 1

                doc_id = db.insert_document(
                    url=self.url, sha256=sha, state=self.state_code,
                    agency_code=self.agency_code, agency_name=self.agency_name,
                    engine=self.engine, host=host_folder, filepath=path, filesize=filesize,
                )

                # --- OCR + indexing: every downloaded PDF becomes searchable ---
                try:
                    text = extract_text(path)
                    ocr_used = False
                    if not text.strip():
                        text = ocr_pdf(path)
                        ocr_used = bool(text.strip())
                    title = safe.rsplit('.', 1)[0].replace('_', ' ')
                    index_document(doc_id, title, text)
                    ents = extract_entities(text)
                    db.insert_entities(doc_id, ents)
                    db.mark_processed(doc_id, ocr_used=ocr_used, text_extracted=bool(text.strip()))
                except Exception:
                    pass  # indexing/OCR failure shouldn't lose the downloaded document

            except Exception:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                with lock:
                    failed_count += 1
            finally:
                if bar is not None:
                    bar.close()
                self.position_pool.put(position)
