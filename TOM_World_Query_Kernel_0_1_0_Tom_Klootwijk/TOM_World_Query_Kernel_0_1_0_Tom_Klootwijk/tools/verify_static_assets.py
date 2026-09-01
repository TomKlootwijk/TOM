from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world.canonical import verify_hash
from tom_world.records import validate_record
from tom_world.seed import verify_seed_file


def main() -> int:
    identity = verify_seed_file(ROOT / "TOM_seed_genome_2026-09-01.txt")
    required = [
        "AGENTS.md",
        "docs/ROADMAP.md",
        "docs/ROADMAP_AND_STARTER.md",
        "docs/IMPLEMENTATION_STATUS.md",
        "docs/ARCHITECTURE.md",
        "docs/QUERY_API.md",
        "docs/AGI_GAP_MATRIX.md",
        "docs/NEXT_EXPERIMENTS.md",
        "spec/TOM_WORLD_QUERY_KERNEL_0_1.md",
        "spec/world/tom_world_record.schema.json",
        "spec/world/tom_world_source.schema.json",
        "spec/world/tom_world_transaction.schema.json",
        "spec/world/tom_event_certificate.schema.json",
        "spec/world/tom_literal_artifact_source.schema.json",
        "sources/TOMAGI_1_0_Tom_Klootwijk.pdf",
        "sources/TOM_seeded_substrate_paradigm_2026-09-01.pdf",
    ]
    missing = [relative for relative in required if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError("missing static assets: " + ", ".join(missing))

    source = json.loads((ROOT / "examples/world_counter/world_source.json").read_text(encoding="utf-8"))
    if source.get("schema") != "TOM-WORLD-SOURCE-0.1":
        raise ValueError("counter world source schema mismatch")
    ids = [record["id"] for record in source["records"]]
    if len(ids) != len(set(ids)):
        raise ValueError("counter world source contains duplicate IDs")

    transaction = json.loads((ROOT / "examples/world_counter/initial_transaction.json").read_text(encoding="utf-8"))
    if not verify_hash(transaction):
        raise ValueError("counter initial transaction content hash mismatch")
    for record in transaction["records"]:
        validate_record(record)

    artifact_source = json.loads((ROOT / "examples/artifacts/roadmap_and_starter.source.json").read_text(encoding="utf-8"))
    if not verify_hash(artifact_source):
        raise ValueError("roadmap artifact source content hash mismatch")
    for definition in artifact_source["definitions"]:
        validate_record(definition)

    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema is not None:
        record_schema = json.loads((ROOT / "spec/world/tom_world_record.schema.json").read_text())
        transaction_schema = json.loads((ROOT / "spec/world/tom_world_transaction.schema.json").read_text())
        transaction_schema["properties"]["records"]["items"] = record_schema
        jsonschema.Draft202012Validator(transaction_schema).validate(transaction)
        event_schema = json.loads((ROOT / "spec/world/tom_event_certificate.schema.json").read_text())
        event = json.loads((ROOT / "validation/next_event.json").read_text())
        jsonschema.Draft202012Validator(event_schema).validate(event)
        artifact_schema = json.loads((ROOT / "spec/world/tom_literal_artifact_source.schema.json").read_text())
        artifact_schema["properties"]["definitions"]["items"] = record_schema
        jsonschema.Draft202012Validator(artifact_schema).validate(artifact_source)

    result = {
        "status": "pass",
        "seed": identity.as_record(),
        "required_static_assets": len(required),
        "counter_source_records": len(source["records"]),
        "transaction_records": len(transaction["records"]),
        "artifact_definitions": len(artifact_source["definitions"]),
        "jsonschema_available": jsonschema is not None,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
