from multitable_inline.patterns import PART_NO_REGEX

import re

SIMPLE2_PN_REGEX = re.compile(
    r"""
    ^
    (
        \d{4,}                              # pure numeric
        |
        [A-Z]{4,}[A-Z0-9]*                 # long uppercase industrial codes
        |
        [A-Z0-9]+(?:[-/][A-Z0-9]+)+        # hyphen/slash codes
        |
        [A-Z]{2,}\d{3,}[A-Z]?              # OEM style
        |
        \d+[A-Z]+\d*                       # 110377E200
    )
    $
    """,
    re.VERBOSE
)

def extract_simple_2col_table(normalized_table, debug=False):

    results = []

    page = normalized_table["page"]
    rows = normalized_table.get("rows", [])

    if not rows:
        return results

    # --------------------------------------------------
    # 1️⃣ PAGE BOUNDS
    # --------------------------------------------------
    all_words = [w for row in rows for w in row["words"]]
    page_left = min(w["x0"] for w in all_words)
    page_right = max(w["x1"] for w in all_words)

    # --------------------------------------------------
    # 2️⃣ FIND HEADER ROW
    # --------------------------------------------------
    header_row = None

    for row in rows:
        row_text = " ".join(w["text"].lower() for w in row["words"])
    
        # Accept both:
        # "Part Number | Description"
        # "Number | Description"
        if (
            "description" in row_text
            and (
                "part" in row_text
                or "number" in row_text
            )
        ):
            header_row = row
            break

    if header_row is None:
        if debug:
            print(f"[SIMPLE_2COL] Page {page} | Header not found")
        return results

    # --------------------------------------------------
    # 3️⃣ DETECT HEADER COLUMN ENVELOPES
    # --------------------------------------------------
    pn_left = None
    pn_right = None
    desc_left = None
    desc_right = None

    words_sorted = sorted(header_row["words"], key=lambda w: w["x0"])

    i = 0
    while i < len(words_sorted):
    
        text = words_sorted[i]["text"].lower().replace(".", "").strip()
    
        # Detect "Part Number"
        if text == "part" and i + 1 < len(words_sorted):
            next_text = words_sorted[i + 1]["text"].lower().replace(".", "").strip()
            # Detect standalone "Number" header
        if text == "number":
            w = words_sorted[i]
            pn_left = w["x0"]
            pn_right = w["x1"]
            i += 1
            continue
            if next_text in {"number", "no"}:
                w1 = words_sorted[i]
                w2 = words_sorted[i + 1]
    
                pn_left = min(w1["x0"], w2["x0"])
                pn_right = max(w1["x1"], w2["x1"])
                i += 2
                continue
    
        if "part" in text:
            w = words_sorted[i]
            pn_left = w["x0"]
            pn_right = w["x1"]
    
        if "description" in text:
            w = words_sorted[i]
            desc_left = w["x0"]
            desc_right = w["x1"]
    
        i += 1
    
    
    # ✅ MOVE VALIDATION HERE — AFTER LOOP
    if pn_left is None or desc_left is None:
        if debug:
            print(f"[SIMPLE_2COL] Page {page} | Header columns not detected")
            print(f"pn_left={pn_left}, desc_left={desc_left}")
            print("Header words:", [w["text"] for w in header_row["words"]])
        return results
    
    
    # ✅ DEBUG PRINT HERE — AFTER VALIDATION
    if debug:
        print("\n" + "=" * 80)
        print(f"[SIMPLE_2COL HEADER GEOMETRY] Page {page}")
        print(f"PN  header: left={pn_left:.2f}, right={pn_right:.2f}")
        print(f"DESC header: left={desc_left:.2f}, right={desc_right:.2f}")
        print("=" * 80)

    if pn_left is None or desc_left is None:
        if debug:
            print(f"[SIMPLE_2COL] Page {page} | Header columns not detected")
        return results

    # --------------------------------------------------
    # 4️⃣ COMPUTE BOUNDS
    # --------------------------------------------------
    COL_MARGIN = 5

    if pn_left < desc_left:
        PART_LEFT  = page_left
        PART_RIGHT = pn_right + 12
        
        DESC_LEFT  = PART_RIGHT + COL_MARGIN
        DESC_RIGHT = page_right
    else:
        PART_LEFT  = pn_left - COL_MARGIN
        PART_RIGHT = page_right
        DESC_LEFT  = page_left
        DESC_RIGHT = pn_left - COL_MARGIN

    if debug:
        print("=" * 80)
        print(f"[SIMPLE_2COL FINAL BOUNDS] Page {page}")
        print(f"PART range: {PART_LEFT:.2f} → {PART_RIGHT:.2f}")
        print(f"DESC range: {DESC_LEFT:.2f} → {DESC_RIGHT:.2f}")
        print("=" * 80)

    header_bottom = max(w["bottom"] for w in header_row["words"])

    # --------------------------------------------------
    # 5️⃣ EXTRACT ROWS
    # --------------------------------------------------
    for row in rows:

        if row["top"] <= header_bottom:
            continue

        pn_words = [
            w for w in row["words"]
            if PART_LEFT <= w["x0"] <= PART_RIGHT
            and SIMPLE2_PN_REGEX.fullmatch(w["text"])
        ]

        if not pn_words:
            continue

        pn_word = sorted(pn_words, key=lambda w: w["x0"])[0]

        desc_words = [
            w for w in row["words"]
            if DESC_LEFT <= w["x0"] <= DESC_RIGHT
        ]

        description = " ".join(
            w["text"] for w in sorted(desc_words, key=lambda w: w["x0"])
        ).strip()

        if not description:
            continue

        entry = {
            "page": page,
            "part_no": pn_word["text"],
            "description": description
        }
        
        if debug:
            entry["trace"] = {
                "pn_boxes": [{
                    "text": pn_word["text"],
                    "x0": pn_word["x0"],
                    "x1": pn_word["x1"],
                    "top": pn_word["top"],
                    "bottom": pn_word["bottom"],
                }],
                "desc_boxes": [
                    {
                        "text": w["text"],
                        "x0": w["x0"],
                        "x1": w["x1"],
                        "top": w["top"],
                        "bottom": w["bottom"],
                    }
                    for w in desc_words
                ]
            }
        
        results.append(entry)

    if debug:
        print(f"[SIMPLE_2COL] Extracted {len(results)} rows")

    return results