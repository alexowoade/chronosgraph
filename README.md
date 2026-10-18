# ⏳ ChronosGraph: Temporal Conflict & Web Verification Engine on AMD ROCm

Built for **AMD AI League — Match 4: Intelligent Web Information Retrieval**.

**ChronosGraph** is an autonomous multi-hop web information retrieval and verification engine built for **AMD ROCm™ GPUs**. Unlike standard web scrapers that blindly return the first matching snippet, ChronosGraph builds a **Cross-Page Claim Graph** across visited URLs, extracts **temporal freshness signals** (`article:modified_time`, release years, semantic version tags), automatically resolves contradictions between stale and current web pages, and issues a **tamper-evident SHA-256 DOM receipt** for every verified answer.

## ✨ Key Innovations
1. **Cross-Page Temporal Conflict Resolution:** Detects when an archived/stale webpage contradicts a newer primary specification table (`<table>` or `JSON-LD`), overrides the outdated value, and outputs a transparent Conflict Resolution Matrix.
2. **Cryptographic Evidence Receipts (`SHA-256`):** Generates a 16-byte SHA-256 fingerprint (`url || verbatim_quote`) proving exact primary-source grounding.
3. **Strict Cite-or-Refuse Gate:** Every numerical value in a candidate answer must appear verbatim in the cited source passage, guaranteeing 0% hallucination.
4. **Native AMD ROCm + Zero-Cost Deterministic Core:** Runs inside the official `rocm/pytorch:latest` container with `torch.version.hip` detection and a sub-second deterministic CPU core requiring zero paid APIs.

## 🚀 Quickstart

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the automated verification & temporal conflict test suite
pytest -v

# Launch the interactive ChronosGraph Inspector UI
streamlit run app.py

# Or launch the FastAPI REST endpoint on port 8000
uvicorn api:app --host 0.0.0.0 --port 8000
```
