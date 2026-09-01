from __future__ import annotations

"""Build and validate the frozen TOM 0.2 10,000-record index benchmark."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from tom_world.audit import audit_store
from tom_world.canonical import attach_hash, canonical_bytes, digest_file, verify_hash
from tom_world.query import QueryEngine
from tom_world.seed import verify_seed_bytes
from tom_world.store import WorldStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/index_benchmark"
STORE_PATH = ROOT / "world/index_benchmark_store"
VALIDATION = ROOT / "validation/index_benchmark"
SEED_PATH = ROOT / "TOM_seed_genome_2026-09-01.txt"
INITIAL_TRANSACTION = SOURCE / "initial_transaction.json"
CHECKPOINT_TRANSACTION = SOURCE / "checkpoint_transaction.json"
BATCH_REQUESTS = SOURCE / "batch_requests.json"
SPEC_PATH = SOURCE / "benchmark_spec.json"
TARGET_INSTANCE = "instance:benchmark:042"


def write_json(path: Path, value: Any, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_bytes(canonical_bytes(value) + b"\n")


def tree_manifest(root: Path) -> dict[str, Any]:
    entries = []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        data = path.read_bytes()
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    length_prefixed = bytearray()
    for item in entries:
        data = canonical_bytes(item)
        length_prefixed.extend(len(data).to_bytes(8, "little"))
        length_prefixed.extend(data)
    return {
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "tree_sha256": "sha256:" + hashlib.sha256(length_prefixed).hexdigest(),
        "entries_sha256": "sha256:" + hashlib.sha256(canonical_bytes(entries)).hexdigest(),
    }


def stage_counts(planned: Mapping[str, Any]) -> list[int]:
    stages = planned["plan"]["relation_selection"]["stages"]
    return [int(stage["input_count"]) for stage in stages[:1]] + [int(stage["output_count"]) for stage in stages]


def semantic_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return canonical_bytes(left["result"]) == canonical_bytes(right["result"])


def main() -> int:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    identity = verify_seed_bytes(SEED_PATH.read_bytes())
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if not verify_hash(spec):
        raise ValueError("benchmark specification content hash mismatch")

    shutil.rmtree(STORE_PATH, ignore_errors=True)
    store = WorldStore.initialize(STORE_PATH, SEED_PATH.read_bytes())
    initial_commit = store.commit_transaction_file(INITIAL_TRANSACTION)
    checkpoint_commit = store.commit_transaction_file(CHECKPOINT_TRANSACTION)
    final_commit = str(checkpoint_commit["content_hash"])
    snapshot = store.snapshot_for_commit(final_commit)
    if len(snapshot["records"]) != 10_000:
        raise AssertionError(f"benchmark record count is {len(snapshot['records'])}, expected 10000")

    # Immutable index posting-list sanity checks.
    index = store.index_for_commit(final_commit, required=True)
    assert index is not None
    postings = {
        "relations": len(store.indexed_record_ids("by_type", "relation", commit=final_commit)),
        "instances": len(store.indexed_record_ids("by_type", "instance", commit=final_commit)),
        "support_bucket_04": len(store.indexed_record_ids(
            "relation_by_support", "support:benchmark-bucket:04", commit=final_commit
        )),
        "instance_042_relations": len(store.indexed_record_ids(
            "relation_by_instance", TARGET_INSTANCE, commit=final_commit
        )),
        "sheet_2_records": len(store.indexed_record_ids("by_topology_sheet", 2, commit=final_commit)),
        "interval_1_32_relations": len(store.interval_record_ids(1, 32, commit=final_commit, record_type="relation")),
        "checkpoint_count": len(index["indexes"]["checkpoint_by_instance"][TARGET_INSTANCE]),
        "compound_address_matches": len(store.indexed_record_ids(
            "by_generative_address",
            {"kind": "benchmark-relation", "instance": 42, "target": 5, "bucket": 4, "sheet": 2},
            commit=final_commit,
        )),
    }
    expected_postings = {
        "relations": 9600,
        "instances": 100,
        "support_bucket_04": 600,
        "instance_042_relations": 96,
        "checkpoint_count": 10,
        "compound_address_matches": 1,
    }
    for key, expected in expected_postings.items():
        if postings[key] != expected:
            raise AssertionError(f"posting count {key}: {postings[key]} != {expected}")

    indexed = QueryEngine(store, commit=final_commit, max_query_steps=2000, planner_mode="indexed")
    exhaustive = QueryEngine(
        store, commit=final_commit, max_query_steps=2000,
        planner_mode="exhaustive", use_checkpoints=False,
    )

    indexed_events = indexed.events_in_support_with_plan(
        TARGET_INSTANCE,
        start_tick=0,
        end_tick=32,
        support_id="support:benchmark-bucket:04",
        planner_mode="indexed",
    )
    exhaustive_events = exhaustive.events_in_support_with_plan(
        TARGET_INSTANCE,
        start_tick=0,
        end_tick=32,
        support_id="support:benchmark-bucket:04",
        planner_mode="exhaustive",
    )
    if not semantic_equal(indexed_events, exhaustive_events):
        raise AssertionError("indexed/exhaustive events_in_support semantic bytes differ")
    event_ticks = [event["event_tick"] for event in indexed_events["result"]["events"]]
    if event_ticks != [5, 21]:
        raise AssertionError(event_ticks)
    candidate_counts = stage_counts(indexed_events)
    if candidate_counts != [10000, 9600, 96, 6, 2]:
        raise AssertionError(f"candidate path {candidate_counts}")

    indexed_state = indexed.state_at_with_plan(TARGET_INSTANCE, 999, planner_mode="indexed")
    exhaustive_state = exhaustive.state_at_with_plan(TARGET_INSTANCE, 999, planner_mode="exhaustive")
    if not semantic_equal(indexed_state, exhaustive_state):
        raise AssertionError("checkpoint/root state_at semantic bytes differ")
    indexed_replay = indexed_state["plan"]
    exhaustive_replay = exhaustive_state["plan"]
    if indexed_replay["checkpoint_tick"] != 900 or indexed_replay["replayed_steps"] != 99:
        raise AssertionError("indexed checkpoint plan mismatch")
    if exhaustive_replay["checkpoint_tick"] != 0 or exhaustive_replay["replayed_steps"] != 999:
        raise AssertionError("root replay plan mismatch")
    state_reduction = {
        "rho": indexed_state["result"]["state"]["rho"],
        "tick": indexed_state["result"]["state"]["tick"],
        "indexed_replayed_steps": indexed_replay["replayed_steps"],
        "exhaustive_replayed_steps": exhaustive_replay["replayed_steps"],
        "saved_steps": exhaustive_replay["replayed_steps"] - indexed_replay["replayed_steps"],
    }
    if state_reduction != {
        "rho": 999, "tick": 999, "indexed_replayed_steps": 99,
        "exhaustive_replayed_steps": 999, "saved_steps": 900,
    }:
        raise AssertionError(state_reduction)

    request_record = json.loads(BATCH_REQUESTS.read_text(encoding="utf-8"))
    requests = request_record["requests"]
    indexed_batch = indexed.batch(requests, planner_mode="indexed")
    exhaustive_batch = exhaustive.batch(requests, planner_mode="exhaustive")
    if indexed_batch["semantic_reduction_hash"] != exhaustive_batch["semantic_reduction_hash"]:
        raise AssertionError("batch semantic reduction differs across planner modes")
    if indexed_batch["semantic_result_hashes"] != exhaustive_batch["semantic_result_hashes"]:
        raise AssertionError("batch semantic result hashes differ across planner modes")

    # Index loss is recoverable from immutable snapshot records and must recreate
    # the exact content-addressed bytes named by the snapshot.
    index_hash = str(snapshot["indexes_hash"])
    index_path = store._index_path(index_hash)
    original_index_bytes = index_path.read_bytes()
    original_index_file_hash = hashlib.sha256(original_index_bytes).hexdigest()
    index_path.unlink()
    rebuild_certificate = store.rebuild_indexes(commit=final_commit, write=True)
    rebuilt_index_bytes = index_path.read_bytes()
    index_rebuild_equal = original_index_bytes == rebuilt_index_bytes
    if not index_rebuild_equal:
        raise AssertionError("rebuilt index file bytes differ")

    audit = audit_store(store, commit=final_commit, require_no_orphans=True, strict=True)
    if not audit["valid"]:
        raise AssertionError("benchmark world audit failed")

    write_json(VALIDATION / "initial_commit.json", initial_commit)
    write_json(VALIDATION / "checkpoint_commit.json", checkpoint_commit)
    write_json(VALIDATION / "postings.json", postings)
    write_json(VALIDATION / "events_indexed.json", indexed_events)
    write_json(VALIDATION / "events_exhaustive.json", exhaustive_events)
    write_json(VALIDATION / "state_at_999_indexed.json", indexed_state)
    write_json(VALIDATION / "state_at_999_exhaustive.json", exhaustive_state)
    write_json(VALIDATION / "batch_indexed.json", indexed_batch)
    write_json(VALIDATION / "batch_exhaustive.json", exhaustive_batch)
    write_json(VALIDATION / "index_rebuild.json", rebuild_certificate)
    write_json(VALIDATION / "audit.json", audit)

    store_tree = tree_manifest(STORE_PATH)
    report = attach_hash({
        "schema": "TOM-INDEX-BENCHMARK-REPORT-0.2",
        "version": "0.2.0",
        "status": "pass",
        "seed_sha256": "sha256:" + identity.sha256,
        "specification_hash": spec["content_hash"],
        "source": {
            "initial_transaction_sha256": digest_file(INITIAL_TRANSACTION),
            "checkpoint_transaction_sha256": digest_file(CHECKPOINT_TRANSACTION),
            "batch_requests_sha256": digest_file(BATCH_REQUESTS),
        },
        "world": {
            "initial_commit": initial_commit["content_hash"],
            "checkpoint_commit": checkpoint_commit["content_hash"],
            "head": store.head,
            "record_count": len(snapshot["records"]),
            "blob_count": len(snapshot["blobs"]),
            "indexes_hash": index_hash,
            "store_tree": store_tree,
        },
        "postings": postings,
        "events_in_support": {
            "event_ticks": event_ticks,
            "candidate_count_path": candidate_counts,
            "indexed_selected_relations": indexed_events["plan"]["selected_relation_count"],
            "indexed_relation_evaluations": indexed_events["plan"]["relation_evaluations"],
            "exhaustive_record_reads": exhaustive_events["plan"]["relation_selection"]["work"]["record_reads"],
            "semantic_byte_equal": semantic_equal(indexed_events, exhaustive_events),
            "indexed_certificate_hash": indexed_events["content_hash"],
            "exhaustive_certificate_hash": exhaustive_events["content_hash"],
            "semantic_result_hash": indexed_events["result"]["content_hash"],
        },
        "checkpoint_replay": {
            **state_reduction,
            "semantic_byte_equal": semantic_equal(indexed_state, exhaustive_state),
            "semantic_result_hash": indexed_state["result"]["content_hash"],
            "selected_checkpoint_id": indexed_replay["checkpoint_id"],
        },
        "batch": {
            "request_count": indexed_batch["request_count"],
            "reduction_order": indexed_batch["reduction_order"],
            "semantic_reduction_hash": indexed_batch["semantic_reduction_hash"],
            "semantic_equal": indexed_batch["semantic_reduction_hash"] == exhaustive_batch["semantic_reduction_hash"],
            "indexed_work": indexed_batch["work"],
            "exhaustive_work": exhaustive_batch["work"],
        },
        "index_rebuild": {
            "deleted_then_rebuilt": True,
            "declared_indexes_hash": index_hash,
            "original_file_sha256": "sha256:" + original_index_file_hash,
            "rebuilt_file_sha256": "sha256:" + hashlib.sha256(rebuilt_index_bytes).hexdigest(),
            "byte_equal": index_rebuild_equal,
            "certificate_hash": rebuild_certificate["content_hash"],
        },
        "audit": {
            "valid": audit["valid"],
            "certificate_hash": audit["content_hash"],
            "ancestry_length": len(audit["ancestry"]),
            "errors": len(audit["errors"]),
            "orphan_counts": {key: value["count"] for key, value in audit["orphans"].items()},
        },
        "acceptance": {
            "record_count_exactly_10000": len(snapshot["records"]) == 10000,
            "candidate_path_exact": candidate_counts == [10000, 9600, 96, 6, 2],
            "events_semantic_equal": semantic_equal(indexed_events, exhaustive_events),
            "checkpoint_semantic_equal": semantic_equal(indexed_state, exhaustive_state),
            "checkpoint_saved_900_steps": state_reduction["saved_steps"] == 900,
            "batch_semantic_equal": indexed_batch["semantic_reduction_hash"] == exhaustive_batch["semantic_reduction_hash"],
            "index_rebuild_byte_equal": index_rebuild_equal,
            "full_ancestry_audit": audit["valid"],
        },
    })
    if not all(report["acceptance"].values()):
        raise AssertionError(report["acceptance"])
    write_json(VALIDATION / "report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
