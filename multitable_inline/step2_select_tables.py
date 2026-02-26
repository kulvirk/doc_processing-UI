from multitable_inline.patterns import (
    PART_NO_REGEX,
    PART_NUMBER_HEADERS,
    X_TOL,
)
import re
from multitable_inline.step3_geometry_normalize import normalize_table


FOOTER_Y_RATIO = 0.90
MAX_FOOTER_WORDS = 25
MIN_PN_COLUMN_HITS = 2


# ==================================================
# BASIC STRUCTURAL HEURISTIC
# ==================================================
def looks_like_table(words):
    texts = [w["text"].strip() for w in words if w.get("text")]

    numeric_tokens = sum(1 for t in texts if t.isdigit())
    short_tokens = sum(1 for t in texts if len(t) <= 4)
    total_tokens = len(texts)

    return (
        numeric_tokens >= 10 and
        short_tokens >= 15 and
        total_tokens >= 40
    )


# ==================================================
# BOM REGION DETECTOR
# ==================================================
def detect_bom_region(words):
    HEADER_KEYS = {
        "item",
        "qty",
        "part",
        "part number",
        "description",
    }

    lines = {}
    for w in words:
        y = round(w["top"] / 5) * 5
        lines.setdefault(y, []).append(w)

    for y, ws in lines.items():
        text_line = " ".join(w["text"].lower() for w in ws)
        hits = sum(1 for k in HEADER_KEYS if k in text_line)

        if hits >= 2:
            return {
                "top": y - 10,
                "bottom": max(w["bottom"] for w in ws) + 400,
                "left": min(w["x0"] for w in ws) - 50,
                "right": max(w["x1"] for w in ws) + 50,
            }

    return None


