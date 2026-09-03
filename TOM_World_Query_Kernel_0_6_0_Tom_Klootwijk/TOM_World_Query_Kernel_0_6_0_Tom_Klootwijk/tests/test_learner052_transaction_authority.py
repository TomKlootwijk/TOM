from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

from tom_learner052.oracle import addressed, build_promotion_result
from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tomagi.formal import Limits, run_program, verify_program_hash
from tomagi.format import load
from tomagi.immutable_store import ImmutablePublicationStore, validate_plan
from tomagi.materialize import materialize_trace

FORMAL_LIMITS = Limits(
    max_steps=2_000_000,
    max_depth=256,
    max_collection_items=50_000,
    max_value_nodes=3_000_000,
    max_canonical_bytes=16_000_000,
)


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Learner052AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.promotion_program = load_json("examples/learner052/promotion_authority.formal.json")
        cls.learner_program = load_json("examples/learner052/authority_inputs/learner05_affine_authority.formal.json")
        cls.datasets = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "examples/learner052/authority_inputs/datasets").glob("*.json"))
        ]
        cls.context = load_json("examples/learner052/promotion_context.json")
        cls.corrective = load_json("examples/learner052/authority_inputs/TOM_CORRECTIVE_HANDOFF_0_5_1.json")
        cls.registry = load_json("examples/learner052/authority_inputs/tom_seed_token_registry_1_0.json")
        cls.learner_execution = run_program(
            cls.learner_program, {"datasets": cls.datasets}, limits=FORMAL_LIMITS
        )
        cls.formal_execution = run_program(
            cls.promotion_program,
            {"promotion_inputs": [
                cls.promotion_program, cls.learner_program, cls.learner_execution,
                *cls.datasets, cls.context, cls.corrective, cls.registry,
            ]},
            limits=FORMAL_LIMITS,
        )
        cls.value = cls.formal_execution["value"]
        cls.plan = cls.value["publication_plan"]

    def test_corrective_handoff_is_pinned_and_valid(self):
        verification = load_json("validation/learner052/corrective_handoff_verification.json")
        self.assertTrue(verify_hash(verification))
        self.assertTrue(verification["valid"])
        self.assertEqual(verification["unchanged_base_file_count"], 44)
        self.assertEqual(verification["replacement_count"], 3)

    def test_formal_program_identity(self):
        self.assertTrue(verify_program_hash(self.promotion_program, limits=FORMAL_LIMITS))
        self.assertEqual(
            self.promotion_program["content_hash"],
            "sha256:f1030e332b5f7358c43603096a64ebca7f9268aaaf2fbbe16dbebc972daa8bdd",
        )

    def test_seeded_source_executes_both_formal_authorities(self):
        source = load_json("examples/learner052/promotion_authority.literal.json")
        self.assertNotIn("cells", source)
        operations = [d["operation"]["op"] for d in source["definitions"]]
        self.assertEqual(operations.count("formal.evaluate"), 2)
        self.assertIn("canonical.encode", operations)
        self.assertIn("emit.graph", operations)
        self.assertEqual(source["root_definition"], "program:learner052-promotion")

    def test_formal_result_identity_and_aggregates(self):
        self.assertEqual(
            self.formal_execution["content_hash"],
            "sha256:f1a5ccbab6eb64033200c480c3e45852c3f1eccb212eca344a98005e79ecc00d",
        )
        self.assertEqual(self.formal_execution["steps"], 32900)
        self.assertEqual(self.value["dataset_count"], 19)
        self.assertEqual(self.value["accepted_count"], 12)
        self.assertEqual(self.value["rejected_count"], 7)
        self.assertEqual(self.value["publication_count"], 20)

    def test_seeded_materialization_equals_direct_formal_execution(self):
        materialized = (ROOT / "validation/learner052/promotion_authority.materialized.json").read_bytes()
        self.assertEqual(materialized, canonical_bytes(self.formal_execution) + b"\n")
        self.assertEqual(
            hashlib.sha256(materialized).hexdigest(),
            "2d6bc5b206545042e13faa5e9b4d9a0ec6b0ccf4929755c01025746b8ab4523c",
        )

    def test_independent_oracle_equals_formal_value(self):
        result = build_promotion_result(
            self.promotion_program, self.learner_program, self.learner_execution,
            self.datasets, self.context, self.corrective, self.registry,
        )
        self.assertEqual(result, self.value)

    def test_publication_plan_validates(self):
        checked = validate_plan(self.plan)
        self.assertEqual(len(checked["publications"]), 20)
        self.assertEqual(
            checked["content_hash"],
            "sha256:07b1607745e37c1f3ac7d61a47db96a3d01c884682432c91f1d77568045337e8",
        )
        self.assertEqual(checked["terminal_head"], self.value["terminal_head"])

    def test_parent_chain_is_explicit_and_contiguous(self):
        previous = None
        for sequence, publication in enumerate(self.plan["publications"]):
            self.assertEqual(publication["sequence"], sequence)
            self.assertEqual(publication["expected_head"], previous)
            previous = publication["replacement_head"]
        self.assertEqual(previous, self.plan["terminal_head"])

    def test_every_session_transaction_binds_complete_evidence(self):
        for publication in self.plan["publications"][1:]:
            transactions = [
                write["record"] for write in publication["writes"]
                if write["namespace"] == "transactions"
            ]
            self.assertEqual(len(transactions), 1)
            transaction = transactions[0]
            self.assertGreaterEqual(len(transaction["evidence_record_hashes"]), 16)
            self.assertEqual(
                len(transaction["evidence_record_hashes"]),
                len(set(transaction["evidence_record_hashes"])),
            )
            self.assertIn(transaction["acceptance_decision_hash"], transaction["evidence_record_hashes"])
            self.assertIn(transaction["promotion_certificate_hash"], transaction["evidence_record_hashes"])
            self.assertEqual(transaction["expected_parent_commit_hash"], publication["expected_head"])

    def test_accepted_and_rejected_authority_paths_are_disjoint(self):
        accepted = rejected = 0
        for publication in self.plan["publications"][1:]:
            transaction = next(
                write["record"] for write in publication["writes"]
                if write["namespace"] == "transactions"
            )
            if transaction["accepted"]:
                accepted += 1
                self.assertIsNotNone(transaction["published_definition_hash"])
                self.assertIsNone(transaction["rejection_lineage_hash"])
            else:
                rejected += 1
                self.assertIsNone(transaction["published_definition_hash"])
                self.assertIsNotNone(transaction["rejection_lineage_hash"])
        self.assertEqual((accepted, rejected), (12, 7))

    def test_generated_store_audit_and_reconstruction(self):
        audit = load_json("validation/learner052/promotion_store_audit.json")
        reconstruction = load_json("validation/learner052/promotion_store_reconstruction.json")
        self.assertTrue(verify_hash(audit))
        self.assertTrue(audit["valid"])
        self.assertEqual(audit["planned_records"], 535)
        self.assertTrue(verify_hash(reconstruction))
        self.assertEqual(reconstruction["commit_count"], 20)
        self.assertEqual(reconstruction["session_count"], 19)
        self.assertEqual(reconstruction["accepted_definition_count"], 12)
        self.assertEqual(reconstruction["rejected_session_count"], 7)

    def test_generic_store_applies_plan_from_empty_state(self):
        seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            store = ImmutablePublicationStore.apply_plan(Path(td) / "store", seed, self.plan)
            audit = store.audit_plan(self.plan, require_no_extra_records=True)
            self.assertTrue(audit["valid"])
            self.assertEqual(audit["terminal_head"], self.plan["terminal_head"])

    def test_stale_publication_head_rejected(self):
        seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            checked = validate_plan(self.plan)
            store = ImmutablePublicationStore.initialize(
                Path(td) / "store", checked["store_descriptor"], seed
            )
            store.apply_publication(checked["publications"][0])
            with self.assertRaisesRegex(ValueError, "stale publication head"):
                store.apply_publication(checked["publications"][0])

    def test_duplicate_required_hash_rejected(self):
        plan = copy.deepcopy(self.plan)
        publication = copy.deepcopy(plan["publications"][1])
        publication["required_hashes"].append(publication["required_hashes"][0])
        publication.pop("content_hash")
        publication = addressed(publication)
        plan["publications"][1] = publication
        plan.pop("content_hash")
        plan = addressed(plan)
        with self.assertRaisesRegex(ValueError, "required_hashes must be unique"):
            validate_plan(plan)

    def test_missing_replacement_commit_write_rejected(self):
        plan = copy.deepcopy(self.plan)
        publication = copy.deepcopy(plan["publications"][1])
        publication["writes"] = [
            write for write in publication["writes"]
            if not (
                write["namespace"] == "commits"
                and write["record"]["content_hash"] == publication["replacement_head"]
            )
        ]
        publication.pop("content_hash")
        publication = addressed(publication)
        plan["publications"][1] = publication
        plan.pop("content_hash")
        plan = addressed(plan)
        with self.assertRaisesRegex(ValueError, "replacement_head must be written"):
            validate_plan(plan)

    def test_result_row_dataset_hash_mutation_rejected(self):
        mutated = copy.deepcopy(self.datasets)
        mutated[0]["observations"][0]["y"] = {"num": 999, "den": 1}
        # The stale content hash itself is enough to make the source unfit for authority.
        with self.assertRaisesRegex(Exception, "content hash mismatch"):
            build_promotion_result(
                self.promotion_program, self.learner_program, self.learner_execution,
                mutated, self.context, self.corrective, self.registry,
            )

    def test_forged_trace_is_rejected_by_authenticated_materializer(self):
        program = load(ROOT / "examples/learner05/corrective_handoff_0_5_1.tmg")
        from tomagi.core import run
        _, trace = run(program, trace=True)
        forged = copy.deepcopy(trace)
        forged[0]["lineage"] ^= 1
        with self.assertRaisesRegex(ValueError, "does not match deterministic replay"):
            materialize_trace(program, forged)

    def test_static_cross_backend_proof(self):
        proof = load_json("validation/learner052/promotion_authority.proof.json")
        self.assertTrue(verify_hash(proof))
        self.assertEqual(proof["status"], "pass")
        self.assertTrue(proof["python_c_complete_trace_equal"])
        self.assertTrue(proof["python_c_materialized_bytes_equal"])
        self.assertTrue(proof["independent_oracle_equals_formal_value"])
        self.assertEqual(proof["cell_count"], 242749)


if __name__ == "__main__":
    unittest.main()
