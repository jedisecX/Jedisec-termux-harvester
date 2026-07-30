import hashlib

def sha256_file(path, chunk_size=65536):
    """Fingerprint an existing file on disk (used for one-off checks / backfills)."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

class StreamingSHA256:
    """Fed chunks as they're written to disk so a download is fingerprinted
    in-flight instead of requiring a second full read of the file afterward."""
    def __init__(self):
        self._h = hashlib.sha256()

    def update(self, chunk):
        self._h.update(chunk)

    def hexdigest(self):
        return self._h.hexdigest()
