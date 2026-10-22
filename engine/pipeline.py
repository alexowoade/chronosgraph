import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from engine.device import detect_rocm_device
from engine.query import tokenize_query
from engine.fetch import create_session, keyless_search
from engine.extract import ClaimNode, parse_page_into_claims
from engine.conflict import verify_verbatim_grounding, detect_and_resolve_conflicts

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

    Honest scope note: this is a deterministic retrieval + verification
    engine. model_id is kept for API compatibility with the future
    ROCm generation step, but NO model is loaded and NO text is
    generated here — the answer is always a verbatim quote from a
    fetched page. Do not describe this version as "running Qwen on
    ROCm" until a real inference step is added.
    """
    def __init__(self, model_id: str = "Qwen/Qwen2.5-1.5B-Instruct", max_pages: int = 6, max_hops: int = 2):
        self.model_id = model_id  # reserved, not loaded (see docstring)
        self.max_pages = max_pages
        self.max_hops = max_hops
        self.session = create_session()
        self.compute_backend = detect_rocm_device()

    def verify_verbatim_grounding(self, candidate: str, quote: str, keywords: List[str]) -> bool:
        return verify_verbatim_grounding(candidate, quote, keywords)

    def run_query(
        self,
        query: str,
        seed_urls: Optional[List[str]] = None,
        offline_html_fixtures: Optional[Dict[str, str]] = None
    ) -> ChronosResult:
        t0 = time.time()
        keywords = tokenize_query(query)
        # FIX — offline queue: the original used seeds if given, else
        # fixtures, so fixture pages that were not linked from a seed
        # were silently never visited. Now seeds come first, then any
        # remaining fixture URLs, in fixture order, all subject to
        # max_pages. A queued-set also stops the same link being
        # enqueued twice from different pages.
        if seed_urls:
            queue = [(u, 0) for u in seed_urls]
        elif offline_html_fixtures:
            queue = [(u, 0) for u in offline_html_fixtures.keys()]
        else:
            queue = [(u, 0) for u in keyless_search(self.session, query)]
        queued = {u for u, _ in queue}
        if offline_html_fixtures and seed_urls:
            for u in offline_html_fixtures.keys():
                if u not in queued:
                    queue.append((u, 0))
                    queued.add(u)

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
                # FIX: always include "title" (empty on failure) so the
                # Streamlit trace table has the same columns every row.
                trace.append({"hop": str(hop), "url": url, "title": "", "status": status_s, "claims_extracted": "0"})
                continue

            title, page_claims, next_links = parse_page_into_claims(url, html, keywords)
            all_claims.extend(page_claims)
            trace.append({"hop": str(hop), "url": url, "title": title, "status": status_s, "claims_extracted": str(len(page_claims))})

            if hop < self.max_hops:
                for _, n_url in next_links:
                    if n_url not in visited and n_url not in queued:
                        queue.append((n_url, hop + 1))
                        queued.add(n_url)

        all_claims.sort(key=lambda c: (c.authority_score, c.iso_date), reverse=True)
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
        if not verify_verbatim_grounding(candidate_answer, best.quote, keywords):
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

        has_conflict, conflict_details = detect_and_resolve_conflicts(all_claims)
        status_code = "VERIFIED_TEMPORAL_OVERRIDE" if has_conflict else "VERIFIED_CONSENSUS"

        iso_display = best.iso_date if best.iso_date else "no ISO date"
        return ChronosResult(
            query=query,
            status=status_code,
            answer=candidate_answer,
            primary_citation=best.url,
            verbatim_quote=best.quote,
            sha256_evidence_hash=best.sha256_receipt,
            freshness_metadata=f"Year: {best.freshness_year} ({iso_display}) | Version: {best.version_tag} | Source: {best.source_type}",
            conflict_detected=has_conflict,
            conflict_log=conflict_details,
            navigation_trace=trace,
            compute_backend=self.compute_backend,
            latency_ms=latency
        )
