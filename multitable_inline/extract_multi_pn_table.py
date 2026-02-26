import re
from multitable_inline.patterns import PART_NO_REGEX

PN_HEADER_REGEX = re.compile(
    r"""
    ^
    (p\/?n)              # P/N or PN
    $
    |
    ^
    (part\s*number)
    $
    |
    ^
    (pin)                # ONLY standalone PIN
    $
    """,
    re.IGNORECASE | re.VERBOSE
)

def extract_multi_pn_table(normalized_table, debug=False):

    results = []

    page = normalized_table["page"]
    rows = normalized_table.get("rows", [])

    if not rows:
        if debug:
            print("NO ROWS")
        return results

    # -------------------------------------------------
    # 1️⃣ Find header row
    # -------------------------------------------------
    header_row = None

    for row in rows[:8]:

        row_text = " ".join(w["text"].lower() for w in row["words"])
    
        has_desc = "description" in row_text
    
        has_pn = any(
            PN_HEADER_REGEX.search(w["text"])
            for w in row["words"]
        )
    
        if has_desc and has_pn:
            header_row = row
            break

    if not header_row:
        if debug:
            print("HEADER NOT FOUND")
        return results

    if debug:
        print(f"\n[MULTI-PN HEADER] {[w['text'] for w in header_row['words']]}")

    header_bottom = max(w["bottom"] for w in header_row["words"])

    # -------------------------------------------------
    # Detect PN header anchors
    # -------------------------------------------------
    pn_header_words = [
        w for w in header_row["words"]
        if PN_HEADER_REGEX.search(w["text"])
    ]

    if debug:
        print("PN HEADER WORDS:", [(w["text"], w["x0"]) for w in pn_header_words])

    if len(pn_header_words) < 2:
        if debug:
            print("NOT MULTI PN (less than 2 PN headers)")
        return results

    pn_header_words = sorted(pn_header_words, key=lambda w: w["x0"])

    # -------------------------------------------------
    # Header geometry using full word width
    # -------------------------------------------------
    
    # Group header words by approximate column (cluster by x0 proximity)
    COLUMN_TOL = 15
    
    sorted_words = sorted(header_row["words"], key=lambda w: w["x0"])
    
    header_columns = []
    
    for w in sorted_words:

        placed = False
    
        for col in header_columns:
    
            if abs(w["x0"] - col["left"]) < COLUMN_TOL:
    
                # expand envelope
                col["left"] = min(col["left"], w["x0"])
                col["right"] = max(col["right"], w["x1"])
                col["words"].append(w)
    
                if debug:
                    print("COLUMN ENVELOPE AFTER MERGE:")
                    print(f"   left={col['left']:.2f} right={col['right']:.2f}")
                    print(f"   words={[word['text'] for word in col['words']]}")
                    print("=" * 80)
    
                placed = True
                break
    
        if not placed:

            header_columns.append({
                "left": w["x0"],
                "right": w["x1"],
                "words": [w]
            })
    
    # Sort columns left to right
    header_columns = sorted(header_columns, key=lambda c: c["left"])

    # Compute page_right
    page_right = max(
        w["x1"]
        for r in rows
        for w in r["words"]
    )
    MARGIN = 10

    # -------------------------------------------------
    # Extract rows
    # -------------------------------------------------
    for row in rows:

        if row["top"] <= header_bottom:
            continue

        words = row["words"]

        for pn_header in pn_header_words:

            pn_x = pn_header["x0"]

            # column index based on header_columns
            col_index = None
            
            for i, col in enumerate(header_columns):
                if col["left"] <= pn_x <= col["right"]:
                    col_index = i
                    break
            
            if col_index is None:
                if debug:
                    print("PN header column not found")
                continue

            # PN band based on its own column width
            PN_LEFT = header_columns[col_index]["left"] - 5

            # 👉 use PN header word right edge + small margin
            PN_RIGHT = header_columns[col_index]["right"] + 12

            # ----------------------------
            # DESC band
            # ----------------------------
            if col_index + 1 >= len(header_columns):
                continue

            DESC_LEFT = PN_RIGHT + 2

            if col_index + 2 < len(header_columns):
                DESC_RIGHT = header_columns[col_index + 2]["left"] - MARGIN
            else:
                DESC_RIGHT = page_right
            
                # -------------------------------------------------
                # 🔥 Emit band boxes for overlay
                # -------------------------------------------------
                band_height_top = min(w["top"] for w in words)
                band_height_bottom = max(w["bottom"] for w in words)
            
                # PN band box

                if debug:

                    band_height_top = min(w["top"] for w in words)
                    band_height_bottom = max(w["bottom"] for w in words)
                
                    debug_trace = {
                        "pn_boxes": [{
                            "text": "PN_BAND",
                            "x0": PN_LEFT,
                            "x1": PN_RIGHT,
                            "top": band_height_top,
                            "bottom": band_height_bottom,
                        }],
                        "desc_boxes": [{
                            "text": "DESC_BAND",
                            "x0": DESC_LEFT,
                            "x1": DESC_RIGHT,
                            "top": band_height_top,
                            "bottom": band_height_bottom,
                        }]
                    }

            # Extract PN words
            pn_words = [
                w for w in words
                if PN_LEFT <= w["x0"] <= PN_RIGHT
                and PART_NO_REGEX.search(w["text"])
            ]

            if not pn_words:
                continue

            # Extract description words
            desc_words = [
                w for w in words
                if DESC_LEFT <= w["x0"] <= DESC_RIGHT
            ]

            if not desc_words:
                continue

            description = " ".join(
                w["text"] for w in sorted(desc_words, key=lambda x: x["x0"])
            ).strip()

            if not description:
                continue

            for pn_word in pn_words:
                entry = {
                    "page": page,
                    "part_no": pn_word["text"],
                    "description": description
                }

                if debug:
                    entry["trace"] = {
                        "pn_boxes": [
                            {
                                "text": w["text"],
                                "x0": w["x0"],
                                "x1": w["x1"],
                                "top": w["top"],
                                "bottom": w["bottom"],
                            }
                            for w in pn_words
                        ],
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
        print(f"\n[MULTI-PN] Extracted {len(results)} parts")

    return results