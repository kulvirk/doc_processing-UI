import re

# Numeric-first, industrial-safe part numbers

PART_NO_REGEX = re.compile(
    r"""
    \b
    (
        (?!\d{1,2}-[A-Za-z]{3})

        \d{4,9}                             # pure numeric
        |
        \d{2,6}[-/][0-9A-Z]{2,6}            # hyphen/slash
        |
        \d{2}[A-Z]{2}\d{3,}                 # 01PS0002
        |
        [A-Z]{2,}\d{3,}[A-Z]?               # OEM2906B
        |
        \d{4,}[A-Z]\d{2,}                   # 1234A56
        |
        \d{4,}[A-Z]{1,3}                    # 1383A, 6443SR
        |
        \d+[A-Z]+\d*                        # 110377E200
        |
        [A-Z]\d{2,}                    # N634, N04058
        |
        [A-Z]{2,}-\d{2,}           # CYL-0016, MNR-0008
    )
    \b
    """,
    re.VERBOSE
)


# Headers that indicate non-data rows
PART_NUMBER_HEADERS = {
    "part no",
    "partno.",
    "partno",
    "parts",
    "part number",
    "p/n",
    "pn",
    "pin",
    "kit",
    "kit number",
    "kit no",
    "item",
    "component",
    "component item",
    "article no",
    "article number",

    # NEW — industrial manuals often misuse this
    "material",
    "material no",
    "material number",
}


# Geometry tolerances (unchanged)
X_TOL = 15
Y_TOL = 5
