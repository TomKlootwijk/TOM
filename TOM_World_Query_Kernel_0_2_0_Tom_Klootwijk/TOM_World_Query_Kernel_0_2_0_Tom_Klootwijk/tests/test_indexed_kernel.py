from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tom_world.audit import audit_store
from tom_world.canonical import canonical_bytes, verify_hash
from tom_world.indexes import build_index_record, validate_index_record
from tom_world.query import QueryEngine
from tom_world.store import WorldStore

ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
COUNTER_TRANSACTION = ROOT / "examples/world_counter/initial_transaction.json"
BENCHMARK_STORE = ROOT / "world/index_benchmark_store"
BENCHMARK_REPORT = ROOT / "validation/index_benchmark/report.json"
TARGET_INSTANCE = "instance:benchmark:042"


def new_counter_store(directory: Path) -> WorldStore:
    store = WorldStore.initialize(directory, SEED)
    store.commit_transaction_file(COUNTER_TRANSACTION)
    return store


class ImmutableIndexTests(unittest.TestCase):
    def test_same_snapshot_produces_same_index_in_two_stores(self):
        with tempfile.TemporaryDirectory() as left_dir, tempfile.TemporaryDirectory() as right_dir:
            left = new_counter_store(Path(left_dir))
            right = new_counter_store(Path(right_dir))
            left_index = left.index_for_commit(required=True)
            right_index = right.index_for_commit(required=True)
            self.assertIsNotNone(left_index)
            self.assertIsNotNone(right_index)
            self.assertEqual(canonical_bytes(left_index), canonical_bytes(right_index))
            self.assertEqual(left_index["content_hash"], right_index["content_hash"])

    def test_index_postings_cover_type_dependency_and_relation_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_counter_store(Path(directory))
            self.assertEqual(store.indexed_record_ids("by_type", "instance"), [
                "instance:counter", "instance:odd-peer", "instance:peer"
            ])
            self.assertIn(
                "relation:counter-rho-equals-five",
                store.indexed_record_ids("relation_by_instance", "instance:counter"),
            )
            self.assertEqual(
                store.indexed_record_ids("relation_by_support", "support:counter-rho-window"),
                ["relation:counter-rho-equals-five"],
            )
            self.assertIn(
                "instance:counter",
                store.indexed_record_ids("by_dependency", "definition:counter-trajectory"),
            )

    def test_deleted_index_rebuilds_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_counter_store(Path(directory))
            snapshot = store.snapshot_for_commit()
            index_id = snapshot["indexes_hash"]
            path = store._index_path(index_id)
            expected = path.read_bytes()
            path.unlink()
            store.clear_caches()
            certificate = store.rebuild_indexes(write=True)
            self.assertTrue(certificate["byte_equal_to_declared_hash"])
            self.assertEqual(path.read_bytes(), expected)

    def test_index_schema_and_content_hash(self):
        if not BENCHMARK_STORE.exists():
            self.skipTest("benchmark store not built")
        store = WorldStore(BENCHMARK_STORE)
        index = store.index_for_commit(required=True)
        self.assertIsNotNone(index)
        assert index is not None
        self.assertTrue(verify_hash(index))
        validate_index_record(index, records=store.snapshot_for_commit()["records"],
                              seed_sha256="sha256:" + __import__("hashlib").sha256(SEED).hexdigest())


class PlannerAndCheckpointTests(unittest.TestCase):
    def test_indexed_and_exhaustive_event_semantics_are_equal(self):
        if not BENCHMARK_STORE.exists():
            self.skipTest("benchmark store not built")
        store = WorldStore(BENCHMARK_STORE)
        indexed = QueryEngine(store, max_query_steps=2000, planner_mode="indexed")
        exhaustive = QueryEngine(store, max_query_steps=2000, planner_mode="exhaustive", use_checkpoints=False)
        left = indexed.events_in_support_with_plan(
            TARGET_INSTANCE, start_tick=0, end_tick=32,
            support_id="support:benchmark-bucket:04", planner_mode="indexed",
        )
        right = exhaustive.events_in_support_with_plan(
            TARGET_INSTANCE, start_tick=0, end_tick=32,
            support_id="support:benchmark-bucket:04", planner_mode="exhaustive",
        )
        self.assertEqual(canonical_bytes(left["result"]), canonical_bytes(right["result"]))
        self.assertEqual([event["event_tick"] for event in left["result"]["events"]], [5, 21])
        stages = left["plan"]["relation_selection"]["stages"]
        counts = [stages[0]["input_count"]] + [stage["output_count"] for stage in stages]
        self.assertEqual(counts, [10000, 9600, 96, 6, 2])
        self.assertTrue(all(stage["mechanism"].startswith("immutable_index:") for stage in stages))

    def test_checkpoint_replay_preserves_state_and_saves_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_counter_store(Path(directory))
            QueryEngine(store, max_query_steps=100).commit_checkpoints("instance:counter", [0, 2, 4])
            indexed = QueryEngine(store, max_query_steps=100, planner_mode="indexed")
            root = QueryEngine(store, max_query_steps=100, planner_mode="exhaustive", use_checkpoints=False)
            left = indexed.state_at_with_plan("instance:counter", 5)
            right = root.state_at_with_plan("instance:counter", 5)
            self.assertEqual(canonical_bytes(left["result"]), canonical_bytes(right["result"]))
            self.assertEqual(left["plan"]["checkpoint_tick"], 4)
            self.assertEqual(left["plan"]["replayed_steps"], 1)
            self.assertEqual(right["plan"]["replayed_steps"], 5)

    def test_benchmark_checkpoint_saves_nine_hundred_steps(self):
        if not BENCHMARK_REPORT.exists():
            self.skipTest("benchmark report not built")
        report = json.loads(BENCHMARK_REPORT.read_text())
        self.assertEqual(report["world"]["record_count"], 10000)
        self.assertEqual(report["checkpoint_replay"]["indexed_replayed_steps"], 99)
        self.assertEqual(report["checkpoint_replay"]["exhaustive_replayed_steps"], 999)
        self.assertEqual(report["checkpoint_replay"]["saved_steps"], 900)
        self.assertTrue(report["checkpoint_replay"]["semantic_byte_equal"])


