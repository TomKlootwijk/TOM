from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from tom_world03.canonical import attach_hash, canonical_bytes, require_hash, verify_hash
from tom_world03.interval import ClosedInterval
from tom_world03.rational import Q
from tom_world04r.baseline import trusted_piecewise_baseline
from tom_world04r.engine import run_continuation
from tom_world04r.index import build_interval_index, query_interval_index
from tom_world04r.io import load_world
from tom_world04r.journal import ContinuationStore
from tom_world04r.model import (
    CANONICAL_SEED_SHA256,
    CORRECTED_INTERVAL_SHA256,
    CORRECTED_V03_ZIP_SHA256,
    REJECTED_PRECORRECTION_INTERVAL_SHA256,
    ContinuationRelation,
    ContinuationWorld,
    OpenSegment,
)
from tom_world04r.solver import UnresolvedContinuation, next_event_set
from tom_world04r.transition import ContinuationConflict, apply_event_set
from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load
from tomagi.core import run

WORLD_PATH = ROOT / "examples/world04r/piecewise_world.json"
STORE_PATH = ROOT / "examples/world04r/continuation_store"
VAL = ROOT / "validation/world04r"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rehash(record: dict) -> dict:
    record.pop("content_hash", None)
    record.update({"content_hash": attach_hash(record)["content_hash"]})
    return record


def modified_world(raw: dict, mutate) -> ContinuationWorld:
    record = copy.deepcopy(raw)
    mutate(record)
    relations = [ContinuationRelation.from_record(item) for item in record["relations"]]
    record["interval_index"] = build_interval_index(relations, seed_sha256=record["seed_sha256"])
    record = attach_hash(record)
    return ContinuationWorld.from_record(record)


class TrustResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.world = load_world(WORLD_PATH)

    def test_corrected_v03_archive_pin(self):
        pin = json.loads((ROOT / "sources/CORRECTED_V0_3_BASELINE_PIN.json").read_text())
        self.assertEqual(pin["base_archive"]["sha256"], CORRECTED_V03_ZIP_SHA256)
        self.assertEqual(pin["base_archive"]["bytes"], 22217713)
        self.assertEqual(pin["base_archive"]["zip_entries"], 10291)
        self.assertFalse(pin["policy"]["prior_v0_4_used_as_source"])

    def test_every_pinned_inherited_file_matches(self):
        pin = json.loads((ROOT / "sources/CORRECTED_V0_3_BASELINE_PIN.json").read_text())
        for item in pin["critical_inherited_files"]:
            path = ROOT / item["path"]
            self.assertEqual(path.stat().st_size, item["bytes"], item["path"])
            self.assertEqual(sha256(path), item["sha256"], item["path"])

    def test_corrected_interval_file_is_exact(self):
        path = ROOT / "src/python/tom_world03/interval.py"
        self.assertEqual(sha256(path), CORRECTED_INTERVAL_SHA256)
        self.assertNotEqual(sha256(path), REJECTED_PRECORRECTION_INTERVAL_SHA256)

    def test_corrected_sign_class_uses_full_rational_equality(self):
        self.assertEqual(ClosedInterval(Q(-1, 2), Q(0)).sign_class(), "nonpositive")
        self.assertEqual(ClosedInterval(Q(0), Q(1, 2)).sign_class(), "nonnegative")
        self.assertEqual(ClosedInterval(Q(0), Q(0)).sign_class(), "zero")
        self.assertEqual(ClosedInterval(Q(-1, 2), Q(1, 2)).sign_class(), "straddles-zero")

    def test_new_namespace_and_no_old_v04_module(self):
        self.assertTrue((ROOT / "src/python/tom_world04r").is_dir())
        self.assertFalse((ROOT / "src/python/tom_world04").exists())

    def test_world_declares_trust_reset(self):
        self.assertEqual(self.world.corrected_v03_zip_sha256, CORRECTED_V03_ZIP_SHA256)
        self.assertEqual(self.world.corrected_interval_sha256, CORRECTED_INTERVAL_SHA256)
        self.assertFalse(self.raw["provenance"]["prior_v0_4_used_as_source"])
        self.assertEqual(self.raw["provenance"]["implementation_namespace"], "tom_world04r")

    def test_continuation_until_absent_from_authoritative_world(self):
        self.assertTrue(all("continuation_until" not in item for item in self.raw["relations"]))

    def test_schema_validates_world(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "spec/tom_world_piecewise_continuation_0_4_1.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(self.raw)


class ModelAndIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.world = load_world(WORLD_PATH)

    def test_world_and_nested_hashes(self):
        self.assertTrue(verify_hash(self.raw))
        nested = [self.raw["initial_segment"], self.raw["interval_index"], *self.raw["supports"],
                  *self.raw["compatibilities"], *self.raw["relations"]]
        self.assertTrue(all(verify_hash(item) for item in nested))

    def test_initial_segment_is_open_to_world_horizon(self):
        segment = self.world.initial_segment
        self.assertEqual(segment.sequence, 0)
        self.assertEqual(segment.domain, self.world.horizon)
        self.assertEqual(segment.start, Q(0))
        self.assertEqual(segment.horizon, Q(10))
        self.assertEqual(segment.fired_relations, ())

    def test_relations_declare_sdf0_interface(self):
        self.assertEqual(len(self.world.relations), 1208)
        self.assertTrue(all(item["relation_interface"] == "SDF0@Def" for item in self.raw["relations"]))
        self.assertTrue(all(item["fire_policy"] == "once" for item in self.raw["relations"]))

    def test_relation_continuation_until_rejected(self):
        record = copy.deepcopy(self.raw["relations"][0])
        record["continuation_until"] = {"num": 2, "den": 1}
        record = attach_hash(record)
        with self.assertRaisesRegex(ValueError, "continuation_until is forbidden"):
            ContinuationRelation.from_record(record)

    def test_successor_segment_requires_full_causal_parent(self):
        record = copy.deepcopy(json.loads((VAL / "successor_segment_1.json").read_text()))
        record["source_transition_hash"] = None
        record = attach_hash(record)
        with self.assertRaisesRegex(ValueError, "requires parent"):
            OpenSegment.from_record(record)

    def test_initial_segment_rejects_parent_hash(self):
        record = copy.deepcopy(self.raw["initial_segment"])
        record["parent_segment_hash"] = "sha256:" + "1" * 64
        record = attach_hash(record)
        with self.assertRaisesRegex(ValueError, "initial open segment"):
            OpenSegment.from_record(record)

    def test_interval_index_rebuilds_byte_identically(self):
        rebuilt = build_interval_index(self.world.relations, seed_sha256=self.world.seed_sha256)
        self.assertEqual(canonical_bytes(rebuilt), canonical_bytes(self.raw["interval_index"]))

    def test_index_excludes_fired_relations(self):
        interval = ClosedInterval(Q(1), Q(2))
        ids, plan = query_interval_index(
            self.world.interval_index,
            interval,
            excluded_relation_ids={"relation:stage1:time-2"},
        )
        self.assertNotIn("relation:stage1:time-2", ids)
        self.assertEqual(plan["rejected_as_already_fired"], 1)

    def test_index_has_no_false_negatives_against_exhaustive_event_semantics(self):
        indexed = run_continuation(self.world, planner="indexed")
        exhaustive = run_continuation(self.world, planner="exhaustive")
        self.assertEqual(indexed.record["semantic_chain_sha256"], exhaustive.record["semantic_chain_sha256"])
        self.assertLess(indexed.record["total_candidate_relations"], exhaustive.record["total_candidate_relations"])

    def test_index_queries_multiple_exact_brackets(self):
        relation_map = self.world.relation_map()
        for start_num in range(0, 20):
            lo = Q(start_num, 2)
            hi = min(Q(10), lo + Q(1, 2))
            if hi <= lo:
                continue
            bracket = ClosedInterval(lo, hi)
            ids, _ = query_interval_index(self.world.interval_index, bracket)
            exhaustive_overlap = {
                relation.id for relation in self.world.relations
                if relation.active_time.intersection(bracket) is not None
            }
            self.assertEqual(set(ids), exhaustive_overlap)
            self.assertTrue(all(ident in relation_map for ident in ids))


class SolverContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.world = load_world(WORLD_PATH)
        cls.indexed = run_continuation(cls.world, planner="indexed")
        cls.exhaustive = run_continuation(cls.world, planner="exhaustive")

    def test_first_boundary_is_discovered_at_two(self):
        event_set = next_event_set(self.world, self.world.initial_segment, planner="indexed")
        self.assertEqual(Q.from_value(event_set["event_time"]), Q(2))
        self.assertEqual(event_set["relation_order"], [
            "relation:stage1:time-2", "relation:stage1:x-2"
        ])
        self.assertEqual(event_set["event_count"], 2)

    def test_first_indexed_and_exhaustive_event_sets_are_semantically_equal(self):
        a = next_event_set(self.world, self.world.initial_segment, planner="indexed")
        b = next_event_set(self.world, self.world.initial_segment, planner="exhaustive")
        for field in ("event_time", "event_order", "relation_order", "relation_hashes", "fired_relations_after"):
            self.assertEqual(a[field], b[field])

    def test_complete_event_times(self):
        times = [Q.from_value(item["event_time"]).to_text()
                 for item in self.indexed.record["semantic_chain"]["event_sets"]]
        self.assertEqual(times, ["2", "5", "7", "9"])

    def test_successor_domains_remain_open_to_horizon(self):
        self.assertEqual([segment.start.to_text() for segment in self.indexed.open_segments], ["0", "2", "5", "7", "9"])
        self.assertTrue(all(segment.horizon == Q(10) for segment in self.indexed.open_segments))

    def test_realized_segment_boundaries_come_from_event_certificates(self):
        for bundle in self.indexed.bundles:
            event_time = Q.from_value(bundle.event_set["event_time"])
            self.assertEqual(Q.from_value(bundle.seal["end_time"]), event_time)
            self.assertEqual(bundle.successor.start, event_time)
            self.assertEqual(bundle.successor.source_event_set_hash, bundle.event_set["content_hash"])

    def test_complete_final_state(self):
        final = self.indexed.record["semantic_chain"]["final_state"]
        self.assertEqual({key: Q.from_value(value) for key, value in final.items()}, {
            "clock": Q(10), "counter": Q(34), "mode": Q(5), "output": Q(90), "x": Q(3),
        })

    def test_no_relation_refires(self):
        all_ids = []
        for event in self.indexed.record["semantic_chain"]["event_sets"]:
            all_ids.extend(event["relation_order"])
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertEqual(len(all_ids), 8)

    def test_crossing_certificates_bind_corrected_v03(self):
        first = next_event_set(self.world, self.world.initial_segment)
        for crossing in first["events"]:
            source = crossing["source_certificate"]
            self.assertEqual(source["schema"], "TOM-CERTIFIED-CROSSING-0.3")
            self.assertTrue(verify_hash(source))
            self.assertEqual(crossing["source_certificate_hash"], source["content_hash"])

    def test_non_affine_relation_rejects_continuation(self):
        def mutate(record):
            relation = record["relations"][0]
            relation["expression"] = {"op": "mul", "args": [
                {"op": "field", "name": "x"}, {"op": "field", "name": "x"}
            ]}
            record["relations"][0] = attach_hash(relation)
        world = modified_world(self.raw, mutate)
        with self.assertRaisesRegex(UnresolvedContinuation, "not affine"):
            next_event_set(world, world.initial_segment)

    def test_identically_zero_relation_rejects_continuation(self):
        def mutate(record):
            relation = record["relations"][0]
            relation["expression"] = {"op": "const", "value": {"num": 0, "den": 1}}
            record["relations"][0] = attach_hash(relation)
        world = modified_world(self.raw, mutate)
        with self.assertRaisesRegex(UnresolvedContinuation, "identically zero"):
            next_event_set(world, world.initial_segment)

    def test_event_budget_rejects_incomplete_run(self):
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            run_continuation(self.world, max_event_sets=3)

    def test_invalid_search_bounds_reject(self):
        with self.assertRaisesRegex(ValueError, "after lies outside"):
            next_event_set(self.world, self.world.initial_segment, after=-1)
        with self.assertRaisesRegex(ValueError, "before lies outside"):
            next_event_set(self.world, self.world.initial_segment, after=2, before=1)


class TransitionAndBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.world = load_world(WORLD_PATH)
        cls.first = next_event_set(cls.world, cls.world.initial_segment)

    def test_atomic_transition_uses_common_prestate(self):
        bundle = apply_event_set(self.world, self.world.initial_segment, self.first)
        self.assertEqual(Q.from_value(bundle.transition["pre_state"]["counter"]), Q(0))
        self.assertEqual(Q.from_value(bundle.transition["post_state"]["counter"]), Q(3))
        self.assertEqual(Q.from_value(bundle.transition["post_state"]["mode"]), Q(2))
        self.assertEqual(Q.from_value(bundle.transition["post_rates"]["x"]), Q(2))

    def test_conflicting_simultaneous_sets_reject(self):
        def mutate(record):
            relation = record["relations"][1]
            for operation in relation["transition"]:
                if operation["field"] == "output":
                    operation["value"] = {"num": 21, "den": 1}
            record["relations"][1] = attach_hash(relation)
        world = modified_world(self.raw, mutate)
        event_set = next_event_set(world, world.initial_segment)
        with self.assertRaisesRegex(ContinuationConflict, "set conflict"):
            apply_event_set(world, world.initial_segment, event_set)

    def test_tampered_event_certificate_rejects(self):
        event = copy.deepcopy(self.first)
        event["event_time"] = {"num": 3, "den": 1}
        with self.assertRaisesRegex(ValueError, "content hash mismatch"):
            apply_event_set(self.world, self.world.initial_segment, event)

    def test_independent_baseline_matches(self):
        baseline = trusted_piecewise_baseline(self.raw)
        run_record = run_continuation(self.world, planner="indexed").record
        self.assertEqual(baseline["semantic_chain_sha256"], run_record["semantic_chain_sha256"])
        self.assertEqual(baseline["event_set_count"], 4)
        self.assertEqual(baseline["realized_segment_count"], 5)

    def test_baseline_has_no_kernel_imports(self):
        source = (ROOT / "src/python/tom_world04r/baseline.py").read_text()
        self.assertNotIn("import tom_world03", source)
        self.assertNotIn("from tom_world03", source)
        self.assertNotIn("from tom_world04r", source)


class JournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.world = load_world(WORLD_PATH)

    def test_journal_audit_is_complete(self):
        store = ContinuationStore(STORE_PATH)
        audit = store.audit()
        self.assertTrue(audit["valid"], audit["errors"])
        self.assertEqual(audit["commit_count"], 6)
        self.assertEqual(audit["event_commit_count"], 4)
        self.assertEqual(audit["transaction_count"], 6)
        self.assertEqual(audit["object_count"], 19)

    def test_journal_reconstruction_matches_solver_semantics(self):
        store = ContinuationStore(STORE_PATH)
        reconstruction = store.reconstruct()
        run_record = run_continuation(self.world).record
        self.assertEqual(reconstruction["semantic_chain_sha256"], run_record["semantic_chain_sha256"])
        self.assertEqual(reconstruction["segment_count"], 5)
        self.assertEqual(reconstruction["event_set_count"], 4)

    def test_world_object_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            copy_path = Path(td) / "store"
            shutil.copytree(STORE_PATH, copy_path)
            store = ContinuationStore(copy_path)
            world_hash = store.descriptor()["world_hash"]
            path = copy_path / "objects" / f"{world_hash[7:]}.json"
            data = bytearray(path.read_bytes())
            data[20] ^= 1
            path.write_bytes(data)
            audit = store.audit()
            self.assertFalse(audit["valid"])
            self.assertTrue(any("content hash mismatch" in item or "Expecting" in item for item in audit["errors"]))

    def test_missing_initial_segment_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            copy_path = Path(td) / "store"
            shutil.copytree(STORE_PATH, copy_path)
            store = ContinuationStore(copy_path)
            chain = store._chain()
            genesis = store._get("transactions", chain[0]["transaction_hash"])
            (copy_path / "objects" / f"{genesis['initial_segment_hash'][7:]}.json").unlink()
            audit = store.audit()
            self.assertFalse(audit["valid"])
            self.assertEqual(len(audit["errors"]), 1)
            self.assertTrue(audit["errors"][0].startswith("missing immutable record: "))
            self.assertNotIn(td, audit["errors"][0])

    def test_orphan_policy_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            copy_path = Path(td) / "store"
            shutil.copytree(STORE_PATH, copy_path)
            orphan = attach_hash({"schema": "TOM-TEST-ORPHAN", "value": 1})
            path = copy_path / "objects" / f"{orphan['content_hash'][7:]}.json"
            path.write_bytes(canonical_bytes(orphan) + b"\n")
            store = ContinuationStore(copy_path)
            self.assertFalse(store.audit(require_no_orphans=True)["valid"])
            permissive = store.audit(require_no_orphans=False)
            self.assertTrue(permissive["valid"])
            self.assertTrue(permissive["warnings"])

    def test_append_after_finalization_rejects(self):
        store = ContinuationStore(STORE_PATH)
        event_set = next_event_set(self.world, self.world.initial_segment)
        bundle = apply_event_set(self.world, self.world.initial_segment, event_set)
        with self.assertRaisesRegex(ValueError, "finalized"):
            store.commit_event(bundle)


class TomagiAndCliTests(unittest.TestCase):
    def test_tomagi_abi_unchanged(self):
        self.assertEqual((HEADER_SIZE, STATE_SIZE, CELL_SIZE), (128, 64, 48))

    def test_tomagi_reference_anchors_and_python_c_trace(self):
        record = json.loads((VAL / "tomagi_piecewise_baseline.json").read_text())
        self.assertTrue(record["anchors_valid"])
        self.assertTrue(record["python_c_full_trace_equal"])
        self.assertEqual([item["time"] for item in record["anchors"]], list(range(11)))
        self.assertEqual([item["rho"] for item in record["anchors"]], [0, 2, 4, 8, 12, 16, 10, 4, 5, 6, 6])

    def test_reference_program_replays(self):
        program = load(ROOT / "examples/world04r/piecewise_reference.tmg")
        state, trace = run(program, trace=True)
        expected = json.loads((VAL / "piecewise_reference.python.trace.json").read_text())
        actual = {"state": {name: getattr(state, name) for name in state.__dataclass_fields__}, "trace": trace}
        self.assertEqual(actual, expected)

    def test_cli_validate_and_run(self):
        env = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src/python")}
        validate = subprocess.check_output([
            __import__("sys").executable, "-m", "tom_world04r", "validate", str(WORLD_PATH)
        ], cwd=ROOT, env=env, text=True)
        self.assertEqual(json.loads(validate)["status"], "valid")
        run_text = subprocess.check_output([
            __import__("sys").executable, "-m", "tom_world04r", "run", str(WORLD_PATH), "--planner", "indexed"
        ], cwd=ROOT, env=env, text=True)
        self.assertEqual(json.loads(run_text)["semantic_chain_sha256"],
                         json.loads((VAL / "run_indexed.json").read_text())["semantic_chain_sha256"])


if __name__ == "__main__":
    unittest.main()
