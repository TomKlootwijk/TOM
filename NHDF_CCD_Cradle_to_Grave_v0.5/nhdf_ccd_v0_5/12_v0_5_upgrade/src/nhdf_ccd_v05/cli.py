from __future__ import annotations

import argparse
import json
from pathlib import Path
from .batch import evaluate_queries
from .corpus import corpus_statistics, load_sample_queries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NHDF-CCD v0.5 reference tools")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("corpus", help="parse and evaluate a Sample-Queries CSV")
    p.add_argument("query_type", choices=["vertex-face", "edge-edge"])
    p.add_argument("csv")
    p.add_argument("--limit", type=int)
    p.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "corpus":
        q = load_sample_queries(args.csv, args.query_type)
        summary, records = evaluate_queries(q, limit=args.limit)
        payload = {"corpus": corpus_statistics(q), "evaluation": summary.to_dict(), "records": records}
        text = json.dumps(payload, indent=2, sort_keys=True)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
