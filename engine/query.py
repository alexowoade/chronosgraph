import re
from typing import List

STOPWORDS = {
    "what","is","the","of","in","for","to","a","an","and","or","on","at","by",
    "with","from","how","much","many","does","do","can","you","find","tell",
    "me","current","latest","who","where","when","official","which","are"
}

def tokenize_query(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-zA-Z0-9_.\-]+", text.lower()) if w not in STOPWORDS and len(w) > 1]

def score_passage(text: str, keywords: List[str]) -> float:
    if not keywords:
        return 0.0
    lower_t = text.lower()
    hits = sum(1 for kw in keywords if kw in lower_t)
    if hits == 0:
        return 0.0
    # FIX: "tb/s" must come BEFORE "tb" in the alternation, otherwise
    # "5.3 TB/s" matches just "tb" first. Same idea already applied
    # to "ms" before "s". Order inside an alternation matters.
    metric_bonus = 0.35 if re.search(
        r"(\d+(\.\d+)?\s*(gb|mb|tb/s|tb|ms|s|w|ghz|mhz|%|usd|\$|€|cores)|v\d+\.\d+|202\d-\d{2}-\d{2})",
        lower_t
    ) else 0.0
    return round((hits / len(keywords)) + metric_bonus, 4)
