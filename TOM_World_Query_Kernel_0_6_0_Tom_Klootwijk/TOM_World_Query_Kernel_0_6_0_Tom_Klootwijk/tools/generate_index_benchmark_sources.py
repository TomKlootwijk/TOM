from __future__ import annotations

"""Generate the frozen literal 10,000-record benchmark transactions.

This is a release-authoring tool.  Normal validation consumes the resulting
content-addressed JSON transactions as literal source and does not regenerate
or reinterpret their domain records.
"""

import json
import shutil
import tempfile
from pathlib import Path

from tom_world.canonical import attach_hash, canonical_bytes, digest_file
from tom_world.query import QueryEngine
from tom_world.records import make_record
from tom_world.seed import CANONICAL_SEED_SHA256
from tom_world.store import TRANSACTION_SCHEMA, WorldStore

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples/index_benchmark"
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
PROGRAM = ROOT / "examples/world_counter/counter_program.tmg"
PROGRAM_LOGICAL_ID = "blob:index-benchmark-counter.tmg"
INSTANCE_COUNT = 100
RELATIONS_PER_INSTANCE = 96
SUPPORT_COUNT = 16
COMPATIBILITY_COUNT = 4
OBSERVATION_COUNT = 269
CHECKPOINT_TICKS = list(range(0, 1000, 100))
TARGET_INSTANCE = "instance:benchmark:042"


