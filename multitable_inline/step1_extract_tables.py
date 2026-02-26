import pdfplumber

def extract_table_candidates(pdf_path, pages=None):

    """
    Returns ALL possible table-like regions.
    No filtering. No assumptions.
    """

    candidates = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):

            # ✅ Skip pages not requested
            if pages and page_no not in pages:
                continue

            try:
                words = page.extract_words(
                    use_text_flow=True,
                    keep_blank_chars=False,
                    extra_attrs=["size", "fontname"]
                )
            except Exception as e:
                print(f"[STEP1] Page {page_no} | Skipped due to PDF error: {e}")
                continue

            if not words:
                continue

            candidates.append({
                "page": page_no,
                "words": words,
                "page_text": page.extract_text() or ""
            })

    return candidates