import hashlib

def compute_sha256_receipt(url: str, quote: str) -> str:
    # FIX: the original docstring said "16-byte". hexdigest()[:16] is
    # 16 hex *characters* = 64 bits = 8 bytes. The function itself is
    # fine (tests expect length 16); only the label was wrong.
    """Generates a 16-character truncated SHA-256 receipt for a quote."""
    payload = f"{url.strip()}||{quote.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
