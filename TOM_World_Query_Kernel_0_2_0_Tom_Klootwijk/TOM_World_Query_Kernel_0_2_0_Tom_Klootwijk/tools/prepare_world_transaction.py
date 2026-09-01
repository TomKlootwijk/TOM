from __future__ import annotations

import argparse
import json
from pathlib import Path

from tom_world.canonical import attach_hash, digest_file
from tom_world.records import validate_record
from tom_world.store import TRANSACTION_SCHEMA
from tom_world.seed import verify_seed_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash literal world records and blob boundaries")
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--seed", required=True)
    parser.add_argument("--base-commit", default=None)
    parser.add_argument("--sequence", type=int, default=0)
    args = parser.parse_args()

    source_path = Path(args.source)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    identity = verify_seed_file(args.seed)
    records = []
    for raw in source.get("records", []):
        record = attach_hash({key: value for key, value in raw.items() if key != "content_hash"})
        validate_record(record)
        records.append(record)
    blobs = []
    for raw in source.get("blobs", []):
        path = source_path.parent / raw["path"]
        blobs.append({
            "id": raw["id"],
            "path": raw["path"],
            "media_type": raw.get("media_type", "application/octet-stream"),
            "sha256": digest_file(path),
        })
    transaction = attach_hash({
        "schema": TRANSACTION_SCHEMA,
        "seed_sha256": "sha256:" + identity.sha256,
        "base_commit": args.base_commit,
        "sequence": args.sequence,
        "message": str(source.get("message", "")),
        "records": records,
        "blobs": blobs,
        "provenance": dict(source.get("provenance", {})),
    })
    destination = Path(args.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(transaction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
