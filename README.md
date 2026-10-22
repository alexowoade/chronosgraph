# ⏳ ChronosGraph: Temporal Conflict & Web Verification Engine on AMD ROCm

Built for **AMD AI League — Match 4: Intelligent Web Information Retrieval**.

**ChronosGraph** is an autonomous multi-hop web information retrieval and verification engine built for **AMD ROCm™ GPUs**. Unlike standard web scrapers that blindly return the first matching snippet, ChronosGraph builds a **Cross-Page Claim Graph** across visited URLs, extracts **temporal freshness signals** (`article:modified_time`, ISO dates, release years, semantic version tags), automatically resolves contradictions between stale and current web pages, and issues a **tamper-evident SHA-256 DOM receipt** for every verified answer.

## ✨ Key Innovations & Modular Architecture (`engine/`)
- **`engine/dates.py` (Temporal Signal Extraction):** Extracts full ISO dates (`YYYY-MM-DD`), modification years, and v-prefixed semantic version tags to defeat stale web pages.
- **`engine/extract.py` (Structural DOM & Schema Claim Graph):** Prioritizes HTML `<table>` specification sheets (including `<th scope="row">`) and `application/ld+json` schemas over unstructured prose.
- **`engine/conflict.py` (Cross-Page Conflict Resolution & Cite-or-Refuse Gate):** Compares competing claims across URLs, overrides outdated values, and enforces verbatim numerical grounding.
- **`engine/receipt.py` (Cryptographic Evidence Receipts):** Issues a 16-character truncated SHA-256 hash (`url || verbatim_quote`) proving primary-source integrity.
- **`engine/device.py` (AMD ROCm Integration):** Runs inside `rocm/pytorch:latest` with automatic `torch.version.hip` detection, and honestly reports CPU when no GPU is present.

## 🚀 Quickstart

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the 13-test automated verification suite
pytest -v

# Run the 6-case temporal & hallucination benchmark suite
python3 benchmark.py

# Launch the interactive Streamlit UI
streamlit run app.py

# Launch the FastAPI REST server on port 8000 (separate process)
uvicorn api:app --host 0.0.0.0 --port 8000
```

## Honest scope

This version is a deterministic retrieval and verification engine: it
fetches pages, extracts claims, resolves temporal conflicts, and returns
a verbatim quote with a citation and a receipt. It does not load a
language model and does not generate new text. The `model_id` in
`ChronosGraphROCmAgent` is reserved for a future ROCm inference step.
