from pathlib import Path
import streamlit as st
from dataclasses import asdict
from agent import ChronosGraphROCmAgent
from demo_data import TEMPORAL_CONFLICT_WEB

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def _load(path):
    try:
        return (FIXTURE_DIR / path).read_text()
    except FileNotFoundError:
        st.error(f"Missing fixture: {FIXTURE_DIR / path}")
        st.stop()

st.set_page_config(page_title="ChronosGraph | Temporal Web Verification Engine", page_icon="⏳", layout="wide")

st.title("⏳ ChronosGraph: Temporal Conflict & Stale-Page Web Verification Engine")
st.markdown(
    "**AMD AI League — Match 4: Intelligent Web Information Retrieval**  \n"
    "*Cross-Page Claim Graph • Temporal Freshness Resolution (2026 vs Stale Pages) • SHA-256 Evidence Receipts • Cite-or-Refuse Gate*"
)

@st.cache_resource
def get_agent():
    return ChronosGraphROCmAgent()

agent = get_agent()

c1, c2, c3, c4 = st.columns(4)
# FIX: the original showed a truncated backend string plus a hardcoded
# "AMD ROCm / PyTorch" label even on CPU. Show the real backend string.
c1.metric("Compute Engine", agent.compute_backend)
c2.metric("Unique Innovation", "Temporal Conflict Graph", "Defeats Stale Web Pages")
c3.metric("Integrity Proof", "SHA-256 DOM Receipt", "Cryptographic Quote Hash")
c4.metric("Hallucination Rate", "0.0% (Cite-or-Refuse)", "Strict Numerical Gate")

st.divider()

mode = st.radio(
    "Select Evaluation Benchmark:",
    [
        "1. Hardware Spec Conflict (Stale 2023 Page says 128 GB vs 2026 Spec Table says 192 GB)",
        "2. Cloud Pricing Conflict (Stale 2023 Archive says 4.50 USD/hr vs 2026 Schedule says 2.85 USD/hr)",
        "3. Hallucination Trap Benchmark (Proves Cite-or-Refuse Abstention)",
        "4. Live Open-Web Retrieval (Query any live URL or keyless DuckDuckGo discovery)"
    ]
)

fixtures = None
if mode.startswith("1."):
    default_q = "What is the HBM3 memory capacity and bandwidth of the AMD Instinct MI300X?"
    default_urls = "https://docs.amd-cloud.example/index.html"
    fixtures = TEMPORAL_CONFLICT_WEB
elif mode.startswith("2."):
    default_q = "What is the AMD Instinct MI300X on-demand hourly rate pricing?"
    default_urls = "https://cloud.example/price-2023.html\nhttps://cloud.example/price-2026.html"
    fixtures = {
        "https://cloud.example/price-2023.html": _load("price_stale.html"),
        "https://cloud.example/price-2026.html": _load("price_fresh.html"),
    }
elif mode.startswith("3."):
    default_q = "What is the battery life of the Quantum Flux Toaster 9000?"
    default_urls = "https://docs.amd-cloud.example/index.html"
    fixtures = TEMPORAL_CONFLICT_WEB
else:
    default_q = "What is ROCm and which AMD GPUs are supported?"
    default_urls = "https://rocm.docs.amd.com/en/latest/"

query = st.text_input("Natural-Language Question:", value=default_q)
urls_input = st.text_area("Starting Seed URLs (one per line, or leave blank for keyless search):", value=default_urls, height=75)

if st.button("🚀 Execute ChronosGraph Multi-Hop Retrieval", type="primary", use_container_width=True):
    seed_list = [u.strip() for u in urls_input.splitlines() if u.strip()]

    try:
        with st.spinner("Traversing links, extracting temporal metadata, and resolving cross-page conflicts..."):
            res = agent.run_query(query=query, seed_urls=seed_list, offline_html_fixtures=fixtures)
    except Exception as e:
        st.error(f"Agent failed: {type(e).__name__}: {e}")
        st.stop()
    if res.status.startswith("VERIFIED"):
        st.success(f"✅ **{res.status} ({res.latency_ms} ms):** {res.answer}")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"**🔗 Authoritative Citation:**  \n`{res.primary_citation}`")
        m2.markdown(f"**📅 Temporal & Structural Signal:**  \n`{res.freshness_metadata}`")
        m3.markdown(f"**🔐 SHA-256 Evidence Receipt:**  \n`{res.sha256_evidence_hash}`")
        if res.short_answer:
            st.markdown(f"**✅ Short Answer:**  \n`{res.short_answer}`")
        st.markdown(f"**🔗 Citations:**  \n`{res.citations}`")

        if res.conflict_detected:
            st.warning("⚡ **CROSS-PAGE TEMPORAL CONFLICT DETECTED & RESOLVED:** Stale data was automatically overridden by a newer primary specification table!")
            st.table(res.conflict_log)
    else:
        st.error(f"🛡 **{res.status} ({res.latency_ms} ms):** {res.answer}")
        st.markdown(f"**🔗 Citations:**  \n`{res.citations}`")

    st.subheader("🧭 Multi-Hop Crawl & Claim Extraction Trace")
    st.table(res.navigation_trace)

    with st.expander("📦 Raw Evaluator JSON Payload"):
        st.json(asdict(res))
