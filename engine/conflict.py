import re
from typing import List, Dict, Tuple, Set
from engine.extract import ClaimNode

UNIT_PATTERN = r"(?:\$\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:gb|tb/s|tb|mb|w|ghz|mhz|ms|%|usd|\$|€|cores)\b|\bv\d+\.\d+(?:\.\d+)?\b|\b202\d-\d{2}-\d{2}\b)"

def _units_in(quote: str) -> Set[str]:
    """The unit types a quote talks about: gb, $, v-version, date, ..."""
    q = quote.lower()
    units = set()
    for unit in ["gb", "tb/s", "tb", "mb", "w", "ghz", "mhz", "ms", "%", "usd", "cores"]:
        if re.search(r"\d+\s*" + re.escape(unit) + r"\b", q):
            units.add(unit)
    if "$" in q:
        units.add("$")
    if re.search(r"\bv\d+\.\d+", q):
        units.add("version")
    if re.search(r"\b202\d-\d{2}-\d{2}\b", q):
        units.add("date")
    return units

def verify_verbatim_grounding(candidate: str, quote: str, keywords: List[str]) -> bool:
    """
    Strict Cite-or-Refuse Gate, fixed in two ways:
    1. Numbers are compared as whole tokens, not substrings. The
       original `"2" in "192 GB"` check would accept a candidate
       number 2 just because 192 contains a 2.
    2. `v2.4` is now recognised: the original \\b-anchored pattern
       could not match the 2 in "v2.4" (v and 2 are both word chars,
       so there is no word boundary between them), so version
       numbers were never checked at all.
    NOTE on the pipeline: this gate is meaningful for a *generated*
    answer. In this retrieval-only design the pipeline's answer IS
    the quote, so checking the quote against itself can never fail.
    The real guarantee here is "answer = verbatim quote, never
    generated text" plus the 0.35 relevance floor in pipeline.py.
    Do not claim the gate alone stops hallucination.
    """
    if not candidate or not quote:
        return False
    quote_numbers = set(re.findall(r"\d+(?:\.\d+)?", quote))
    for num in re.findall(r"\d+(?:\.\d+)?", candidate):
        if num not in quote_numbers:
            return False
    matched = [kw for kw in keywords if kw in quote.lower()]
    return len(matched) >= max(1, int(len(keywords) * 0.3))

def detect_and_resolve_conflicts(claims: List[ClaimNode]) -> Tuple[bool, List[Dict[str, str]]]:
    """Compares top claims across pages to identify stale/conflicting values.

    FIX — false positives: the original flagged ANY difference in
    numeric sets as a conflict. A memory claim (192 GB) vs a TDP
    claim (750 W) in the top 6 was logged as a "temporal conflict"
    even though they are about different things. Now the two quotes
    must share at least one unit type (gb, $, version, date, ...)
    before they count as conflicting.
    """
    if len(claims) < 2:
        return False, []
    winner = claims[0]
    win_nums = set(re.findall(UNIT_PATTERN, winner.quote.lower()))
    win_units = _units_in(winner.quote)
    conflict_log = []
    conflict_found = False

    for other in claims[1:6]:
        if other.url == winner.url and other.quote == winner.quote:
            continue
        other_nums = set(re.findall(UNIT_PATTERN, other.quote.lower()))
        if win_nums and other_nums and win_nums != other_nums:
            if not (win_units & _units_in(other.quote)):
                continue
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
