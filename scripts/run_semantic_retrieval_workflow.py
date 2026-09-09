from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.processing.retrieval.query import execute_query


OUTPUT_DIR = Path("data/retrieval")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semantic retrieval over the Phase 10 region vector index")
    parser.add_argument("--query", required=True, help="Natural-language query to embed and search")
    parser.add_argument("--top-k", type=int, default=5, help="Number of nearest neighbours to retrieve")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    result = execute_query(args.query, top_k=args.top_k)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "retrieval_report.json"
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "query": result["query"],
        "top_k": result["top_k"],
        "result_count": len(result["results"]),
        "collection_name": result["collection_name"],
        "embedding_model": result["embedding_model"],
        "report": str(report_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
