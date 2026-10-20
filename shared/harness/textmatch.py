"""Normalization rules for finding a value inside free text.

These rules decide what the code scorer accepts, so they are part of the
measurement: changing them can change utility numbers.
"""

import re

_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]


def mentions_time(text: str, hhmm: str) -> bool:
    """True if `text` mentions the time HH:MM.
    Accepted: 15:30, 15.30, 3:30 pm, 3:30pm, 3.30 p.m.; for full hours also 10am, 10 a.m."""
    h, m = (int(x) for x in hhmm.split(":"))
    variants = [rf"{h:02d}[:.]{m:02d}", rf"{h}[:.]{m:02d}"]
    h12 = h % 12 or 12
    ampm = r"\s*(a\.?m\.?)" if h < 12 else r"\s*(p\.?m\.?)"
    variants.append(rf"{h12}[:.]{m:02d}{ampm}")
    if m == 0:
        variants.append(rf"{h12}{ampm}")
    pattern = r"(?<![\d:.])(" + "|".join(variants) + r")(?![\d])"
    return re.search(pattern, text.lower()) is not None


def mentions_date(text: str, iso_date: str) -> bool:
    """True if `text` mentions the date YYYY-MM-DD.
    Accepted: 2026-11-03, November 3, Nov 3, Nov. 3rd, 3 November, 3rd of November."""
    y, mo, d = (int(x) for x in iso_date.split("-"))
    month = _MONTHS[mo - 1]
    mon = rf"({month}|{month[:3]}\.?)"
    day = rf"{d}(st|nd|rd|th)?"
    variants = [
        rf"{y}-{mo:02d}-{d:02d}",
        rf"{mon}\s+{day}(?!\d)",
        rf"(?<!\d){day}\s+(of\s+)?{mon}",
    ]
    return re.search("|".join(variants), text.lower()) is not None


def mentions_number(text: str, n: int, word: str) -> bool:
    """True if `text` contains the number as digits or as a word."""
    return re.search(rf"(?<![\d.]){n}(?![\d.])|\b{word}\b", text.lower()) is not None


def contains(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()
