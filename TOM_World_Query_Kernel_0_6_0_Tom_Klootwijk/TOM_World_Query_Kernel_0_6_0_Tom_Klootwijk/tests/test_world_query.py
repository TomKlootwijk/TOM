from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _c_backend_command(executable: Path, program: Path, *args: str) -> list[str]:
    if os.name != "nt":
        return [str(executable), str(program), *args]

    def wsl_path(path: Path) -> str:
        resolved = str(path.resolve()).replace("\\", "/")
        if len(resolved) < 3 or resolved[1:3] != ":/":
            raise RuntimeError(f"cannot map Windows path into WSL: {resolved}")
        return f"/mnt/{resolved[0].lower()}/{resolved[3:]}"

    return ["wsl.exe", wsl_path(executable), wsl_path(program), *args]

from tomagi.core import run
from tomagi.format import load
from tom_world.artifact import (
    compile_literal_artifact,
    make_literal_artifact_source,
    materialize_trace,
    run_and_materialize,
)
from tom_world.canonical import attach_hash, canonical_bytes, content_hash, verify_hash
from tom_world.expression import ExpressionBudget, evaluate_expression
from tom_world.grammar import GrammarEngine
from tom_world.query import QueryEngine
from tom_world.records import make_record, topological_record_order
from tom_world.seed import CANONICAL_SEED_SHA256, verify_seed_bytes
from tom_world.store import WorldStore

SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
TRANSACTION_PATH = ROOT / "examples/world_counter/initial_transaction.json"
PROGRAM_PATH = ROOT / "examples/world_counter/counter_program.tmg"


def new_store(directory: Path) -> WorldStore:
    store = WorldStore.initialize(directory, SEED)
    store.commit_transaction_file(TRANSACTION_PATH)
    return store


class SeedAndCanonicalTests(unittest.TestCase):
    def test_seed_identity(self):
        identity = verify_seed_bytes(SEED)
        self.assertEqual(identity.bytes, 244)
        self.assertEqual(identity.sha256, CANONICAL_SEED_SHA256)

    def test_seed_mutation_rejected(self):
        changed = bytearray(SEED)
        changed[10] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verify_seed_bytes(bytes(changed))

    def test_record_hash_is_semantic(self):
        record = make_record(
            "observation",
            "observation:test",
            {"b": 2, "a": [1, 3]},
            provenance={"source": "test"},
        )
        self.assertTrue(verify_hash(record))
        reordered = json.loads(json.dumps(record, sort_keys=False))
        self.assertEqual(canonical_bytes(record), canonical_bytes(reordered))
        reordered["payload"]["b"] = 4
        self.assertFalse(verify_hash(reordered))

    def test_dependency_order_and_cycle(self):
        a = make_record("observation", "observation:a", {}, provenance={})
        b = make_record("hypothesis", "hypothesis:b", {}, dependencies=[a["id"]], provenance={})
        self.assertEqual(topological_record_order([b, a]), [a["id"], b["id"]])
        c = copy.deepcopy(a)
        d = copy.deepcopy(b)
        c["dependencies"] = [d["id"]]
        c["content_hash"] = content_hash(c)
        d["dependencies"] = [c["id"]]
        d["content_hash"] = content_hash(d)
        with self.assertRaisesRegex(ValueError, "cycle"):
            topological_record_order([c, d])


class ExpressionTests(unittest.TestCase):
    def test_integer_boolean_interval_and_cyclic_expressions(self):
        sources = {"state": {"rho": 5, "theta": 1}, "context": {"target": 5}}
        expr = {
            "op": "all",
            "args": [
                {"op": "eq", "args": [
                    {"op": "field", "source": "state", "name": "rho"},
                    {"op": "field", "source": "context", "name": "target"}
                ]},
                {"op": "contains_zero", "args": [
                    {"op": "interval", "args": [
                        {"op": "const", "value": -1},
                        {"op": "const", "value": 2}
                    ]}
                ]},
                {"op": "eq", "args": [
                    {"op": "cyclic_delta", "args": [
                        {"op": "const", "value": 15},
                        {"op": "const", "value": 1},
                        {"op": "const", "value": 16}
                    ]},
                    {"op": "const", "value": -2}
                ]}
            ]
        }
        self.assertTrue(evaluate_expression(expr, sources))

    def test_expression_budget_rejected(self):
        with self.assertRaisesRegex(ValueError, "node budget"):
            evaluate_expression(
                {"op": "add", "args": [{"op": "const", "value": 1}, {"op": "const", "value": 2}]},
                {},
                budget=ExpressionBudget(max_nodes=2, max_depth=10),
            )