# ==================================================
# MAIN TABLE DECISION LOGIC
# ==================================================
def is_parts_table(table_candidate, debug=False):

    page = table_candidate["page"]
    words = table_candidate.get("words", [])

    if not words:
        if debug:
            print(f"[STEP2] Page {page} | Rejected (no words)")
        return False

    # --------------------------------------------------
    # DEBUG PAGE STATS
    # --------------------------------------------------
    if debug:
        texts = [w["text"] for w in words if w.get("text")]
        numeric = sum(1 for t in texts if t.isdigit())
        short = sum(1 for t in texts if len(t) <= 4)
        total = len(texts)

        print(
            f"[STEP2-DEBUG] Page {page} | "
            f"total={total}, numeric={numeric}, short={short}"
        )

    # --------------------------------------------------
    # BODY / FOOTER SPLIT
    # --------------------------------------------------
    page_bottom = max(w["bottom"] for w in words)
    footer_y = page_bottom * FOOTER_Y_RATIO

    footer_words = [w for w in words if w["top"] >= footer_y]
    body_words = [w for w in words if w["top"] < footer_y]

    footer_numeric_density = sum(
        1 for w in footer_words if w["text"].strip().isdigit()
    )

    if len(footer_words) > MAX_FOOTER_WORDS and footer_numeric_density < 5:
        body_words = words

    if not body_words:
        if debug:
            print(f"[STEP2] Page {page} | Rejected (empty body)")
        return False

    # --------------------------------------------------
    # NORMALIZE ONCE (used by all branches)
    # --------------------------------------------------
    normalized = normalize_table(
        {
            "page": page,
            "words": body_words
        },
        debug=False
    )

    rows = normalized.get("rows", [])
    columns = normalized.get("columns", [])
    part_col = normalized.get("part_col")

    body_text = " ".join(
        w["text"].lower().strip()
        for w in body_words
        if w.get("text")
    )
    if debug:
        print(f"[STEP2-DEBUG] rows count={len(rows)}")
        for r in rows[:5]:
            print([w["text"] for w in r["words"]])

    # ==================================================
    # 1️⃣ STRICT SIMPLE 2-COLUMN HEADER VALIDATION
    # ==================================================
    for row in rows:
    
        tokens = [w["text"].lower().replace(".", "") for w in row["words"]]
        joined = " ".join(tokens)
    
        # Accept both:
        # "Part Number | Description"
        # "Number | Description"
        if (
            ("description" in joined)
            and (
                "part number" in joined
                or "partno" in joined
                or "part no" in joined
                or "number" in joined
            )
        ):
    
            # Ensure visually 2 columns (cluster X positions)
            header_x_positions = sorted(w["x0"] for w in row["words"])
            clusters = []
    
            for x in header_x_positions:
                for i, cx in enumerate(clusters):
                    if abs(cx - x) < 40:
                        clusters[i] = (cx + x) / 2
                        break
                else:
                    clusters.append(x)
    
            if len(clusters) == 2:
                if debug:
                    print(f"[STEP2] Page {page} | STRICT SIMPLE_2COL_TABLE (header override)")
                return "SIMPLE_2COL_TABLE"
 
    # ==================================================
    # 2️⃣ ALT-ID EARLY OPT-IN
    # ==================================================
    if "drawing reference" in body_text and "tag no" in body_text:
        if debug:
            print(f"[STEP2] Page {page} | ALT_ID_TABLE (opt-in)")
        return "ALT_ID_TABLE"

    # ==================================================
    # 3️⃣ STRUCTURAL HEURISTIC (NUMERIC TABLES)
    # ==================================================

    # --------------------------------------------------
    # TRACEABILITY HEADER OVERRIDE
    # Accept tables like:
    # Description | Part number | Heat-code | Vendor
    # --------------------------------------------------
    for row in rows:
        tokens = {
            w["text"].lower().replace(".", "").replace(",", "")
            for w in row["words"]
        }
        if (
            "description" in tokens
            and (
                "partnumber" in tokens
                or ("part" in tokens and "number" in tokens)
            )
        ):
            if debug:
                print(f"[STEP2] Page {page} | TRACEABILITY HEADER ACCEPTED")
            return "NORMAL_TABLE"

    # HEADER OVERRIDE — if clear header row exists, accept
    for row in rows:
        tokens = {
            w["text"].lower().replace(".", "").replace(",", "")
            for w in row["words"]
        }
    
        # Accept if header contains core fields
        if (
            "description" in tokens
            and "qty" in tokens
            and (
                ("part" in tokens and "no" in tokens)
                or "partno" in tokens
                or "partnumber" in tokens
            )
        ):
            if debug:
                print(f"[STEP2] Page {page} | Header override accepted")
            return "NORMAL_TABLE"

    if not looks_like_table(body_words):
        if debug:
            print(f"[STEP2] Page {page} | Rejected (no table structure)")
        return False

    # ==================================================
    # 4️⃣ REQUIRE STRUCTURAL PN COLUMN
    # ==================================================
    if debug:
        print(f"[STEP2-DEBUG] columns={columns}")
        print(f"[STEP2-DEBUG] part_col={part_col}")
    
    if part_col is None or not columns:
        if debug:
            print(f"[STEP2] Page {page} | Rejected (no PN column)")
        return False

    # --------------------------------------------------
    # PN COLUMN DOMINANCE CHECK
    # --------------------------------------------------
    pn_hits = 0
    col_x = columns[part_col]

    for row in rows:
        for w in row["words"]:
            if PART_NO_REGEX.search(w["text"]):
                if abs(w["x0"] - col_x) < (X_TOL * 2):
                    pn_hits += 1
                    break

    if debug:
        print(f"[STEP2-DEBUG] pn_hits={pn_hits}")
        print(f"[STEP2-DEBUG] MIN_PN_COLUMN_HITS={MIN_PN_COLUMN_HITS}")
    if pn_hits < MIN_PN_COLUMN_HITS:
        if debug:
            print("REASON: < MIN_PN_COLUMN_HITS")
        return False

    # --------------------------------------------------
    # HEADER-ONLY GUARD
    # --------------------------------------------------
    header_hits = sum(
        1 for h in PART_NUMBER_HEADERS
        if h in body_text
    )

    if header_hits and pn_hits <= 2:
        if debug:
            print(f"[STEP2] Page {page} | Rejected (header-only table)")
        return False

    if debug:
        print(f"[STEP2] Page {page} | Accepted (NORMAL_TABLE)")
        print("=" * 80)

    return "NORMAL_TABLE"
