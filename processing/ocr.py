def ocr_pdf(pdf_path, dpi=200, max_pages=None):
    """OCR fallback for scanned/image-only PDFs (no text layer).

    Requires: pdf2image + pytesseract (pip) AND system installs of
    Tesseract OCR + Poppler (apt/pkg install tesseract-ocr poppler-utils,
    or on Termux: pkg install tesseract poppler). Returns '' if any of
    that isn't available so the rest of the pipeline still completes --
    the document just won't be text-searchable until OCR deps are added.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        return ""
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
        if max_pages:
            images = images[:max_pages]
        text_parts = [pytesseract.image_to_string(img) for img in images]
        return "\n".join(text_parts).strip()
    except Exception:
        return ""
