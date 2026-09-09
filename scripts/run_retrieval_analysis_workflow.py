from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.processing.interpretation import build_retrieval_analysis

OUTPUT_DIR = Path("data/retrieval_analysis")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retrieval-grounded Phase 12 analysis over the real Phase 10 index")
    parser.add_argument("--query", required=True, help="Natural-language query to execute against the real Qdrant-backed semantic index")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved regions to interpret")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    analysis = build_retrieval_analysis(args.query, top_k=args.top_k)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report_path = OUTPUT_DIR / "retrieval_analysis.json"
    report_path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")

    status_path = OUTPUT_DIR / "retrieval_analysis_report.json"
    status_path.write_text(json.dumps({
        "status": analysis["status"],
        "query": analysis["query"],
        "top_k": analysis["top_k"],
        "result_count": len(analysis["results"]),
        "output": str(report_path),
        "timestamp": analysis["query_timestamp"],
    }, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": analysis["status"],
        "query": analysis["query"],
        "top_k": analysis["top_k"],
        "result_count": len(analysis["results"]),
        "output": str(report_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
