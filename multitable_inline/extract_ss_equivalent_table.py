def extract_ss_equivalent_table(normalized_table, debug=False):

    results = []

    page = normalized_table["page"]
    rows = normalized_table["rows"]

    if not rows:
        return results

    # -------------------------------------------------
    # 1️⃣ Find header row
    # -------------------------------------------------
    header_row = None

    for row in rows:
        tokens = [w["text"].lower().replace(".", "") for w in row["words"]]
        joined = " ".join(tokens)

        if (
            "part" in joined
            and "number" in joined
            and "ss" in joined
            and "equivalent" in joined
            and "description" in joined
        ):
            header_row = row
            break

    if header_row is None:
        return results

    words_sorted = sorted(header_row["words"], key=lambda w: w["x0"])

    # -------------------------------------------------
    # 2️⃣ Merge header blocks geometrically
    # -------------------------------------------------
    pn1_left = pn1_right = None
    pn2_left = pn2_right = None
    desc_left = None

    i = 0
    while i < len(words_sorted):

        text = words_sorted[i]["text"].lower().replace(".", "")

        # PART + NUMBER
        if text == "part" and i + 1 < len(words_sorted):
            if words_sorted[i+1]["text"].lower().replace(".", "") == "number":
                w1 = words_sorted[i]
                w2 = words_sorted[i+1]
                pn1_left = min(w1["x0"], w2["x0"])
                pn1_right = max(w1["x1"], w2["x1"])
                i += 2
                continue

        # SS + EQUIVALENT
        if text == "ss" and i + 1 < len(words_sorted):
            if words_sorted[i+1]["text"].lower().replace(".", "") == "equivalent":
                w1 = words_sorted[i]
                w2 = words_sorted[i+1]
                pn2_left = min(w1["x0"], w2["x0"])
                pn2_right = max(w1["x1"], w2["x1"])
                i += 2
                continue

        # DESCRIPTION
        if "description" in text:
            desc_left = words_sorted[i]["x0"]

        i += 1

    if pn1_left is None or pn2_left is None or desc_left is None:
        return results

    # -------------------------------------------------
    # 3️⃣ Compute column bounds
    # -------------------------------------------------

    COL_MARGIN = 10

    PART1_LEFT  = pn1_left - COL_MARGIN
    PART1_RIGHT = pn1_right + COL_MARGIN

    PART2_LEFT  = pn2_left - COL_MARGIN
    PART2_RIGHT = pn2_right + COL_MARGIN

    DESC_LEFT   = desc_left - COL_MARGIN
    DESC_RIGHT  = max(w["x1"] for r in rows for w in r["words"])

    header_bottom = max(w["bottom"] for w in header_row["words"])

    # -------------------------------------------------
    # 4️⃣ Extract rows
    # -------------------------------------------------

    from multitable_inline.patterns import PART_NO_REGEX

    for row in rows:

        if row["top"] <= header_bottom:
            continue

        words = row["words"]

        pn1_words = [
            w for w in words
            if PART1_LEFT <= w["x0"] <= PART1_RIGHT
            and PART_NO_REGEX.search(w["text"])
        ]

        pn2_words = [
            w for w in words
            if PART2_LEFT <= w["x0"] <= PART2_RIGHT
            and PART_NO_REGEX.search(w["text"])
        ]

        desc_words = [
            w for w in words
            if DESC_LEFT <= w["x0"] <= DESC_RIGHT
        ]

        description = " ".join(
            w["text"] for w in sorted(desc_words, key=lambda w: w["x0"])
        ).strip()

        if not description:
            continue

        # Combine both PN columns and remove duplicates
        all_pn_words = pn1_words + pn2_words
        
        seen = set()
        
        for pn_word in all_pn_words:
        
            pn_value = pn_word["text"]
        
            if pn_value in seen:
                continue
        
            seen.add(pn_value)

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