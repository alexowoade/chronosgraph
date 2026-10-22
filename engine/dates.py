import re
from typing import Tuple
from bs4 import BeautifulSoup

def _version_key(version: str):
    # "v2.4" -> (2, 4), "v2.4.1" -> (2, 4, 1), so max() picks the newest.
    nums = re.findall(r"\d+", version)
    return tuple(int(n) for n in nums)

def extract_temporal_signals(soup: BeautifulSoup, text_sample: str) -> Tuple[int, str, str]:
    """
    Returns (year, version_tag, iso_date).

    FIX 1 — version: the original took the FIRST decimal number in the
    text as the "version". For the fresh spec row
    "192 GB | 5.3 TB/s | 2026 v2.4" that returned "5.3", and for the
    fresh price row it returned "2.85". A bandwidth or a price is not
    a version. Now only v-prefixed versions (v2.4, v1.0) count, and
    the highest one wins, so a page mentioning v1.0 history and a
    v2.4 release is labelled v2.4, not v1.0.

    FIX 2 — fake dates: the original invented "2024-01-01" (or
    "<year>-01-01") when only a year was known. That fake precision
    then fed the freshness sort and the displayed metadata. Now
    iso_date is "" when no real ISO date was found; the year is
    kept separately and is the honest signal.
    """
    iso_dates = []
    years = []

    for meta in soup.find_all(["meta", "time"]):
        content = " ".join([str(v) for v in meta.attrs.values()]) + " " + meta.get_text(" ", strip=True)
        for d in re.findall(r"\b(20[12]\d-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b", content):
            iso_dates.append(d)
        for y in re.findall(r"\b(201\d|202\d|203\d)\b", content):
            years.append(int(y))

    for d in re.findall(r"\b(20[12]\d-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b", text_sample):
        iso_dates.append(d)
    for y in re.findall(r"\b(201\d|202\d|203\d)\b", text_sample):
        years.append(int(y))

    best_iso = max(iso_dates) if iso_dates else ""
    best_year = int(best_iso[:4]) if best_iso else (max(years) if years else 2024)

    v_versions = re.findall(r"\bv\d+\.\d+(?:\.\d+)?\b", text_sample.lower())
    # Also pick up v-versions from meta attributes, not just body text.
    for meta in soup.find_all(["meta", "time"]):
        meta_text = " ".join([str(v) for v in meta.attrs.values()])
        v_versions += re.findall(r"\bv\d+\.\d+(?:\.\d+)?\b", meta_text.lower())
    best_ver = max(v_versions, key=_version_key) if v_versions else "unversioned"
    return best_year, best_ver, best_iso
