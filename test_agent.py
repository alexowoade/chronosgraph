from agent import ChronosGraphROCmAgent
from api import health, retrieve, RetrieveRequest

TEMPORAL_CONFLICT_WEB = {
    "https://docs.amd-cloud.example/index.html": """
        <html><head><title>AMD Instinct Documentation Portal</title></head>
        <body>
            <p>Browse official hardware specifications and historical archives.</p>
            <a href="https://docs.amd-cloud.example/archive-2023-specs.html">Archived 2023 Preview Specs</a>
            <a href="https://docs.amd-cloud.example/current-2026-specs.html">Official 2026 Production Spec Sheet</a>
            <a href="https://docs.amd-cloud.example/support.html">Enterprise Support & JSON-LD</a>
        </body></html>
    """,
    "https://docs.amd-cloud.example/archive-2023-specs.html": """
        <html><head><title>2023 Early Preview</title>
        <meta property="article:modified_time" content="2023-06-15" /></head>
        <body>
            <p>In the 2023 v1.0 early preview, the accelerator memory capacity was 128 GB HBM3 with 4.0 TB/s bandwidth.</p>
        </body></html>
    """,
    "https://docs.amd-cloud.example/current-2026-specs.html": """
        <html><head><title>2026 Official Production Specs</title>
        <meta property="article:modified_time" content="2026-09-01" /></head>
        <body>
            <table>
                <tr><th>Model</th><th>Memory Capacity</th><th>Peak Bandwidth</th><th>Release</th></tr>
                <tr><td>AMD Instinct MI300X Production</td><td>192 GB HBM3</td><td>5.3 TB/s</td><td>2026 v2.4</td></tr>
            </table>
        </body></html>
    """,
    "https://docs.amd-cloud.example/support.html": """
        <html><head><title>AMD Support</title>
        <script type="application/ld+json">
        {"@type": "Organization", "name": "AMD ROCm Enterprise Support", "email": "rocm-support@amd.example.com"}
        </script></head>
        <body><p>Contact our team.</p></body></html>
    """
}

def test_01_temporal_conflict_override():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    res = agent.run_query(
        query="What is the HBM3 memory capacity and bandwidth of the AMD Instinct MI300X?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB
    )
    assert res.status == "VERIFIED_TEMPORAL_OVERRIDE"
    assert "192 GB" in res.answer
    assert res.primary_citation == "https://docs.amd-cloud.example/current-2026-specs.html"
    assert res.conflict_detected is True
    assert len(res.conflict_log) >= 1

def test_02_sha256_receipt_generated():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    res = agent.run_query(
        query="What is the HBM3 memory capacity of AMD Instinct MI300X?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB
    )
    assert len(res.sha256_evidence_hash) == 16

def test_03_cite_or_refuse_hallucination_trap():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    res = agent.run_query(
        query="What is the battery life of the Quantum Flux Toaster 9000?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB
    )
    assert res.status == "REFUSED_UNVERIFIABLE"
    assert res.primary_citation == ""

def test_04_unverified_number_rejected():
    agent = ChronosGraphROCmAgent()
    assert agent.verify_verbatim_grounding("Capacity is 512 GB", "Capacity is 192 GB", ["capacity", "gb"]) is False

def test_05_verified_number_accepted():
    agent = ChronosGraphROCmAgent()
    assert agent.verify_verbatim_grounding("Capacity is 192 GB", "Capacity is 192 GB HBM3", ["capacity", "gb"]) is True

def test_06_page_budget_enforced():
    agent = ChronosGraphROCmAgent(max_pages=1, max_hops=2)
    res = agent.run_query(
        query="What is the memory capacity?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB
    )
    assert len(res.navigation_trace) == 1

def test_07_json_ld_extraction():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    res = agent.run_query(
        query="What is the email for AMD ROCm Enterprise Support?",
        seed_urls=["https://docs.amd-cloud.example/index.html"],
        offline_html_fixtures=TEMPORAL_CONFLICT_WEB
    )
    assert res.status.startswith("VERIFIED")
    assert "rocm-support@amd.example.com" in res.answer

def test_08_row_header_table_extraction():
    fixtures = {
        "https://spec.example/row-th.html": """
        <html><body><table>
            <tr><th scope="row">Thermal Design Power</th><td>750 W</td></tr>
        </table></body></html>
        """
    }
    agent = ChronosGraphROCmAgent()
    res = agent.run_query("What is the Thermal Design Power?", seed_urls=["https://spec.example/row-th.html"], offline_html_fixtures=fixtures)
    assert res.status.startswith("VERIFIED")
    assert "750 W" in res.answer

def test_09_broken_url_graceful_handling():
    agent = ChronosGraphROCmAgent(max_pages=2, max_hops=1)
    res = agent.run_query("What is the memory capacity?", seed_urls=["https://invalid.domain.example.test/404"])
    assert res.status == "REFUSED_UNVERIFIABLE"

def test_10_fastapi_health_endpoint():
    resp = health()
    assert resp["status"] == "ok"
    assert "compute_backend" in resp
