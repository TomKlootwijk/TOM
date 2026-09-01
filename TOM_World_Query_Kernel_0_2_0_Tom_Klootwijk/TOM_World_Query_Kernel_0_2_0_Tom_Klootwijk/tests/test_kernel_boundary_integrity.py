from __future__ import annotations

import copy
import struct
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any

from tomagi.core import Cell, Opcode, Program
from tomagi.format import dumps, load, loads
from tom_world.audit import audit_store
from tom_world.canonical import attach_hash, canonical_bytes, content_hash, digest_bytes
from tom_world.indexes import build_index_record
from tom_world.query import QueryEngine
from tom_world.store import (
    COMMIT_SCHEMA,
    SNAPSHOT_SCHEMA,
    STORE_VERSION,
    TRANSACTION_SCHEMA,
    WorldStore,
)


ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
TRANSACTION_PATH = ROOT / "examples/world_counter/initial_transaction.json"
PROGRAM_PATH = ROOT / "examples/world_counter/counter_program.tmg"


def new_store(directory: Path) -> WorldStore:
    store = WorldStore.initialize(directory, SEED)
    store.commit_transaction_file(TRANSACTION_PATH)
    return store


def transaction_for(
    store: WorldStore,
    records: list[dict[str, Any]],
    *,
    blobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base = store.read_commit()
    return attach_hash({
        "schema": TRANSACTION_SCHEMA,
        "seed_sha256": base["seed_sha256"],
        "base_commit": store.head,
        "sequence": int(base["sequence"]) + 1,
        "message": "kernel boundary integrity regression",
        "records": records,
        "blobs": list(blobs or []),
        "provenance": {"source": "test_kernel_boundary_integrity"},
    })


def publish_unchecked_commit(store: WorldStore, records: list[dict[str, Any]]) -> str:
    """Write a fully self-hashed commit while intentionally bypassing publication checks."""

    parent = store.read_commit()
    parent_snapshot = store.snapshot_for_commit()
    record_map = {str(key): str(value) for key, value in parent_snapshot["records"].items()}
    for record in records:
        object_id = store._put_hashed_json(store.objects_dir, record)
        record_map[str(record["id"])] = object_id

    index = build_index_record(
        record_map,
        store._load_record_from_map,
        seed_sha256=str(parent_snapshot["seed_sha256"]),
    )
    index_id = store._put_hashed_json(store.indexes_dir, index)
    snapshot = attach_hash({
        "schema": SNAPSHOT_SCHEMA,
        "version": STORE_VERSION,
        "seed_sha256": parent_snapshot["seed_sha256"],
        "records": {key: record_map[key] for key in sorted(record_map)},
        "blobs": dict(parent_snapshot["blobs"]),
        "indexes_hash": index_id,
    })
    snapshot_id = store._put_hashed_json(store.snapshots_dir, snapshot)
    transaction = transaction_for(store, records)
    transaction_id = store._put_hashed_json(store.transactions_dir, transaction)
    commit = attach_hash({
        "schema": COMMIT_SCHEMA,
        "version": STORE_VERSION,
        "seed_sha256": parent["seed_sha256"],
        "sequence": int(parent["sequence"]) + 1,
        "parent": parent["content_hash"],
        "transaction_hash": transaction_id,
        "snapshot_hash": snapshot_id,
        "indexes_hash": index_id,
        "message": transaction["message"],
        "provenance": transaction["provenance"],
    })
    commit_id = store._put_hashed_json(store.commits_dir, commit)
    store.head_path.write_text(commit_id + "\n", encoding="ascii")
    return commit_id


class QueryBoundaryTests(unittest.TestCase):
    def test_batch_hashes_literal_null_and_counts_each_plan_once(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = QueryEngine(new_store(Path(directory)), max_query_steps=20)
            request = {
                "id": "no-event",
                "operation": "next_event",
                "parameters": {
                    "instance_id": "instance:counter",
                    "after_tick": 0,
                    "horizon": 4,
                },
            }
            individual = engine.next_event_with_plan("instance:counter", 0, horizon=4)
            batch = engine.batch([request])

            null_bytes = canonical_bytes(None)
            expected = digest_bytes(len(null_bytes).to_bytes(8, "little") + null_bytes)
            self.assertIsNone(batch["results"][0]["result"])
            self.assertEqual(batch["semantic_reduction_hash"], expected)
            self.assertEqual(batch["work"], individual["plan"]["work"])

    def test_query_configuration_and_parameters_are_not_coerced(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            with self.assertRaisesRegex(ValueError, "max_query_steps"):
                QueryEngine(store, max_query_steps=True)
            with self.assertRaisesRegex(ValueError, "use_checkpoints"):
                QueryEngine(store, use_checkpoints="false")  # type: ignore[arg-type]

            engine = QueryEngine(store, max_query_steps=20)
            for tick in ("3", True, 3.9):
                with self.subTest(tick=tick), self.assertRaises(ValueError):
                    engine.batch([{
                        "id": "state",
                        "operation": "state_at",
                        "parameters": {"instance_id": "instance:counter", "tick": tick},
                    }])
            with self.assertRaisesRegex(ValueError, "include_trace"):
                engine.state_at("instance:counter", 1, include_trace="false")  # type: ignore[arg-type]
            with self.assertRaisesRegex(ValueError, "relation_ids"):
                engine.next_event("instance:counter", 0, horizon=1, relation_ids="")  # type: ignore[arg-type]
            with self.assertRaisesRegex(ValueError, "context"):
                engine.next_event("instance:counter", 0, horizon=1, context=[])  # type: ignore[arg-type]
            with self.assertRaisesRegex(ValueError, "end_tick"):
                engine.events_in_support("instance:counter", start_tick=0, end_tick=True)


class ProgramAndInstanceBoundaryTests(unittest.TestCase):
    def test_instance_cell_override_is_the_actual_root_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = new_store(root / "store")
            original = load(PROGRAM_PATH)
            program = Program(
                cells=[
                    Cell(0, 0, int(Opcode.NOP), 0, 0, 0, 0, 0, 0, 0, 0, 0),
                    Cell(0, 1, int(Opcode.HALT), 0, 0, 0, 0, 0, 1, 1, 0, 0),
                ],
                entry=0,
                seed=original.seed,
                default_ticks=original.default_ticks,
                initial_state=replace(original.initial_state, cell=0),
                flags=original.flags,
            )
            blob_data = dumps(program)
            blob_path = root / "two-cell.tmg"
            blob_path.write_bytes(blob_data)
            instance = store.read_record("instance:counter")
            instance["payload"]["initial_state"] = {"cell": 1}
            instance["content_hash"] = content_hash(instance)
            transaction = transaction_for(
                store,
                [instance],
                blobs=[{
                    "id": "blob:counter-trajectory.tmg",
                    "path": blob_path.name,
                    "sha256": digest_bytes(blob_data),
                }],
            )
            store.commit_transaction(transaction, source_dir=root)

            state = QueryEngine(store).state_at("instance:counter", 0)
            self.assertEqual(state["state"]["cell"], 1)

    def test_out_of_range_instance_cell_is_rejected_at_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            instance = store.read_record("instance:counter")
            instance["payload"]["initial_state"] = {"cell": 1}
            instance["content_hash"] = content_hash(instance)
            with self.assertRaisesRegex(ValueError, "cell table"):
                store.commit_transaction(transaction_for(store, [instance]))

    def test_python_loader_and_store_reject_unknown_tomagi_opcode(self):
        malformed = bytearray(PROGRAM_PATH.read_bytes())
        struct.pack_into("<I", malformed, 128 + 8, 16)
        with self.assertRaisesRegex(ValueError, "opcode"):
            loads(bytes(malformed))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = new_store(root / "store")
            blob_path = root / "bad-opcode.tmg"
            blob_path.write_bytes(malformed)
            transaction = transaction_for(
                store,
                [],
                blobs=[{
                    "id": "blob:counter-trajectory.tmg",
                    "path": blob_path.name,
                    "sha256": digest_bytes(bytes(malformed)),
                }],
            )
            with self.assertRaisesRegex(ValueError, "valid TOMAGI program"):
                store.commit_transaction(transaction, source_dir=root)


class ExecutableCertificateBoundaryTests(unittest.TestCase):
    @staticmethod
    def forged_event(engine: QueryEngine) -> dict[str, Any]:
        event = engine.next_event("instance:counter", 0, horizon=8)
        assert event is not None
        forged = copy.deepcopy(event)
        forged["post_state"]["output"] = 999
        forged["content_hash"] = content_hash(forged)
        return forged

    def test_direct_transaction_cannot_bypass_event_reconstruction(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            engine = QueryEngine(store)
            event_record, lineage_record = engine.event_records(self.forged_event(engine))
            old_head = store.head
            with self.assertRaisesRegex(ValueError, "reconstruct"):
                store.commit_transaction(transaction_for(store, [event_record, lineage_record]))
            self.assertEqual(store.head, old_head)

    def test_audit_rejects_self_consistent_forged_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            checkpoint = QueryEngine(store).make_checkpoint_record("instance:counter", 3)
            forged = copy.deepcopy(checkpoint)
            forged["payload"]["state"]["rho"] = 999
            payload = forged["payload"]
            declared = attach_hash({
                "schema": "TOM-STATE-AT-CERTIFICATE-0.2",
                "commit": payload["source_commit"],
                "instance_id": payload["instance_id"],
                "instance_hash": payload["instance_hash"],
                "requested_tick": payload["tick"],
                "executed_steps": payload["executed_steps"],
                "state": dict(payload["state"]),
                "status": "exact_discrete_replay",
            })
            payload["state_certificate_hash"] = declared["content_hash"]
            forged["content_hash"] = content_hash(forged)
            publish_unchecked_commit(store, [forged])

            audit = audit_store(store)
            self.assertFalse(audit["valid"])
            self.assertTrue(any("checkpoint semantic" in item["message"] for item in audit["errors"]))

    def test_audit_rejects_self_consistent_forged_event_records(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            engine = QueryEngine(store)
            event_record, lineage_record = engine.event_records(self.forged_event(engine))
            publish_unchecked_commit(store, [event_record, lineage_record])

            audit = audit_store(store)
            self.assertFalse(audit["valid"])
            self.assertTrue(any("event semantic" in item["message"] for item in audit["errors"]))


if __name__ == "__main__":
    unittest.main()
