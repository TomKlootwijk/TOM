from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tomagi.core import STATUS_HALT
from tom_world.canonical import attach_hash, canonical_bytes, content_hash
from tom_world.query import QueryEngine, verify_checkpoint_record
from tom_world.records import make_record
from tom_world.store import TRANSACTION_SCHEMA, WorldStore


ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
TRANSACTION_PATH = ROOT / "examples/world_counter/initial_transaction.json"


def new_store(directory: Path) -> WorldStore:
    store = WorldStore.initialize(directory, SEED)
    store.commit_transaction_file(TRANSACTION_PATH)
    return store


def commit_records(store: WorldStore, records: list[dict], message: str) -> None:
    head = store.read_commit()
    transaction = attach_hash({
        "schema": TRANSACTION_SCHEMA,
        "seed_sha256": head["seed_sha256"],
        "base_commit": store.head,
        "sequence": int(head["sequence"]) + 1,
        "message": message,
        "records": records,
        "blobs": [],
        "provenance": {"source": "query integrity test"},
    })
    store.commit_transaction(transaction)


class CheckpointIntegrityTests(unittest.TestCase):
    def test_checkpoint_verifier_replays_from_root_and_rejects_forged_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            record = QueryEngine(store, max_query_steps=20).make_checkpoint_record(
                "instance:counter", 3
            )
            proof = verify_checkpoint_record(store, record, target_instance_id="instance:counter")
            self.assertTrue(proof["byte_equal"])
            self.assertEqual(proof["root_replay_steps"], 3)

            forged = copy.deepcopy(record)
            forged["payload"]["state"]["rho"] = 1000
            forged["content_hash"] = content_hash(forged)
            with self.assertRaisesRegex(ValueError, "semantic verification failed"):
                verify_checkpoint_record(store, forged)

    def test_full_trace_ignores_checkpoint_and_returns_the_complete_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            QueryEngine(store, max_query_steps=20).commit_checkpoints("instance:counter", [4])
            indexed = QueryEngine(store, max_query_steps=20, use_checkpoints=True)
            root = QueryEngine(store, max_query_steps=20, use_checkpoints=False)

            actual = indexed.state_at_with_plan("instance:counter", 5, include_trace=True)
            expected = root.state_at_with_plan("instance:counter", 5, include_trace=True)

            self.assertEqual(canonical_bytes(actual["result"]), canonical_bytes(expected["result"]))
            self.assertEqual(len(actual["result"]["trace"]), 5)
            self.assertIsNone(actual["plan"]["checkpoint_id"])
            self.assertEqual(actual["plan"]["replayed_steps"], 5)
            self.assertEqual(actual["plan"]["work"]["tomagi_steps"], 5)

    def test_halted_logical_ticks_do_not_count_as_tomagi_work_or_saved_work(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            halted = store.read_record("instance:counter")
            halted["payload"]["initial_state"] = {"status": STATUS_HALT}
            halted["content_hash"] = content_hash(halted)
            commit_records(store, [halted], "halt counter at its initial state")
            QueryEngine(store, max_query_steps=20).commit_checkpoints("instance:counter", [3])
            engine = QueryEngine(store, max_query_steps=20)

            state = engine.state_at_with_plan("instance:counter", 5)
            self.assertEqual(state["plan"]["checkpoint_tick"], 3)
            self.assertEqual(state["plan"]["replayed_steps"], 0)
            self.assertEqual(state["plan"]["saved_replay_steps"], 0)
            self.assertEqual(state["plan"]["work"]["tomagi_steps"], 0)

            event = engine.next_event_with_plan("instance:counter", 0, horizon=3)
            self.assertIsNone(event["result"])
            self.assertEqual(event["plan"]["ticks_scanned"], 3)
            self.assertEqual(event["plan"]["tomagi_steps_scanned"], 0)
            self.assertEqual(event["plan"]["work"]["tomagi_steps"], 0)


class EventIntegrityTests(unittest.TestCase):
    def test_rehashed_false_event_is_rejected_before_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            engine = QueryEngine(store)
            event = engine.next_event("instance:counter", 0, horizon=8)
            self.assertIsNotNone(event)
            assert event is not None

            forged = copy.deepcopy(event)
            forged["post_state"]["output"] = 999
            forged["content_hash"] = content_hash(forged)
            with self.assertRaisesRegex(ValueError, "does not reconstruct"):
                engine.commit_event(forged)
            self.assertEqual(store.list_records(record_type="event"), [])
            self.assertEqual(store.list_records(record_type="lineage"), [])

    def test_later_support_event_reconstructs_its_exact_result_position(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            always = make_record(
                "relation",
                "relation:counter-always-zero",
                {
                    "instance_id": "instance:counter",
                    "expression": {"op": "const", "value": 0},
                    "priority": 10,
                    "support_ids": ["support:counter-rho-window"],
                    "trigger": "zero",
                    "zero_test": "equal_zero",
                },
                dependencies=["instance:counter", "support:counter-rho-window"],
                provenance={"source": "query integrity test"},
            )
            commit_records(store, [always], "add repeatable exact-zero relation")
            engine = QueryEngine(store, max_query_steps=20)

            result = engine.events_in_support(
                "instance:counter",
                start_tick=0,
                end_tick=3,
                support_id="support:counter-rho-window",
            )
            self.assertEqual(result["event_count"], 3)
            later = result["events"][1]
            self.assertEqual(later["event_tick"], 2)
            self.assertEqual(later["query"]["query_kind"], "events_in_support")
            self.assertEqual(later["query"]["result_index"], 1)
            self.assertEqual(later["query"]["support_id"], "support:counter-rho-window")
            self.assertTrue(engine.reconstruct(later)["byte_equal"])

    def test_multi_relation_next_event_preserves_candidate_set(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            early = make_record(
                "relation",
                "relation:counter-rho-equals-three",
                {
                    "instance_id": "instance:counter",
                    "expression": {
                        "op": "sub",
                        "args": [
                            {"op": "field", "source": "state", "name": "rho"},
                            {"op": "const", "value": 3},
                        ],
                    },
                    "priority": 5,
                    "trigger": "enter_zero",
                    "zero_test": "equal_zero",
                },
                dependencies=["instance:counter"],
                provenance={"source": "query integrity test"},
            )
            commit_records(store, [early], "add earlier event candidate")
            engine = QueryEngine(store, max_query_steps=20)
            relation_ids = [
                "relation:counter-rho-equals-five",
                "relation:counter-rho-equals-three",
            ]

            event = engine.next_event(
                "instance:counter", 0, horizon=8, relation_ids=relation_ids
            )
            self.assertIsNotNone(event)
            assert event is not None
            self.assertEqual(event["event_tick"], 3)
            self.assertEqual(event["query"]["query_kind"], "next_event")
            self.assertEqual(event["query"]["result_index"], 0)
            self.assertEqual(event["query"]["relation_ids"], sorted(relation_ids))
            self.assertTrue(engine.reconstruct(event)["byte_equal"])

    def test_legacy_single_relation_certificate_still_reconstructs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            engine = QueryEngine(store)
            event = engine.next_event(
                "instance:counter",
                0,
                horizon=8,
                relation_ids=["relation:counter-rho-equals-five"],
            )
            self.assertIsNotNone(event)
            assert event is not None
            legacy = dict(event)
            legacy["query"] = {
                "instance_id": "instance:counter",
                "after_tick": 0,
                "horizon": 8,
                "relation_ids": ["relation:counter-rho-equals-five"],
            }
            legacy = attach_hash(legacy)
            self.assertTrue(engine.reconstruct(legacy)["byte_equal"])


if __name__ == "__main__":
    unittest.main()
