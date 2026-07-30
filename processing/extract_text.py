def extract_text(pdf_path, max_pages=None):
    """Best-effort text-layer extraction via pypdf.

    pypdf is pure Python -- no C extensions, no numpy, no compiled
    binary dependency -- so `pip install pypdf` works identically on a
    desktop, a server, or Termux with zero system package requirements.
    (Deliberately not using pdfplumber here: it pulls in pypdfium2,
    which has no reliable Android/aarch64 wheel and would otherwise
    force a from-source build.)

    Returns '' on failure or if pypdf isn't installed -- callers should
    treat an empty result as the signal to fall back to OCR (see
    ocr.py), which is exactly what downloader.py does.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(pdf_path)
        pages = reader.pages if max_pages is None else reader.pages[:max_pages]
        text_parts = []
        for page in pages:
            t = page.extract_text() or ""
            if t:
                text_parts.append(t)
        return "\n".join(text_parts).strip()
    except Exception:
        return ""
