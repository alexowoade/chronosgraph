from engine.extract import ClaimNode
from engine.pipeline import ChronosResult, ChronosGraphROCmAgent

__all__ = ["ClaimNode", "ChronosResult", "ChronosGraphROCmAgent"]

if __name__ == "__main__":
    import argparse
    import json
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description="ChronosGraph CLI — Temporal Web Verification Engine on AMD ROCm")
    parser.add_argument("--query", "-q", type=str, required=True, help="Natural language question")
    parser.add_argument("--url", "-u", type=str, nargs="*", default=None, help="Optional starting seed URLs")
    args = parser.parse_args()

    cli_agent = ChronosGraphROCmAgent()
    result = cli_agent.run_query(query=args.query, seed_urls=args.url)
    print(json.dumps(asdict(result), indent=2))
