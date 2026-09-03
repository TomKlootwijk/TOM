from __future__ import annotations

import argparse
import json
from pathlib import Path

from tomagi.canonical import attach_hash, canonical_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach canonical definition hashes to a literal TOMAGI source")
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("program source must be an object")
    definitions = source.get("definitions", [])
    if not isinstance(definitions, list):
        raise ValueError("definitions must be an array")
    output = dict(source)
    output["definitions"] = [attach_hash({k: v for k, v in definition.items() if k != "content_hash"}) for definition in definitions]
    destination = Path(args.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
