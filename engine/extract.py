import re
import urllib.parse
from dataclasses import dataclass
from typing import List, Tuple
from bs4 import BeautifulSoup
from engine.dates import extract_temporal_signals
from engine.query import score_passage
from engine.receipt import compute_sha256_receipt

@dataclass
class ClaimNode:
    url: str
    page_title: str
    source_type: str        # "spec_table", "json_ld", "body_text"
    freshness_year: int
    version_tag: str
    quote: str
    relevance_score: float
    authority_score: float
    sha256_receipt: str
    iso_date: str = ""

# FIX — freshness weight: the original boost was
# 1.0 + (year - 2022) * 0.08. For 2026 that is 1.32, for 2023 it is
# 1.08. A stale table (weight 1.35 x 1.08 = 1.46) therefore beat a
# fresh paragraph (1.00 x 1.32 = 1.32) with the same relevance.
# The existing tests never caught this because they paired a stale
# paragraph against a fresh table — both weights pointed the same way.
# 0.30 per year makes a 2026 paragraph (2.20) beat a 2023 table (1.76)
# and a 2024 table (2.16) only just, which is the right trade-off:
# freshness should usually win, a 1-year-old table may still win.
def _freshness_factor(year: int) -> float:
    return 1.0 + max(0, (year - 2022) * 0.30)

def parse_page_into_claims(url: str, html: str, keywords: List[str]) -> Tuple[str, List[ClaimNode], List[Tuple[float, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url
    full_text = soup.get_text(" ", strip=True)
    page_year, page_ver, page_iso = extract_temporal_signals(soup, full_text[:3000])
    freshness_boost = _freshness_factor(page_year)

    claims: List[ClaimNode] = []

    # 1. HTML Specification Tables
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(" ", strip=True) for th in thead.find_all("th")]
        else:
            first_tr = table.find("tr")
            # FIX — row headers: the original treated the first row's
            # <th> as column headers even when that row was a data row
            # like <th scope="row">Thermal Design Power</th><td>750 W</td>.
            # That produced "[Thermal Design Power] | Thermal Design
            # Power | 750 W". Only treat a first row as a header row
            # when it has <th> and NO <td>.
            if first_tr and first_tr.find_all("th") and not first_tr.find_all("td"):
                headers = [th.get_text(" ", strip=True) for th in first_tr.find_all("th")]
            else:
                headers = []
        h_prefix = ("[" + " | ".join(headers[:6]) + "] ") if headers else ""

        for row in table.find_all("tr"):
            if not row.find_all("td"):
                continue
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            row_str = h_prefix + " | ".join([c for c in cells if c])
            rel = score_passage(row_str, keywords)
            if rel > 0:
                y, v, iso = extract_temporal_signals(soup, row_str + " " + title)
                eff_year = max(page_year, y)
                eff_iso = max(page_iso, iso) if page_iso and iso else (page_iso or iso)
                auth = round(rel * 1.35 * _freshness_factor(eff_year), 4)
                q_trim = row_str[:500]
                claims.append(ClaimNode(
                    url, title, "spec_table", eff_year,
                    v if v != "unversioned" else page_ver,
                    q_trim, rel, auth, compute_sha256_receipt(url, q_trim), eff_iso
                ))

    # 2. JSON-LD Structured Schemas
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.get_text(strip=True)
        rel = score_passage(raw, keywords)
        if rel > 0:
            auth = round(rel * 1.25 * freshness_boost, 4)
            q_trim = raw[:500]
            claims.append(ClaimNode(
                url, title, "json_ld", page_year, page_ver,
                q_trim, rel, auth, compute_sha256_receipt(url, q_trim), page_iso
            ))

    # 3. Body Paragraphs & Release Notes
    # FIX: the original also scanned <article>, which contains its own
    # <p> children, so every paragraph inside an article was claimed
    # twice (once as the paragraph, once as the whole article). Only
    # p / li / dd are scanned now.
    for tag in soup.find_all(["p", "li", "dd"]):
        txt = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))
        if 20 <= len(txt) <= 750:
            rel = score_passage(txt, keywords)
            if rel > 0:
                y, v, iso = extract_temporal_signals(soup, txt)
                eff_year = max(page_year, y)
                eff_iso = max(page_iso, iso) if page_iso and iso else (page_iso or iso)
                auth = round(rel * _freshness_factor(eff_year), 4)
                claims.append(ClaimNode(
                    url, title, "body_text", eff_year,
                    v if v != "unversioned" else page_ver,
                    txt, rel, auth, compute_sha256_receipt(url, txt), eff_iso
                ))

    # 4. Multi-Hop Link Discovery
    links: List[Tuple[float, str]] = []
    base_dom = urllib.parse.urlparse(url).netloc
    for a in soup.find_all("a", href=True):
        full_url = urllib.parse.urljoin(url, a["href"]).split("#")[0]
        if not full_url.startswith("http"):
            continue
        l_sc = score_passage((a.get_text(" ", strip=True) + " " + a["href"]).lower(), keywords)
        if urllib.parse.urlparse(full_url).netloc == base_dom:
            l_sc *= 1.25
        if l_sc > 0:
            links.append((l_sc, full_url))
    links.sort(key=lambda x: x[0], reverse=True)
    return title, claims, links[:4]
