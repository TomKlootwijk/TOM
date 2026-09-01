from __future__ import annotations

"""Verify shipped 0.2 literal sources, schemas, indexes, and certificates."""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world.canonical import verify_hash
from tom_world.records import validate_record
from tom_world.seed import verify_seed_file
from tom_world.store import WorldStore


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def iter_plans(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("schema") == "TOM-QUERY-PLAN-0.2":
            yield value
        for child in value.values():
            yield from iter_plans(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_plans(child)


def main() -> int:
    identity = verify_seed_file(ROOT / "TOM_seed_genome_2026-09-01.txt")
    required = [
        "AGENTS.md",
        "README.md",
        "CHANGELOG.md",
        "NOTICE.md",
        "docs/ROADMAP.md",
        "docs/ROADMAP_AND_STARTER.md",
        "docs/IMPLEMENTATION_STATUS.md",
        "docs/ARCHITECTURE.md",
        "docs/QUERY_API.md",
        "docs/AGI_GAP_MATRIX.md",
        "docs/NEXT_EXPERIMENTS.md",
        "docs/INDEX_AND_QUERY_PLAN_PROFILE.md",
        "docs/CHECKPOINT_AND_AUDIT_PROFILE.md",
        "docs/BENCHMARK_10000.md",
        "docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md",
        "spec/TOM_WORLD_QUERY_KERNEL_0_1.md",
        "spec/TOM_WORLD_QUERY_KERNEL_0_2.md",
        "spec/world/tom_world_record.schema.json",
        "spec/world/tom_world_source.schema.json",
        "spec/world/tom_world_transaction.schema.json",
        "spec/world/tom_event_certificate.schema.json",
        "spec/world/tom_literal_artifact_source.schema.json",
        "spec/world/tom_world_indexes.schema.json",
        "spec/world/tom_query_plan.schema.json",
        "spec/world/tom_batch_query.schema.json",
        "spec/world/tom_audit_certificate.schema.json",
        "spec/world/tom_state_at_certificate_0_2.schema.json",
        "src/python/tom_world/indexes.py",
        "src/python/tom_world/planner.py",
        "src/python/tom_world/audit.py",
        "examples/index_benchmark/benchmark_spec.json",
        "examples/index_benchmark/initial_transaction.json",
        "examples/index_benchmark/checkpoint_transaction.json",
        "examples/index_benchmark/batch_requests.json",
        "sources/TOMAGI_1_0_Tom_Klootwijk.pdf",
        "sources/TOM_seeded_substrate_paradigm_2026-09-01.pdf",
    ]
    missing = [relative for relative in required if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError("missing static assets: " + ", ".join(missing))

    # 0.1 counter-world compatibility source.
    counter_source = load("examples/world_counter/world_source.json")
    if counter_source.get("schema") != "TOM-WORLD-SOURCE-0.1":
        raise ValueError("counter world source schema mismatch")
    ids = [record["id"] for record in counter_source["records"]]
    if len(ids) != len(set(ids)):
        raise ValueError("counter world source contains duplicate IDs")
    counter_transaction = load("examples/world_counter/initial_transaction.json")
    if not verify_hash(counter_transaction):
        raise ValueError("counter initial transaction content hash mismatch")
    for record in counter_transaction["records"]:
        validate_record(record)

    # Frozen 10,000-record benchmark sources.
    benchmark_spec = load("examples/index_benchmark/benchmark_spec.json")
    initial = load("examples/index_benchmark/initial_transaction.json")
    checkpoints = load("examples/index_benchmark/checkpoint_transaction.json")
    batch_requests = load("examples/index_benchmark/batch_requests.json")
    for name, value in (
        ("benchmark specification", benchmark_spec),
        ("initial transaction", initial),
        ("checkpoint transaction", checkpoints),
    ):
        if not verify_hash(value):
            raise ValueError(f"{name} content hash mismatch")
    if batch_requests.get("schema") != "TOM-BATCH-QUERY-REQUESTS-0.2" or batch_requests.get("version") != "0.2.0":
        raise ValueError("batch request source schema/version mismatch")
    all_benchmark_records = [*initial["records"], *checkpoints["records"]]
    if len(all_benchmark_records) != 10_000:
        raise ValueError(f"benchmark source contains {len(all_benchmark_records)} records, expected 10000")
    type_counts: Counter[str] = Counter()
    record_ids: set[str] = set()
    for record in all_benchmark_records:
        validate_record(record)
        if record["id"] in record_ids:
            raise ValueError(f"duplicate benchmark record ID: {record['id']}")
        record_ids.add(record["id"])
        type_counts[record["record_type"]] += 1
    expected_counts = {
        "definition": 1,
        "support": 16,
        "compatibility": 4,
        "instance": 100,
        "relation": 9600,
        "observation": 269,
        "checkpoint": 10,
    }
    if dict(sorted(type_counts.items())) != dict(sorted(expected_counts.items())):
        raise ValueError(f"benchmark type counts differ: {dict(type_counts)}")
    if len(batch_requests.get("requests", [])) != 4:
        raise ValueError("benchmark batch must contain four requests")

    benchmark_report = load("validation/index_benchmark/report.json")
    if benchmark_report.get("status") != "pass" or not verify_hash(benchmark_report):
        raise ValueError("benchmark report hash/status mismatch")
    if not all(benchmark_report.get("acceptance", {}).values()):
        raise ValueError("not all benchmark acceptance conditions passed")
    if benchmark_report["world"]["record_count"] != 10_000:
        raise ValueError("benchmark report record count mismatch")
    if benchmark_report["events_in_support"]["candidate_count_path"] != [10000, 9600, 96, 6, 2]:
        raise ValueError("benchmark candidate count path mismatch")

    # Immutable index file named by the final snapshot.
    store = WorldStore(ROOT / "world/index_benchmark_store")
    head = store.head
    if head is None:
        raise ValueError("benchmark store has no HEAD")
    snapshot = store.snapshot_for_commit(head)
    index = store.index_for_commit(head, required=True)
    if index is None or not verify_hash(index):
        raise ValueError("benchmark immutable index missing or invalid")
    if index["record_count"] != 10_000 or snapshot.get("indexes_hash") != index["content_hash"]:
        raise ValueError("benchmark snapshot/index binding mismatch")

    # Both documentation artifacts have a complete literal-source chain.
    artifact_sources = [
        load("examples/artifacts/roadmap_and_starter.source.json"),
        load("examples/artifacts/world_query_kernel_0_2_release.source.json"),
    ]
    for source in artifact_sources:
        if not verify_hash(source):
            raise ValueError("documentation artifact source content hash mismatch")
        for definition in source["definitions"]:
            validate_record(definition)
    roadmap_proof = load("validation/roadmap_artifact_proof.json")
    release_proof = load("validation/release_0_2_artifact_proof.json")
    for proof in (roadmap_proof, release_proof):
        if proof.get("status") != "pass" or not verify_hash(proof):
            raise ValueError("documentation artifact proof status/hash mismatch")
        if not proof["artifact"].get("source_byte_equal") or not proof["execution"].get("python_c_full_trace_equal"):
            raise ValueError("documentation artifact proof equality failure")

    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    schema_validations = 0
    if jsonschema is not None:
        def schema(name: str) -> dict[str, Any]:
            return load(f"spec/world/{name}")

        record_schema = schema("tom_world_record.schema.json")
        transaction_schema = schema("tom_world_transaction.schema.json")
        transaction_schema["properties"]["records"]["items"] = record_schema
        event_schema = schema("tom_event_certificate.schema.json")
        artifact_schema = schema("tom_literal_artifact_source.schema.json")
        artifact_schema["properties"]["definitions"]["items"] = record_schema
        index_schema = schema("tom_world_indexes.schema.json")
        plan_schema = schema("tom_query_plan.schema.json")
        batch_schema = schema("tom_batch_query.schema.json")
        audit_schema = schema("tom_audit_certificate.schema.json")
        state_schema = schema("tom_state_at_certificate_0_2.schema.json")

        # Transaction schema validation is performed on the smaller checkpoint
        # transaction; all 10,000 records have already passed the normative
        # Python validator above.
        jsonschema.Draft202012Validator(transaction_schema).validate(checkpoints)
        schema_validations += 1
        for source in artifact_sources:
            jsonschema.Draft202012Validator(artifact_schema).validate(source)
            schema_validations += 1
        jsonschema.Draft202012Validator(index_schema).validate(index)
        schema_validations += 1

        generated = {
            "events_indexed": load("validation/index_benchmark/events_indexed.json"),
            "events_exhaustive": load("validation/index_benchmark/events_exhaustive.json"),
            "state_indexed": load("validation/index_benchmark/state_at_999_indexed.json"),
            "state_exhaustive": load("validation/index_benchmark/state_at_999_exhaustive.json"),
            "batch_indexed": load("validation/index_benchmark/batch_indexed.json"),
            "batch_exhaustive": load("validation/index_benchmark/batch_exhaustive.json"),
            "audit": load("validation/index_benchmark/audit.json"),
        }
        for plan in iter_plans(generated):
            jsonschema.Draft202012Validator(plan_schema).validate(plan)
            schema_validations += 1
        for key in ("batch_indexed", "batch_exhaustive"):
            jsonschema.Draft202012Validator(batch_schema).validate(generated[key])
            schema_validations += 1
        jsonschema.Draft202012Validator(audit_schema).validate(generated["audit"])
        schema_validations += 1
        for key in ("state_indexed", "state_exhaustive"):
            jsonschema.Draft202012Validator(state_schema).validate(generated[key]["result"])
            schema_validations += 1
        for key in ("events_indexed", "events_exhaustive"):
            for event in generated[key]["result"]["events"]:
                jsonschema.Draft202012Validator(event_schema).validate(event)
                schema_validations += 1

    result = {
        "status": "pass",
        "version": "0.2.0",
        "seed": identity.as_record(),
        "required_static_assets": len(required),
        "counter_transaction_records": len(counter_transaction["records"]),
        "benchmark_records": len(all_benchmark_records),
        "benchmark_record_types": dict(sorted(type_counts.items())),
        "benchmark_head": head,
        "benchmark_indexes_hash": index["content_hash"],
        "artifact_definitions": sum(len(source["definitions"]) for source in artifact_sources),
        "jsonschema_available": jsonschema is not None,
        "jsonschema_validations": schema_validations,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