class BatchAndAuditTests(unittest.TestCase):
    def test_batch_reduction_is_stable_across_planner_modes(self):
        if not BENCHMARK_STORE.exists():
            self.skipTest("benchmark store not built")
        requests = json.loads((ROOT / "examples/index_benchmark/batch_requests.json").read_text())["requests"]
        store = WorldStore(BENCHMARK_STORE)
        indexed = QueryEngine(store, max_query_steps=2000, planner_mode="indexed")
        exhaustive = QueryEngine(store, max_query_steps=2000, planner_mode="exhaustive", use_checkpoints=False)
        left = indexed.batch(requests, planner_mode="indexed")
        right = exhaustive.batch(requests, planner_mode="exhaustive")
        self.assertEqual(left["request_ids"], [item["id"] for item in requests])
        self.assertEqual(left["semantic_reduction_hash"], right["semantic_reduction_hash"])
        self.assertEqual(left["semantic_result_hashes"], right["semantic_result_hashes"])
        self.assertLess(left["work"].get("record_reads", 0), right["work"].get("record_reads", 0))

    def test_full_ancestry_audit_passes_and_has_no_orphans(self):
        if not BENCHMARK_STORE.exists():
            self.skipTest("benchmark store not built")
        certificate = audit_store(WorldStore(BENCHMARK_STORE), require_no_orphans=True, strict=True)
        self.assertTrue(certificate["valid"])
        self.assertEqual(len(certificate["ancestry"]), 2)
        self.assertEqual(certificate["errors"], [])
        self.assertTrue(all(record["count"] == 0 for record in certificate["orphans"].values()))

    def test_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            corrupt = Path(directory) / "corrupt"
            store = new_counter_store(source)
            shutil.copytree(source, corrupt)
            copied = WorldStore(corrupt)
            snapshot = copied.snapshot_for_commit()
            object_id = next(iter(snapshot["records"].values()))
            path = copied._object_path(object_id)
            data = bytearray(path.read_bytes())
            data[len(data) // 2] ^= 1
            path.write_bytes(data)
            certificate = audit_store(copied)
            self.assertFalse(certificate["valid"])
            self.assertTrue(any(error["kind"] in {"record", "index"} for error in certificate["errors"]))

    def test_transactions_and_indexes_are_preserved_for_every_commit(self):
        if not BENCHMARK_STORE.exists():
            self.skipTest("benchmark store not built")
        store = WorldStore(BENCHMARK_STORE)
        current = store.head
        sequence = 1
        while current is not None:
            commit = store.read_commit(current)
            self.assertEqual(commit["sequence"], sequence)
            transaction = store.read_transaction(commit["transaction_hash"])
            snapshot = store.read_snapshot(commit["snapshot_hash"])
            index = store.read_index(snapshot["indexes_hash"])
            self.assertEqual(transaction["base_commit"], commit["parent"])
            self.assertEqual(index["record_count"], len(snapshot["records"]))
            current = commit["parent"]
            sequence -= 1
        self.assertEqual(sequence, -1)


class BenchmarkAndSchemaTests(unittest.TestCase):
    def test_shipped_benchmark_report_acceptance(self):
        if not BENCHMARK_REPORT.exists():
            self.skipTest("benchmark report not built")
        report = json.loads(BENCHMARK_REPORT.read_text())
        self.assertTrue(verify_hash(report))
        self.assertEqual(report["status"], "pass")
        self.assertTrue(all(report["acceptance"].values()))
        self.assertEqual(report["events_in_support"]["candidate_count_path"], [10000, 9600, 96, 6, 2])
        self.assertEqual(report["events_in_support"]["event_ticks"], [5, 21])
        self.assertTrue(report["index_rebuild"]["byte_equal"])
        self.assertTrue(report["audit"]["valid"])

    def test_new_json_schemas_validate_shipped_certificates(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        samples = [
            ("tom_world_indexes.schema.json", WorldStore(BENCHMARK_STORE).index_for_commit(required=True)),
            ("tom_query_plan.schema.json", json.loads((ROOT / "validation/index_benchmark/events_indexed.json").read_text())["plan"]["relation_selection"]),
            ("tom_batch_query.schema.json", json.loads((ROOT / "validation/index_benchmark/batch_indexed.json").read_text())),
            ("tom_audit_certificate.schema.json", json.loads((ROOT / "validation/index_benchmark/audit.json").read_text())),
            ("tom_state_at_certificate_0_2.schema.json", json.loads((ROOT / "validation/index_benchmark/state_at_999_indexed.json").read_text())["result"]),
        ]
        for filename, value in samples:
            schema = json.loads((ROOT / "spec/world" / filename).read_text())
            jsonschema.Draft202012Validator(schema).validate(value)


if __name__ == "__main__":
    unittest.main()
