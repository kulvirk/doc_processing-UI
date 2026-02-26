import re
from multitable_inline.patterns import PART_NUMBER_HEADERS

TABLE_PN_REGEX = re.compile(
    r"""
    \b(
        \d{2}[A-Z]{2}\d{3,}
        |
        [A-Z]{2,}\d{3,}[A-Z]?
        |
        [A-Z]\d{3,}                 # ← ADD THIS
        |
        \d{3,}[-/]\d{2,}
        |
        \d{5,}
        |
        [A-Z]{2,}-\d{2,}           # CYL-0016, MNR-0008
        |
        [A-Z]\d{2,}                    # N634, N04058
        |
        \d{4,}[A-Z]?[-/A-Z0-9]*
    )\b
    """,
    re.VERBOSE
)


DESC_HEADERS = {"description", "part name", "item name", "partname"}


def extract_parts(normalized_table, debug=False):

    results = []

    page = normalized_table["page"]
    rows = normalized_table["rows"]

    if not rows:
        return results

    # =====================================================
    # 1️⃣ FLATTEN ALL WORDS FOR PAGE BOUNDS
    # =====================================================
    all_words = [w for row in rows for w in row["words"]]
    if not all_words:
        return results

    page_left = min(w["x0"] for w in all_words)
    page_right = max(w["x1"] for w in all_words)

    # =====================================================
    # 2️⃣ FIND HEADER ROW (must contain both PART + DESC)
    # =====================================================
    header_row = None

    for row in rows:
        row_text = " ".join(w["text"].lower() for w in row["words"])

        has_desc = any(h in row_text for h in DESC_HEADERS)
        has_part = any(h in row_text for h in PART_NUMBER_HEADERS) or (
            "part no" in row_text
        )

        if has_desc and has_part:
            header_row = row
            break

    if header_row is None:
        if debug:
            print(f"[STEP4] Page {page} | Header row not found")
        return results

    if debug:
        print("\n[STEP4 HEADER ROW]")
        print([w["text"] for w in header_row["words"]])

    # =====================================================
    # 3️⃣ DETECT COLUMN X POSITIONS FROM HEADER ROW ONLY
    # =====================================================
    desc_x = None
    part_x = None
    row_words = header_row["words"]
    header_x_positions = []

    i = 0
    while i < len(row_words):
    
        w = row_words[i]
        x = w["x0"]
        text = w["text"].strip().lower().replace(".", "")
    
        # -------------------------------------------------
        # MERGE: PART NO / PART NUMBER
        # -------------------------------------------------
        if text == "part" and i + 1 < len(row_words):
    
            next_word = row_words[i + 1]
            next_text = next_word["text"].strip().lower().replace(".", "")
            gap = next_word["x0"] - w["x1"]
    
            # ---- PART NO ----
            if next_text in {"no", "number"} and gap < 25:
    
                merged_left = min(w["x0"], next_word["x0"])
                part_x = merged_left
                header_x_positions.append(merged_left)
    
                i += 2
                continue
    
            # ---- SAFE PART DESCRIPTION ----
            if next_text == "description" and gap < 25:
    
                merged_left = min(w["x0"], next_word["x0"])
                desc_x = merged_left
                header_x_positions.append(merged_left)
    
                i += 2
                continue
    
        # -------------------------------------------------
        # NORMAL HEADER COLUMN
        # -------------------------------------------------
        header_x_positions.append(x)
    
        if any(h in text for h in DESC_HEADERS):
            desc_x = x
    
        if any(h in text for h in PART_NUMBER_HEADERS):
            part_x = x
    
        i += 1

    if desc_x is None or part_x is None:
        if debug:
            print(f"[STEP4] Page {page} | Missing DESC or PART header")
        return results

    # =====================================================
    # 4️⃣ SORT HEADER COLUMNS
    # =====================================================

    header_x_positions = sorted(header_x_positions)

    desc_index = header_x_positions.index(desc_x)
    part_index = header_x_positions.index(part_x)

    COL_MARGIN = 15

    # =====================================================
    # 5️⃣ COMPUTE DESCRIPTION BOUNDS
    # =====================================================

    if desc_index == 0:
        DESC_LEFT = page_left
    else:
        prev_col = header_x_positions[desc_index - 1]
        DESC_LEFT = prev_col + COL_MARGIN

    if desc_index == len(header_x_positions) - 1:
        DESC_RIGHT = page_right
    else:
        next_col = header_x_positions[desc_index + 1]
        DESC_RIGHT = next_col - COL_MARGIN

    # =====================================================
    # 6️⃣ COMPUTE PART NUMBER BOUNDS
    # =====================================================

    # If we detected merged Part No., use its real width
    if 'merged_part_header' in locals():
    
        PART_LEFT = merged_part_header["left"] - COL_MARGIN
    
        # Right boundary should extend until next header column
        if part_index == len(header_x_positions) - 1:
            PART_RIGHT = page_right
        else:
            next_col = header_x_positions[part_index + 1]
            PART_RIGHT = next_col - COL_MARGIN
    
    else:
        if part_index == 0:
            PART_LEFT = page_left
        else:
            prev_col = header_x_positions[part_index - 1]
            PART_LEFT = prev_col + COL_MARGIN
    
        if part_index == len(header_x_positions) - 1:
            PART_RIGHT = page_right
        else:
            next_col = header_x_positions[part_index + 1]
            PART_RIGHT = next_col - COL_MARGIN

    if debug:
        print("=" * 80)
        print(f"[STEP4-BOUNDS] Page {page}")
        print(f"DESC X: {desc_x}")
        print(f"PART X: {part_x}")
        print(f"DESC range: {DESC_LEFT:.2f} → {DESC_RIGHT:.2f}")
        print(f"PART range: {PART_LEFT:.2f} → {PART_RIGHT:.2f}")
        print("=" * 80)

    # =====================================================
    # 7️⃣ HEADER BOTTOM
    # =====================================================
    header_bottom = max(w["bottom"] for w in header_row["words"])
    # Collect all description-only rows for spatial matching
    desc_candidates = []
    
    for row in rows:
        if row["top"] <= header_bottom:
            continue
    
        desc_words = [
            w for w in row["words"]
            if DESC_LEFT <= w["x0"] <= DESC_RIGHT
        ]
    
        if desc_words:
            desc_words = sorted(desc_words, key=lambda w: w["x0"])
            desc_text = " ".join(w["text"] for w in desc_words).strip()
    
            if desc_text:
                desc_top = min(w["top"] for w in desc_words)
                desc_bottom = max(w["bottom"] for w in desc_words)
                desc_center = (desc_top + desc_bottom) / 2
    
                desc_candidates.append({
                    "text": desc_text,
                    "center": desc_center
                })

    # =====================================================
    # 8️⃣ EXTRACT DATA ROWS
    # =====================================================
    current_parent_description = None

    for row in rows:
    
        if row["top"] <= header_bottom:
            continue
    
        words = row["words"]
    
        # Words in description column
        desc_words = [
            w for w in words
            if DESC_LEFT <= w["x0"] <= DESC_RIGHT
        ]
    
        desc_words = sorted(desc_words, key=lambda w: w["x0"])
        description = " ".join(w["text"] for w in desc_words).strip()
    
        # Words in part column
        pn_words = [
            w for w in words
            if (
                PART_LEFT <= w["x0"] <= PART_RIGHT
                and TABLE_PN_REGEX.search(w["text"])
            )
        ]
    
        # -------------------------------------------------
        # CASE 1: Row has description but NO PN → store parent
        # -------------------------------------------------
        if description and not pn_words:
            current_parent_description = description
            continue
    
        # -------------------------------------------------
        # CASE 2: Row has PN but NO description → inherit
        # -------------------------------------------------
        if pn_words and not description and desc_candidates:
    
            pn_center = (
                min(w["top"] for w in pn_words) +
                max(w["bottom"] for w in pn_words)
            ) / 2
        
            # Find closest description vertically
            closest = min(
                desc_candidates,
                key=lambda d: abs(d["center"] - pn_center)
            )
    
            description = closest["text"]
    
        # -------------------------------------------------
        # CASE 3: Row has PN (normal or inherited)
        # -------------------------------------------------
        if not pn_words:
            continue
    
        for pn_word in pn_words:
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

    return results
