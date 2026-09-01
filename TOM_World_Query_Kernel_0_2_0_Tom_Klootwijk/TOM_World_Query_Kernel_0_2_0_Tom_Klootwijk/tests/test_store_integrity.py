from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from tom_world.canonical import attach_hash, content_hash, digest_bytes
from tom_world.query import QueryEngine
from tom_world.records import make_record
from tom_world.store import TRANSACTION_SCHEMA, WorldStore


ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
TRANSACTION_PATH = ROOT / "examples/world_counter/initial_transaction.json"


def new_store(directory: Path) -> WorldStore:
    store = WorldStore.initialize(directory, SEED)
    store.commit_transaction_file(TRANSACTION_PATH)
    return store


def transaction_for(store: WorldStore, records: list[dict[str, Any]]) -> dict[str, Any]:
    commit = store.read_commit()
    return attach_hash({
        "schema": TRANSACTION_SCHEMA,
        "seed_sha256": commit["seed_sha256"],
        "base_commit": store.head,
        "sequence": int(commit["sequence"]) + 1,
        "message": "store integrity regression",
        "records": records,
        "blobs": [],
        "provenance": {"source": "test_store_integrity"},
    })


def rehash(record: dict[str, Any], change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    changed = copy.deepcopy(record)
    change(changed)
    changed["content_hash"] = content_hash(changed)
    return changed


class CacheIsolationTests(unittest.TestCase):
    def test_public_values_cannot_mutate_cached_content(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            expected_state = QueryEngine(store).state_at("instance:counter", 3)

            record = store.read_record("instance:counter")
            record["payload"]["initial_state"] = {"rho": 999}
            listed = store.list_records(record_type="instance")
            listed[0]["payload"]["program_blob_id"] = "blob:forged"

            commit = store.read_commit()
            commit["provenance"]["forged"] = True
            snapshot = store.snapshot_for_commit()
            snapshot["records"].clear()
            index = store.index_for_commit(required=True)
            assert index is not None
            index["indexes"]["by_type"]["instance"].clear()
            stored_transaction = store.read_transaction(store.read_commit()["transaction_hash"])
            stored_transaction["records"].clear()

            self.assertNotIn("initial_state", store.read_record("instance:counter")["payload"])
            self.assertEqual(len(store.list_record_ids(record_type="instance")), 3)
            self.assertNotIn("forged", store.read_commit()["provenance"])
            self.assertGreater(len(store.snapshot_for_commit()["records"]), 0)
            self.assertGreater(len(store.read_transaction(store.read_commit()["transaction_hash"])["records"]), 0)
            self.assertEqual(QueryEngine(store).state_at("instance:counter", 3), expected_state)

    def test_mutating_transaction_after_commit_does_not_poison_record_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorldStore.initialize(Path(directory), SEED)
            transaction = json.loads(TRANSACTION_PATH.read_text(encoding="utf-8"))
            store.commit_transaction(transaction, source_dir=TRANSACTION_PATH.parent)
            instance = next(record for record in transaction["records"] if record["id"] == "instance:counter")
            instance["payload"]["program_blob_id"] = "blob:forged"
            instance["payload"]["initial_state"] = {"rho": 999}

            stored = store.read_record("instance:counter")
            self.assertEqual(stored["payload"]["program_blob_id"], "blob:counter-trajectory.tmg")
            self.assertNotIn("initial_state", stored["payload"])
            self.assertEqual(QueryEngine(store).state_at("instance:counter", 3)["state"]["rho"], 3)


class ProspectiveGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = new_store(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_replacement_self_cycle_is_rejected(self):
        replacement = rehash(
            self.store.read_record("instance:counter"),
            lambda record: record["dependencies"].append("instance:counter"),
        )
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            self.store.commit_transaction(transaction_for(self.store, [replacement]))

    def test_replacement_cycle_through_untouched_record_is_rejected(self):
        replacement = rehash(
            self.store.read_record("definition:world-query-kernel"),
            lambda record: record["dependencies"].append("grammar:bounded-binary-branch"),
        )
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            self.store.commit_transaction(transaction_for(self.store, [replacement]))

    def test_replacing_referenced_id_with_wrong_type_is_rejected(self):
        replacement = make_record(
            "observation",
            "instance:counter",
            {"claim": "not an executable instance"},
            dependencies=["definition:counter-trajectory"],
        )
        with self.assertRaisesRegex(ValueError, "must reference instance"):
            self.store.commit_transaction(transaction_for(self.store, [replacement]))

    def test_relation_support_and_compatibility_types_are_enforced(self):
        support_as_compatibility = make_record(
            "compatibility",
            "support:counter-rho-window",
            {"expression": {"op": "const", "value": True}},
            dependencies=["instance:counter"],
        )
        with self.assertRaisesRegex(ValueError, "support_ids.*must reference support"):
            self.store.commit_transaction(transaction_for(self.store, [support_as_compatibility]))

        compatibility_as_support = make_record(
            "support",
            "compatibility:counter-event-topology",
            {"expression": {"op": "const", "value": True}},
            dependencies=["instance:counter"],
        )
        with self.assertRaisesRegex(ValueError, "compatibility_ids.*must reference compatibility"):
            self.store.commit_transaction(transaction_for(self.store, [compatibility_as_support]))

    def test_event_spec_relation_agreement_and_transition_type_are_enforced(self):
        second_relation = make_record(
            "relation",
            "relation:second",
            {
                "instance_id": "instance:counter",
                "expression": {"op": "const", "value": 1},
            },
            dependencies=["instance:counter"],
        )
        mismatched_spec = rehash(
            self.store.read_record("event-spec:counter-rho-five"),
            lambda record: record["payload"].__setitem__("relation_id", "relation:second"),
        )
        with self.assertRaisesRegex(ValueError, "disagree|different event_spec"):
            self.store.commit_transaction(transaction_for(self.store, [second_relation, mismatched_spec]))

        wrong_transition = rehash(
            self.store.read_record("event-spec:counter-rho-five"),
            lambda record: record["payload"].__setitem__(
                "transition_id", "support:counter-rho-window"
            ),
        )
        with self.assertRaisesRegex(ValueError, "transition_id.*must reference transition"):
            self.store.commit_transaction(transaction_for(self.store, [wrong_transition]))

    def test_additional_unselected_event_spec_for_relation_is_coherent(self):
        event_spec = make_record(
            "event_spec",
            "event-spec:counter-rho-five:alternate-route",
            {
                "relation_id": "relation:counter-rho-equals-five",
                "transition_id": "transition:counter-mark-five",
                "route": "counter.target.alternate",
            },
            dependencies=[
                "relation:counter-rho-equals-five",
                "transition:counter-mark-five",
            ],
        )
        commit = self.store.commit_transaction(transaction_for(self.store, [event_spec]))
        self.assertEqual(commit["sequence"], 1)

    def test_replacing_program_blob_with_non_tomagi_bytes_is_rejected(self):
        source = TRANSACTION_PATH.parent / "world_source.json"
        transaction = transaction_for(self.store, [])
        transaction["blobs"] = [{
            "id": "blob:counter-trajectory.tmg",
            "path": source.name,
            "sha256": digest_bytes(source.read_bytes()),
        }]
        transaction["content_hash"] = content_hash(transaction)
        with self.assertRaisesRegex(ValueError, "not a valid TOMAGI program"):
            self.store.commit_transaction(transaction, source_dir=source.parent)

    def test_instance_initial_state_requires_integer_state64_values(self):
        replacement = rehash(
            self.store.read_record("instance:counter"),
            lambda record: record["payload"].__setitem__("initial_state", {"rho": "bad"}),
        )
        with self.assertRaisesRegex(ValueError, "initial_state.rho must be an integer"):
            self.store.commit_transaction(transaction_for(self.store, [replacement]))


class CheckpointCommitValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = new_store(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_checkpoint_is_accepted(self):
        checkpoint = QueryEngine(self.store).make_checkpoint_record("instance:counter", 3)
        commit = self.store.commit_transaction(transaction_for(self.store, [checkpoint]))
        self.assertEqual(commit["sequence"], 1)

    def test_rehashed_fabricated_checkpoint_state_is_rejected_before_publication(self):
        checkpoint = QueryEngine(self.store).make_checkpoint_record("instance:counter", 3)
        forged = rehash(
            checkpoint,
            lambda record: record["payload"]["state"].__setitem__("rho", 1000),
        )
        original_head = self.store.head
        with self.assertRaisesRegex(ValueError, "checkpoint|state"):
            self.store.commit_transaction(transaction_for(self.store, [forged]))
        self.assertEqual(self.store.head, original_head)

    def test_checkpoint_must_bind_prospective_instance_type_and_hash(self):
        checkpoint = QueryEngine(self.store).make_checkpoint_record("instance:counter", 2)
        checkpoint = rehash(
            checkpoint,
            lambda record: record["payload"].__setitem__("instance_hash", "sha256:" + "0" * 64),
        )
        with self.assertRaisesRegex(ValueError, "instance hash"):
            self.store.commit_transaction(transaction_for(self.store, [checkpoint]))


if __name__ == "__main__":
    unittest.main()