def write_pretty(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def const(value):
    return {"op": "const", "value": value}


def field(name: str, source: str = "state"):
    return {"op": "field", "source": source, "name": name}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not PROGRAM.is_file():
        raise FileNotFoundError("counter program must be built before benchmark source generation")

    records: list[dict] = []
    definition_id = "definition:index-benchmark-linear-world"
    records.append(make_record(
        "definition",
        definition_id,
        {
            "kind": "indexed_exact_discrete_benchmark",
            "domain": "content_addressed_world_records",
            "codomain": "deterministic_query_certificates",
            "operation": "tom-world.index-benchmark-10000",
            "phase": "resolve",
            "order": 0,
            "parameters": {
                "instance_count": INSTANCE_COUNT,
                "relations_per_instance": RELATIONS_PER_INSTANCE,
                "support_count": SUPPORT_COUNT,
                "compatibility_count": COMPATIBILITY_COUNT,
                "observation_count": OBSERVATION_COUNT,
                "checkpoint_ticks": CHECKPOINT_TICKS,
                "target_instance": TARGET_INSTANCE,
            },
            "capabilities": [
                "immutable_secondary_indexes",
                "deterministic_query_plans",
                "checkpoint_replay",
                "batch_query",
                "full_ancestry_audit",
            ],
            "invariants": [
                "indexed and exhaustive semantic certificates are byte-equal",
                "deleting an index file does not destroy world authority",
                "checkpoint replay preserves state_at semantics",
            ],
        },
        provenance={"source": "TOM World & Query Kernel 0.2 frozen 10,000-record benchmark"},
    ))

    for bucket in range(SUPPORT_COUNT):
        records.append(make_record(
            "support",
            f"support:benchmark-bucket:{bucket:02d}",
            {
                "expression": const(True),
                "meaning": f"Deterministic relation bucket {bucket:02d}; query planner posting-list selector.",
                "generative_address": {"kind": "support-bucket", "bucket": bucket},
            },
            dependencies=[definition_id],
            provenance={"source": "literal index benchmark support partition"},
        ))

    for sheet in range(COMPATIBILITY_COUNT):
        records.append(make_record(
            "compatibility",
            f"compatibility:benchmark-sheet:{sheet}",
            {
                "expression": {"op": "eq", "args": [field("sheet"), const(sheet)]},
                "meaning": f"Accept only State64 topology sheet {sheet}.",
                "topology_sheet": sheet,
                "generative_address": {"kind": "sheet-compatibility", "sheet": sheet},
            },
            dependencies=[definition_id],
            provenance={"source": "literal index benchmark topology partition"},
        ))

    for instance_index in range(INSTANCE_COUNT):
        instance_id = f"instance:benchmark:{instance_index:03d}"
        sheet = instance_index % COMPATIBILITY_COUNT
        records.append(make_record(
            "instance",
            instance_id,
            {
                "program_blob_id": PROGRAM_LOGICAL_ID,
                "initial_state": {
                    "rho": 0,
                    "theta": instance_index,
                    "tick": 0,
                    "phi": 0,
                    "vrho": 1,
                    "vtheta": 0,
                    "vtick": 1,
                    "vphi": 0,
                    "orientation": 0,
                    "sheet": sheet,
                    "branch": 0,
                    "cell": 0,
                    "lineage": 0,
                    "output": 0,
                    "residual": 0,
                    "status": 0
                },
                "context": {
                    "benchmark_instance_index": instance_index,
                    "relation_count": RELATIONS_PER_INSTANCE,
                    "domain": "index-benchmark-10000",
                },
                "time_interval": {"start": 0, "end": 1000},
                "topology_sheet": sheet,
                "generative_address": {"kind": "benchmark-instance", "index": instance_index},
            },
            dependencies=[definition_id],
            provenance={"source": "literal benchmark instance"},
        ))

        for target in range(1, RELATIONS_PER_INSTANCE + 1):
            bucket = (target - 1) % SUPPORT_COUNT
            support_id = f"support:benchmark-bucket:{bucket:02d}"
            compatibility_id = f"compatibility:benchmark-sheet:{sheet}"
            records.append(make_record(
                "relation",
                f"relation:benchmark:{instance_index:03d}:{target:03d}",
                {
                    "instance_id": instance_id,
                    "expression": {"op": "sub", "args": [field("rho"), const(target)]},
                    "zero_test": "equal_zero",
                    "trigger": "enter_zero",
                    "support_ids": [support_id],
                    "compatibility_ids": [compatibility_id],
                    "priority": target,
                    "active_interval": {"start": target, "end": target},
                    "topology_sheet": sheet,
                    "generative_address": {
                        "kind": "benchmark-relation",
                        "instance": instance_index,
                        "target": target,
                        "bucket": bucket,
                        "sheet": sheet,
                    },
                    "meaning": f"Exact zero when instance {instance_index:03d} reaches rho={target}.",
                },
                dependencies=[instance_id, support_id, compatibility_id],
                provenance={"source": "literal exact-discrete indexed relation"},
            ))

    for index in range(OBSERVATION_COUNT):
        records.append(make_record(
            "observation",
            f"observation:benchmark:{index:03d}",
            {
                "value": index,
                "time_interval": {"start": index % 97, "end": index % 97},
                "topology_sheet": index % COMPATIBILITY_COUNT,
                "generative_address": {"kind": "benchmark-observation", "index": index},
                "meaning": "Non-relation load record used to prove type-first candidate reduction.",
            },
            dependencies=[definition_id],
            provenance={"source": "literal benchmark non-relation population"},
        ))

    expected_initial = 1 + SUPPORT_COUNT + COMPATIBILITY_COUNT + INSTANCE_COUNT + INSTANCE_COUNT * RELATIONS_PER_INSTANCE + OBSERVATION_COUNT
    if expected_initial != 9990 or len(records) != expected_initial:
        raise AssertionError((expected_initial, len(records)))

    initial = attach_hash({
        "schema": TRANSACTION_SCHEMA,
        "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
        "base_commit": None,
        "sequence": 0,
        "message": "Initialize deterministic TOM 0.2 immutable-index benchmark with 9,990 records",
        "records": records,
        "blobs": [{
            "id": PROGRAM_LOGICAL_ID,
            "path": "../world_counter/counter_program.tmg",
            "media_type": "application/x-tomagi",
            "sha256": digest_file(PROGRAM),
        }],
        "provenance": {
            "profile": "TOM-WORLD-QUERY-KERNEL-0.2",
            "benchmark": "TOM-INDEX-BENCHMARK-10000-0.2",
            "record_count": 9990,
            "source": "frozen literal benchmark transaction",
        },
    })
    write_pretty(OUT / "initial_transaction.json", initial)

    with tempfile.TemporaryDirectory(prefix="tom-index-benchmark-source-") as tmp:
        store = WorldStore.initialize(Path(tmp) / "store", SEED)
        initial_commit = store.commit_transaction(initial, source_dir=OUT)
        engine = QueryEngine(store, max_query_steps=2000)
        checkpoint_records = [engine.make_checkpoint_record(TARGET_INSTANCE, tick) for tick in CHECKPOINT_TICKS]
        checkpoint_transaction = attach_hash({
            "schema": TRANSACTION_SCHEMA,
            "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
            "base_commit": initial_commit["content_hash"],
            "sequence": 1,
            "message": "Append ten exact replay checkpoints for benchmark instance 042",
            "records": checkpoint_records,
            "blobs": [],
            "provenance": {
                "profile": "TOM-WORLD-QUERY-KERNEL-0.2",
                "source_commit": initial_commit["content_hash"],
                "target_instance": TARGET_INSTANCE,
                "ticks": CHECKPOINT_TICKS,
            },
        })
        write_pretty(OUT / "checkpoint_transaction.json", checkpoint_transaction)
        checkpoint_commit = store.commit_transaction(checkpoint_transaction)
        final_snapshot = store.snapshot_for_commit(checkpoint_commit["content_hash"])
        if len(final_snapshot["records"]) != 10_000:
            raise AssertionError(len(final_snapshot["records"]))

    requests = {
        "schema": "TOM-BATCH-QUERY-REQUESTS-0.2",
        "version": "0.2.0",
        "planner_modes": ["indexed", "exhaustive"],
        "requests": [
            {
                "id": "state-at-999",
                "operation": "state_at",
                "parameters": {"instance_id": TARGET_INSTANCE, "tick": 999}
            },
            {
                "id": "events-bucket-04",
                "operation": "events_in_support",
                "parameters": {
                    "instance_id": TARGET_INSTANCE,
                    "start_tick": 0,
                    "end_tick": 32,
                    "support_id": "support:benchmark-bucket:04"
                }
            },
            {
                "id": "next-event-after-20",
                "operation": "next_event",
                "parameters": {"instance_id": TARGET_INSTANCE, "after_tick": 20, "horizon": 16}
            },
            {
                "id": "definition-root",
                "operation": "definition_at",
                "parameters": {"id": definition_id}
            }
        ]
    }
    write_pretty(OUT / "batch_requests.json", requests)

    spec = attach_hash({
        "schema": "TOM-INDEX-BENCHMARK-SPECIFICATION-0.2",
        "version": "0.2.0",
        "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
        "initial_records": 9990,
        "checkpoint_records": 10,
        "final_records": 10000,
        "instances": INSTANCE_COUNT,
        "relations": INSTANCE_COUNT * RELATIONS_PER_INSTANCE,
        "supports": SUPPORT_COUNT,
        "compatibility_records": COMPATIBILITY_COUNT,
        "observations": OBSERVATION_COUNT,
        "target_instance": TARGET_INSTANCE,
        "checkpoint_ticks": CHECKPOINT_TICKS,
        "event_query": {
            "start_tick": 0,
            "end_tick": 32,
            "support_id": "support:benchmark-bucket:04",
            "expected_event_ticks": [5, 21],
            "expected_candidate_path": [10000, 9600, 96, 6, 2]
        },
        "state_query": {
            "tick": 999,
            "expected_checkpoint_tick": 900,
            "expected_indexed_replay_steps": 99,
            "expected_root_replay_steps": 999
        },
        "acceptance": [
            "indexed and exhaustive semantic query bytes are equal",
            "indexed candidate plan records every immutable posting-list stage",
            "checkpoint replay returns the root-replay state while reducing TOMAGI transitions",
            "batch semantic reduction hash is equal across planner modes",
            "deleted immutable index bytes rebuild exactly from the snapshot",
            "full commit ancestry audit passes",
        ],
    })
    write_pretty(OUT / "benchmark_spec.json", spec)
    print(json.dumps({
        "initial_transaction": initial["content_hash"],
        "checkpoint_transaction": checkpoint_transaction["content_hash"],
        "initial_records": len(records),
        "checkpoint_records": len(checkpoint_records),
        "final_records": 10000,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