class StoreTests(unittest.TestCase):
    def test_same_transaction_produces_same_commit_in_two_stores(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            left = new_store(Path(a))
            right = new_store(Path(b))
            self.assertEqual(left.head, right.head)
            self.assertEqual(left.read_commit(), right.read_commit())
            self.assertEqual(left.snapshot_for_commit(), right.snapshot_for_commit())

    def test_stale_base_commit_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            transaction = json.loads(TRANSACTION_PATH.read_text())
            with self.assertRaisesRegex(ValueError, "does not match HEAD"):
                store.commit_transaction(transaction, source_dir=TRANSACTION_PATH.parent)

    def test_bad_blob_hash_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorldStore.initialize(Path(directory), SEED)
            transaction = json.loads(TRANSACTION_PATH.read_text())
            transaction["blobs"][0]["sha256"] = "sha256:" + "0" * 64
            transaction["content_hash"] = content_hash(transaction)
            with self.assertRaisesRegex(ValueError, "blob .* hash mismatch"):
                store.commit_transaction(transaction, source_dir=TRANSACTION_PATH.parent)

    def test_verify_definition_and_missing_id(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            engine = QueryEngine(store)
            valid = engine.verify_definition("definition:world-query-kernel")
            self.assertTrue(valid["valid"])
            self.assertTrue(valid["is_definition"])
            missing = store.verify_record("definition:missing")
            self.assertFalse(missing["valid"])


class NativeQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = new_store(Path(self.temp.name))
        self.engine = QueryEngine(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def test_state_at_and_trace(self):
        at_zero = self.engine.state_at("instance:counter", 0)
        at_three = self.engine.state_at("instance:counter", 3)
        trace = self.engine.trace("instance:counter", 5)
        self.assertEqual(at_zero["state"]["rho"], 0)
        self.assertEqual(at_three["state"]["rho"], 3)
        self.assertEqual(at_three["state"]["tick"], 3)
        self.assertEqual(len(trace["trace"]), 5)
        self.assertEqual(trace["state"]["rho"], 5)

    def test_next_event_exact_zero(self):
        event = self.engine.next_event("instance:counter", 0, horizon=8)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["event_tick"], 5)
        self.assertEqual(event["residual"], 0)
        self.assertEqual(event["previous_residual"], -1)
        self.assertEqual(event["guard_margin"], 1)
        self.assertEqual(event["post_state"]["output"], 5)
        self.assertTrue(all(item["accepted"] for item in event["support"]))
        self.assertTrue(all(item["accepted"] for item in event["compatibility"]))

    def test_no_event_before_horizon(self):
        self.assertIsNone(self.engine.next_event("instance:counter", 0, horizon=4))

    def test_events_in_support(self):
        result = self.engine.events_in_support(
            "instance:counter",
            start_tick=0,
            end_tick=8,
            support_id="support:counter-rho-window",
        )
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["events"][0]["event_tick"], 5)

    def test_compatibility_positive_and_negative(self):
        accepted = self.engine.compatible(
            "instance:counter", "instance:peer", "compatibility:same-topology", tick=3
        )
        rejected = self.engine.compatible(
            "instance:counter", "instance:odd-peer", "compatibility:same-topology", tick=3
        )
        self.assertTrue(accepted["compatible"])
        self.assertFalse(rejected["compatible"])

    def test_event_commit_and_lineage_reconstruction(self):
        event = self.engine.next_event("instance:counter", 0, horizon=8)
        assert event is not None
        commit = self.engine.commit_event(event)
        self.assertEqual(commit["sequence"], 1)
        suffix = event["content_hash"][7:23]
        updated = QueryEngine(self.store)
        rebuilt = updated.reconstruct("lineage:" + suffix)
        self.assertTrue(rebuilt["byte_equal"])
        self.assertEqual(len(self.store.list_records(record_type="event")), 1)
        self.assertEqual(len(self.store.list_records(record_type="lineage")), 1)

    def test_tampered_certificate_rejected(self):
        event = self.engine.next_event("instance:counter", 0, horizon=8)
        assert event is not None
        event["event_tick"] = 6
        with self.assertRaisesRegex(ValueError, "invalid"):
            self.engine.reconstruct(event)


class GrammarTests(unittest.TestCase):
    def test_bounded_binary_expansion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            result = GrammarEngine(store).expand("grammar:bounded-binary-branch", depth=3)
            self.assertEqual(result["terminal_symbol_count"], 29)
            self.assertEqual(result["bits_consumed"], 7)
            self.assertEqual(result["generations"][-1]["stack_depth"], 3)

    def test_depth_and_strict_bit_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            store = new_store(Path(directory))
            engine = GrammarEngine(store)
            with self.assertRaisesRegex(ValueError, "depth budget"):
                engine.expand("grammar:bounded-binary-branch", depth=4)
            with self.assertRaisesRegex(ValueError, "exhausted"):
                engine.expand("grammar:bounded-binary-branch", depth=3, branch_bits=[1])


class LiteralArtifactTests(unittest.TestCase):
    def test_literal_definition_to_tmg_to_bytes(self):
        data = b"TOM world query starter\n"
        source = make_literal_artifact_source(
            "test-artifact",
            data,
            media_type="text/plain",
            seed_bytes=SEED,
            provenance={"source": "unit test"},
        )
        program, report = compile_literal_artifact(source, SEED)
        materialized, _, trace, records = run_and_materialize(program)
        self.assertEqual(materialized, data)
        self.assertEqual(report["artifact_bytes"], len(data))
        self.assertEqual(len(trace), len(records))
        c_materialized, _ = materialize_trace(program, trace)
        self.assertEqual(c_materialized, data)


class BackendAndSchemaTests(unittest.TestCase):
    def test_c_full_trace_matches_python_when_built(self):
        executable = ROOT / "build/tomagi-c"
        if not executable.exists():
            self.skipTest("C backend not built")
        program = load(PROGRAM_PATH)
        py_state, py_trace = run(program, ticks=8, trace=True)
        c_record = json.loads(subprocess.check_output(
            _c_backend_command(executable, PROGRAM_PATH, "8", "--trace-json"),
            text=True,
        ))
        self.assertEqual(c_record["state"], {
            name: getattr(py_state, name) for name in py_state.__dataclass_fields__
        })
        self.assertEqual(c_record["trace"], py_trace)


    def test_shipped_roadmap_artifact_chain(self):
        source = ROOT / "docs/ROADMAP_AND_STARTER.md"
        artifact = ROOT / "artifacts/TOM_AGI_ROADMAP_AND_STARTER.md"
        proof_path = ROOT / "validation/roadmap_artifact_proof.json"
        if not artifact.exists() or not proof_path.exists():
            self.skipTest("roadmap artifact not built")
        proof = json.loads(proof_path.read_text())
        self.assertEqual(artifact.read_bytes(), source.read_bytes())
        self.assertTrue(proof["execution"]["python_c_full_trace_equal"])
        self.assertEqual(proof["program"]["cells"], proof["execution"]["emit_records"])
        self.assertEqual(proof["artifact"]["sha256"], "sha256:" + __import__("hashlib").sha256(artifact.read_bytes()).hexdigest())

    def test_world_json_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "spec/world/tom_world_transaction.schema.json").read_text())
        record_schema = json.loads((ROOT / "spec/world/tom_world_record.schema.json").read_text())
        schema["properties"]["records"]["items"] = record_schema
        transaction = json.loads(TRANSACTION_PATH.read_text())
        jsonschema.Draft202012Validator(schema).validate(transaction)
        event_schema = json.loads((ROOT / "spec/world/tom_event_certificate.schema.json").read_text())
        event = json.loads((ROOT / "validation/next_event.json").read_text())
        jsonschema.Draft202012Validator(event_schema).validate(event)


if __name__ == "__main__":
    unittest.main()
