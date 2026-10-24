"""New-field tests for Patch 3: short answer and citations list.

Run on Ubuntu, in ~/chronosgraph with the venv active:
    python3 -m pytest test_short_citations.py -q

These tests do NOT change test_agent.py. They check that:
- Mode 1 gives short answer "192 GB, 5.3 TB/s, v2.4" and citations
  as a one-item list, while primary_citation stays the same string.
- Mode 2 gives short answer "$2.85, v2.0".
- A refusal gives short answer "" and citations [], while
  primary_citation stays "" (the existing test_03 assertion).
"""
from pathlib import Path
from agent import ChronosGraphROCmAgent
from demo_data import TEMPORAL_CONFLICT_WEB

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_short_answer_and_citations_mode1():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    res = agent.run_query(
        query="What is the HBM3 memory capacity and bandwidth of the AMD Instinct MI300X?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB,
    )
    assert res.short_answer == "192 GB, 5.3 TB/s, v2.4"
    assert res.citations == ["https://docs.amd-cloud.example/current-2026-specs.html"]
    assert res.primary_citation == "https://docs.amd-cloud.example/current-2026-specs.html"


def test_short_answer_and_citations_mode2():
    fixtures = {
        "https://cloud.example/price-2023.html": (FIXTURE_DIR / "price_stale.html").read_text(),
        "https://cloud.example/price-2026.html": (FIXTURE_DIR / "price_fresh.html").read_text(),
    }
    agent = ChronosGraphROCmAgent()
    res = agent.run_query(
        query="What is the AMD Instinct MI300X hourly rate pricing?",
        offline_html_fixtures=fixtures,
    )
    assert res.short_answer == "$2.85, v2.0"
    assert res.citations == ["https://cloud.example/price-2026.html"]


def test_refusal_citations_empty_list():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    res = agent.run_query(
        query="What is the battery life of the Quantum Flux Toaster 9000?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB,
    )
    assert res.status == "REFUSED_UNVERIFIABLE"
    assert res.short_answer == ""
    assert res.citations == []
    assert res.primary_citation == ""
