import time
from pathlib import Path
from agent import ChronosGraphROCmAgent
from test_agent import TEMPORAL_CONFLICT_WEB

FIXTURE_DIR = Path(__file__).parent / "fixtures"

BENCHMARK_CASES = [
    {
        "name": "Case 1: 2026 Spec Table vs 2023 Stale Archive (Memory)",
        "query": "What is the HBM3 memory capacity of the AMD Instinct MI300X?",
        "expected_status": "VERIFIED_TEMPORAL_OVERRIDE",
        "must_contain": "192 GB",
        "fixtures": TEMPORAL_CONFLICT_WEB,
        "seeds": ["https://docs.amd-cloud.example/index.html"]
    },
    {
        "name": "Case 2: 2026 Spec Table vs 2023 Stale Archive (Bandwidth)",
        "query": "What is the peak bandwidth of the AMD Instinct MI300X?",
        "expected_status": "VERIFIED_TEMPORAL_OVERRIDE",
        "must_contain": "5.3 TB/s",
        "fixtures": TEMPORAL_CONFLICT_WEB,
        "seeds": ["https://docs.amd-cloud.example/index.html"]
    },
    {
        "name": "Case 3: 2026 Cloud Pricing Schedule vs 2023 Archive",
        "query": "What is the AMD Instinct MI300X on-demand hourly rate pricing?",
        "expected_status": "VERIFIED_TEMPORAL_OVERRIDE",
        "must_contain": "$2.85",
        "fixtures": {
            "https://cloud.example/price-2023.html": (FIXTURE_DIR / "price_stale.html").read_text(),
            "https://cloud.example/price-2026.html": (FIXTURE_DIR / "price_fresh.html").read_text(),
        },
        "seeds": None
    },
    {
        "name": "Case 4: JSON-LD Structured Contact Extraction",
        "query": "What is the email for AMD ROCm Enterprise Support?",
        "expected_status": "VERIFIED_CONSENSUS",
        "must_contain": "rocm-support@amd.example.com",
        "fixtures": TEMPORAL_CONFLICT_WEB,
        "seeds": ["https://docs.amd-cloud.example/index.html"]
    },
    {
        "name": "Case 5: Hallucination Trap (Non-existent Hardware)",
        "query": "What is the battery life of the Quantum Flux Toaster 9000?",
        "expected_status": "REFUSED_UNVERIFIABLE",
        "must_contain": "REFUSED",
        "fixtures": TEMPORAL_CONFLICT_WEB,
        "seeds": ["https://docs.amd-cloud.example/index.html"]
    },
    {
        "name": "Case 6: Hallucination Trap (Fabricated Pricing Query)",
        "query": "What is the monthly subscription fee for Chronos Satellite Internet?",
        "expected_status": "REFUSED_UNVERIFIABLE",
        "must_contain": "REFUSED",
        "fixtures": TEMPORAL_CONFLICT_WEB,
        "seeds": ["https://docs.amd-cloud.example/index.html"]
    }
]

def run_benchmarks():
    agent = ChronosGraphROCmAgent(max_pages=5, max_hops=2)
    passed = 0
    t0 = time.time()
    print("=" * 76)
    print(f"ChronosGraph Evaluation Suite | Backend: {agent.compute_backend}")
    print("=" * 76)

    for case in BENCHMARK_CASES:
        res = agent.run_query(
            query=case["query"],
            seed_urls=case["seeds"],
            offline_html_fixtures=case["fixtures"]
        )
        ok = (res.status == case["expected_status"]) and (case["must_contain"] in res.answer)
        passed += int(ok)
        badge = "PASS" if ok else "FAIL"
        print(f"[{badge}] {case['name']} -> {res.status} ({res.latency_ms} ms)")

    total_ms = round((time.time() - t0) * 1000, 2)
    # FIX: the original printed a hardcoded "(100.0%)" even when cases
    # failed. Compute the real percentage from passed/total.
    pct = round(passed / len(BENCHMARK_CASES) * 100, 1) if BENCHMARK_CASES else 0.0
    print("=" * 76)
    print(f"Benchmark Score: {passed}/{len(BENCHMARK_CASES)} ({pct}%) | Total Time: {total_ms} ms")
    print("=" * 76)
    assert passed == len(BENCHMARK_CASES)

if __name__ == "__main__":
    run_benchmarks()
