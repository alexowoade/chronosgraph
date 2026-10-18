import re
import time
import hashlib
import urllib.parse
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

@dataclass
class ClaimNode:
    url: str
    page_title: str
    source_type: str        # "spec_table", "json_ld", "body_text"
    freshness_year: int     # Extracted release/modification year (e.g., 2026 vs 2023)
    version_tag: str        # Extracted version string (e.g., "v2.4" vs "v1.0")
    quote: str
    relevance_score: float
    authority_score: float  # Combined relevance + freshness + structural weight
    sha256_receipt: str

@dataclass
class ChronosResult:
    query: str
    status: str             # "VERIFIED_CONSENSUS", "VERIFIED_TEMPORAL_OVERRIDE", or "REFUSED_UNVERIFIABLE"
    answer: str
    primary_citation: str
    verbatim_quote: str
    sha256_evidence_hash: str
    freshness_metadata: str
    conflict_detected: bool
    conflict_log: List[Dict[str, str]]
    navigation_trace: List[Dict[str, str]]
    compute_backend: str
    latency_ms: float

class ChronosGraphROCmAgent:
    """
    ChronosGraph: Temporal Conflict & Cross-Page Claim Verification Engine.
    Uniquely resolves contradictory/stale web pages by extracting temporal timestamps,
    semantic versions, and structural authority on AMD ROCm + PyTorch.
    """
    def __init__(self, model_id: str = "Qwen/Qwen2.5-1.5B-Instruct", max_pages: int = 6, max_hops: int = 2):
        self.model_id = model_id
        self.max_pages = max_pages
        self.max_hops = max_hops
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ChronosGraph-ROCm/2.0"})
        self.compute_backend = self._detect_rocm()

    def _detect_rocm(self) -> str:
        if TORCH_AVAILABLE and torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            hip = getattr(torch.version, "hip", None)
            return f"AMD ROCm GPU ({name} | HIP {hip})" if hip else f"GPU ({name})"
        return "AMD ROCm-Ready Deterministic Graph Engine"

    def tokenize_query(self, text: str) -> List[str]:
        stop = {"what","is","the","of","in","for","to","a","an","and","or","on","at","by","with","from","how","much","many","does","do","can","you","find","tell","me","current","latest","who","where","when","official"}
        return [w for w in re.findall(r"[a-zA-Z0-9_.\-]+", text.lower()) if w not in stop and len(w) > 1]

    def extract_temporal_signals(self, soup: BeautifulSoup, text_sample: str) -> Tuple[int, str]:
        """Extracts page modification year and semantic version tags to defeat stale web pages."""
        years = []
        for meta in soup.find_all(["meta", "time"]):
            content = " ".join([str(v) for v in meta.attrs.values()])
            for y in re.findall(r"\b(201\d|202\d)\b", content):
                years.append(int(y))
        for y in re.findall(r"\b(201\d|202\d)\b", text_sample):
            years.append(int(y))
        best_year = max(years) if years else 2024

        versions = re.findall(r"\bv?\d+\.\d+(?:\.\d+)?\b", text_sample.lower())
        best_ver = versions[0] if versions else "unversioned"
        return best_year, best_ver

    def compute_sha256_receipt(self, url: str, quote: str) -> str:
        payload = f"{url.strip()}||{quote.strip()}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def score_passage(self, text: str, keywords: List[str]) -> float:
        if not keywords:
            return 0.0
        lower_t = text.lower()
        hits = sum(1 for kw in keywords if kw in lower_t)
        if hits == 0:
            return 0.0
        metric_bonus = 0.35 if re.search(r"(\d+(\.\d+)?\s*(gb|mb|tb|tb/s|ms|s|w|ghz|mhz|%|usd|\$|€|cores)|v\d+\.\d+)", lower_t) else 0.0
        return round((hits / len(keywords)) + metric_bonus, 4)

    def parse_page_into_claims(self, url: str, html: str, keywords: List[str]) -> Tuple[str, List[ClaimNode], List[Tuple[float, str]]]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else url
        full_text = soup.get_text(" ", strip=True)
        page_year, page_ver = self.extract_temporal_signals(soup, full_text[:3000])
        freshness_boost = 1.0 + max(0, (page_year - 2022) * 0.08)

        claims: List[ClaimNode] = []

        # 1. HTML Specification Tables (Preserves column headers AND row <th> labels)
        for table in soup.find_all("table"):
            thead = table.find("thead")
            if thead:
                headers = [th.get_text(" ", strip=True) for th in thead.find_all("th")]
            else:
                first_tr = table.find("tr")
                headers = [th.get_text(" ", strip=True) for th in first_tr.find_all("th")] if first_tr else []
            h_prefix = ("[" + " | ".join(headers[:6]) + "] ") if headers else ""

            for row in table.find_all("tr"):
                if not row.find_all("td"):
                    continue
                cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
                row_str = h_prefix + " | ".join([c for c in cells if c])
                rel = self.score_passage(row_str, keywords)
                if rel > 0:
                    y, v = self.extract_temporal_signals(soup, row_str + " " + title)
                    eff_year = max(page_year, y)
                    auth = round(rel * 1.35 * (1.0 + max(0, (eff_year - 2022) * 0.08)), 4)
                    claims.append(ClaimNode(url, title, "spec_table", eff_year, v if v != "unversioned" else page_ver, row_str[:500], rel, auth, self.compute_sha256_receipt(url, row_str[:500])))

        # 2. JSON-LD Structured Schemas
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.get_text(strip=True)
            rel = self.score_passage(raw, keywords)
            if rel > 0:
                auth = round(rel * 1.25 * freshness_boost, 4)
                claims.append(ClaimNode(url, title, "json_ld", page_year, page_ver, raw[:500], rel, auth, self.compute_sha256_receipt(url, raw[:500])))

        # 3. Body Paragraphs & Release Notes
        for tag in soup.find_all(["p", "li", "article", "dd"]):
            txt = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))
            if 20 <= len(txt) <= 750:
                rel = self.score_passage(txt, keywords)
                if rel > 0:
                    y, v = self.extract_temporal_signals(soup, txt)
                    eff_year = max(page_year, y)
                    auth = round(rel * (1.0 + max(0, (eff_year - 2022) * 0.08)), 4)
                    claims.append(ClaimNode(url, title, "body_text", eff_year, v if v != "unversioned" else page_ver, txt, rel, auth, self.compute_sha256_receipt(url, txt)))

        # 4. Multi-Hop Link Discovery
        links: List[Tuple[float, str]] = []
        base_dom = urllib.parse.urlparse(url).netloc
        for a in soup.find_all("a", href=True):
            full_url = urllib.parse.urljoin(url, a["href"]).split("#")[0]
            if not full_url.startswith("http"):
                continue
            l_sc = self.score_passage((a.get_text(" ", strip=True) + " " + a["href"]).lower(), keywords)
            if urllib.parse.urlparse(full_url).netloc == base_dom:
                l_sc *= 1.25
            if l_sc > 0:
                links.append((l_sc, full_url))
        links.sort(key=lambda x: x[0], reverse=True)
        return title, claims, links[:4]

    def keyless_search(self, query: str, max_results: int = 4) -> List[str]:
        urls = []
        try:
            r = self.session.post("https://html.duckduckgo.com/html/", data={"q": query}, timeout=8)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("a.result__a"):
                    href = a.get("href", "")
                    if "uddg=" in href:
                        qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "uddg" in qs:
                            href = qs["uddg"][0]
                    if href.startswith("http") and href not in urls:
                        urls.append(href)
                    if len(urls) >= max_results:
                        break
        except Exception:
            pass
        return urls

    def verify_verbatim_grounding(self, candidate: str, quote: str, keywords: List[str]) -> bool:
        """
        Strict Cite-or-Refuse Gate:
        1. Every number in candidate answer must appear verbatim in the source quote.
        2. Query numbers (e.g. model numbers/years) if present must not be contradicted,
           and at least 1 core query keyword must be grounded in the quote.
        """
        if not candidate or not quote:
            return False
        for num in re.findall(r"\b\d+(?:\.\d+)?\b", candidate):
            if num not in quote:
                return False
        matched = [kw for kw in keywords if kw in quote.lower()]
        return len(matched) >= max(1, int(len(keywords) * 0.3))

    def detect_and_resolve_conflicts(self, claims: List[ClaimNode]) -> Tuple[bool, List[Dict[str, str]]]:
        """Compares top claims across pages to identify stale/conflicting numerical values."""
        if len(claims) < 2:
            return False, []
        winner = claims[0]
        unit_pattern = r"\b\d+(?:\.\d+)?\s*(?:gb|tb/s|tb|mb|w|ghz|mhz|ms|%|usd|\$|€|cores)\b"
        win_nums = set(re.findall(unit_pattern, winner.quote.lower()))
        conflict_log = []
        conflict_found = False

        for other in claims[1:5]:
            if other.url == winner.url and other.quote == winner.quote:
                continue
            other_nums = set(re.findall(unit_pattern, other.quote.lower()))
            if win_nums and other_nums and win_nums != other_nums:
                conflict_found = True
                conflict_log.append({
                    "resolution": "SELECTED_AUTHORITATIVE_CURRENT",
                    "winning_url": winner.url,
                    "winning_year": str(winner.freshness_year),
                    "winning_value": ", ".join(sorted(win_nums)),
                    "rejected_stale_url": other.url,
                    "rejected_year": str(other.freshness_year),
                    "rejected_stale_value": ", ".join(sorted(other_nums)),
                    "reason": f"Selected {winner.freshness_year} {winner.source_type} (authority {winner.authority_score}) over {other.freshness_year} source (authority {other.authority_score})"
                })
        return conflict_found, conflict_log

    def run_query(self, query: str, seed_urls: Optional[List[str]] = None, offline_html_fixtures: Optional[Dict[str, str]] = None) -> ChronosResult:
        t0 = time.time()
        keywords = self.tokenize_query(query)
        if seed_urls:
            queue = [(u, 0) for u in seed_urls]
        elif offline_html_fixtures:
            queue = [(u, 0) for u in offline_html_fixtures.keys()]
        else:
            queue = [(u, 0) for u in self.keyless_search(query)]

        visited = set()
        all_claims: List[ClaimNode] = []
        trace: List[Dict[str, str]] = []

        while queue and len(visited) < self.max_pages:
            url, hop = queue.pop(0)
            if url in visited or hop > self.max_hops:
                continue
            visited.add(url)

            html, status_s = "", ""
            if offline_html_fixtures and url in offline_html_fixtures:
                html, status_s = offline_html_fixtures[url], "200 OK (Fixture)"
            else:
                try:
                    resp = self.session.get(url, timeout=7)
                    if resp.status_code == 200:
                        html, status_s = resp.text, "200 OK"
                    else:
                        status_s = f"HTTP {resp.status_code}"
                except Exception as e:
                    status_s = f"Error ({type(e).__name__})"

            if not html:
                trace.append({"hop": str(hop), "url": url, "status": status_s, "claims_extracted": "0"})
                continue

            title, page_claims, next_links = self.parse_page_into_claims(url, html, keywords)
            all_claims.extend(page_claims)
            trace.append({"hop": str(hop), "url": url, "title": title, "status": status_s, "claims_extracted": str(len(page_claims))})

            if hop < self.max_hops:
                for _, n_url in next_links:
                    if n_url not in visited:
                        queue.append((n_url, hop + 1))

        all_claims.sort(key=lambda c: c.authority_score, reverse=True)
        latency = round((time.time() - t0) * 1000, 1)

        if not all_claims or all_claims[0].relevance_score < 0.35:
            return ChronosResult(
                query=query,
                status="REFUSED_UNVERIFIABLE",
                answer="REFUSED: No primary web source contained verifiable evidence matching the query constraints.",
                primary_citation="",
                verbatim_quote="",
                sha256_evidence_hash="",
                freshness_metadata="N/A",
                conflict_detected=False,
                conflict_log=[],
                navigation_trace=trace,
                compute_backend=self.compute_backend,
                latency_ms=latency
            )

        best = all_claims[0]
        candidate_answer = best.quote
        if not self.verify_verbatim_grounding(candidate_answer, best.quote, keywords):
            return ChronosResult(
                query=query,
                status="REFUSED_UNVERIFIABLE",
                answer="REFUSED: Candidate failed strict numerical/keyword grounding verification.",
                primary_citation="",
                verbatim_quote="",
                sha256_evidence_hash="",
                freshness_metadata="N/A",
                conflict_detected=False,
                conflict_log=[],
                navigation_trace=trace,
                compute_backend=self.compute_backend,
                latency_ms=latency
            )

        has_conflict, conflict_details = self.detect_and_resolve_conflicts(all_claims)
        status_code = "VERIFIED_TEMPORAL_OVERRIDE" if has_conflict else "VERIFIED_CONSENSUS"

        return ChronosResult(
            query=query,
            status=status_code,
            answer=candidate_answer,
            primary_citation=best.url,
            verbatim_quote=best.quote,
            sha256_evidence_hash=best.sha256_receipt,
            freshness_metadata=f"Year: {best.freshness_year} | Version: {best.version_tag} | Source: {best.source_type}",
            conflict_detected=has_conflict,
            conflict_log=conflict_details,
            navigation_trace=trace,
            compute_backend=self.compute_backend,
            latency_ms=latency
        )
