from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples/learner06"
VAL = ROOT / "validation/learner06"

from tom_learner06.oracle import OracleError, evaluate_all, evaluate_dataset
from tomagi.canonical import content_hash, verify_hash
from tomagi.immutable_store import ImmutablePublicationStore, validate_plan


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rehash(record: dict) -> None:
    record.pop("content_hash", None)
    record["content_hash"] = content_hash(record)


class Learner06FamilyRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load(BASE / "family_registry.json")
        cls.partition = load(BASE / "partition_policy.json")
        cls.prior = load(BASE / "prior_authority.json")
        cls.bundle = load(BASE / "dataset_bundle.json")
        cls.datasets = cls.bundle["datasets"]
        cls.result = load(VAL / "learner_authority.direct.json")
        cls.rows = {row["dataset_id"]: row for row in cls.result["value"]["results"]}
        cls.promotion = load(VAL / "promotion_authority.direct.json")

    def test_registry_and_datasets_validate_under_strict_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        registry_schema = load(ROOT / "spec/tom_learner_family_registry_0_6.schema.json")
        dataset_schema = load(ROOT / "spec/tom_learner_dataset_0_6.schema.json")
        jsonschema.Draft202012Validator(registry_schema).validate(self.registry)
        for dataset in self.datasets:
            jsonschema.Draft202012Validator(dataset_schema).validate(dataset)

    def test_all_authority_records_are_content_addressed(self):
        self.assertTrue(verify_hash(self.registry))
        self.assertTrue(verify_hash(self.partition))
        self.assertTrue(verify_hash(self.prior))
        self.assertTrue(verify_hash(self.bundle))
        for family in self.registry["families"]:
            self.assertTrue(verify_hash(family), family["id"])
            for candidate in family["candidates"]:
                self.assertTrue(verify_hash(candidate), candidate["id"])
        for dataset in self.datasets:
            self.assertTrue(verify_hash(dataset), dataset["id"])
            self.assertTrue(verify_hash(dataset["assignment_basis"]))
            self.assertEqual(dataset["partitions"], dataset["assignment_basis"]["partitions"])
            for observation in dataset["observations"]:
                self.assertTrue(verify_hash(observation), observation["id"])

    def test_finite_family_registry_has_declared_counts_and_budgets(self):
        expected = {
            "family:polynomial:0.2": 34,
            "family:piecewise-affine:0.2": 21,
            "family:transition-table:0.2": 27,
            "family:expression-tree:0.2": 39,
        }
        actual = {family["id"]: len(family["candidates"]) for family in self.registry["families"]}
        self.assertEqual(actual, expected)
        self.assertEqual(self.registry["family_order"], [family["id"] for family in self.registry["families"]])
        for family in self.registry["families"]:
            self.assertLessEqual(len(family["candidates"]), family["search_budget"]["max_candidates"])

    def test_benchmark_outcomes_are_explicit_and_no_false_promotion_occurs(self):
        value = self.result["value"]
        self.assertEqual(value["dataset_count"], 16)
        self.assertEqual(value["accepted_count"], {"num": 9, "den": 1})
        self.assertEqual(value["rejected_count"], {"num": 7, "den": 1})
        self.assertEqual(value["ambiguity_count"], {"num": 3, "den": 1})
        expected = load(BASE / "benchmark_oracle.json")["expected"]
        for dataset_id, oracle in expected.items():
            row = self.rows[dataset_id]
            self.assertEqual(row["accepted"], oracle["accepted"], dataset_id)
            self.assertEqual(row["reason"], oracle["reason"], dataset_id)
            if oracle["accepted"]:
                self.assertEqual(row["selected_family"], oracle["selected_family"], dataset_id)

    def test_ambiguity_is_recorded_instead_of_tie_broken(self):
        expected_survivors = {
            "dataset:piecewise-ambiguity": 3,
            "dataset:expr-identity-ambiguity": 2,
            "dataset:cross-family-ambiguity": 2,
        }
        for dataset_id, count in expected_survivors.items():
            row = self.rows[dataset_id]
            self.assertFalse(row["accepted"])
            self.assertEqual(row["reason"], "ambiguous-train-survivors")
            self.assertIsNone(row["selected_candidate"])
            self.assertEqual(len(row["survivor_hashes"]), count)
            self.assertIsNotNone(row["ambiguity_record"])
            self.assertEqual(row["ambiguity_record"]["candidate_hashes"], row["survivor_hashes"])
            self.assertEqual(row["ambiguity_record"]["resolution"], "reject-without-hidden-tie-break")

    def test_supersession_requires_regression_impact_certificate(self):
        accepted = self.rows["dataset:poly-affine-supersession"]
        rejected = self.rows["dataset:supersession-regression-failure"]
        self.assertTrue(accepted["accepted"])
        self.assertIsNotNone(accepted["supersession_record"])
        self.assertTrue(accepted["regression_impact"]["all_pass"])
        self.assertFalse(rejected["accepted"])
        self.assertEqual(rejected["reason"], "regression-impact")
        self.assertFalse(rejected["regression_impact"]["all_pass"])
        self.assertIsNone(rejected["supersession_record"])

    def test_validation_target_mutation_does_not_change_training_selection(self):
        original = next(d for d in self.datasets if d["id"] == "dataset:poly-quadratic")
        original_result = evaluate_dataset(original, self.registry, self.prior)
        mutated = copy.deepcopy(original)
        validation_id = mutated["partitions"]["validation"][0]
        observation = next(row for row in mutated["observations"] if row["id"] == validation_id)
        observation["target"] = {"num": 999, "den": 1}
        rehash(observation)
        rehash(mutated)
        result = evaluate_dataset(mutated, self.registry, self.prior)
        self.assertEqual(result["fit_input_hash"], original_result["fit_input_hash"])
        self.assertEqual(result["selected_candidate_hash"], original_result["selected_candidate_hash"])
        self.assertEqual(result["survivor_hashes"], original_result["survivor_hashes"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "validation-counterexample")

    def test_holdout_target_mutation_does_not_change_training_selection(self):
        original = next(d for d in self.datasets if d["id"] == "dataset:expr-abs")
        original_result = evaluate_dataset(original, self.registry, self.prior)
        mutated = copy.deepcopy(original)
        holdout_id = mutated["partitions"]["holdout"][0]
        observation = next(row for row in mutated["observations"] if row["id"] == holdout_id)
        observation["target"] = {"num": 999, "den": 1}
        rehash(observation)
        rehash(mutated)
        result = evaluate_dataset(mutated, self.registry, self.prior)
        self.assertEqual(result["fit_input_hash"], original_result["fit_input_hash"])
        self.assertEqual(result["selected_candidate_hash"], original_result["selected_candidate_hash"])
        self.assertEqual(result["survivor_hashes"], original_result["survivor_hashes"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "holdout-counterexample")

    def test_independent_oracle_matches_formal_authority(self):
        comparison = load(VAL / "oracle_comparison.json")
        self.assertTrue(verify_hash(comparison))
        self.assertTrue(comparison["all_equal"])
        self.assertEqual(comparison["dataset_count"], 16)
        self.assertEqual(comparison["accepted_count"], 9)
        self.assertEqual(comparison["rejected_count"], 7)
        self.assertEqual(comparison["ambiguity_count"], 3)

    def test_candidate_budget_overflow_rejects(self):
        bad = copy.deepcopy(self.registry)
        family = bad["families"][0]
        family["search_budget"]["max_candidates"] = len(family["candidates"]) - 1
        rehash(family)
        rehash(bad)
        with self.assertRaisesRegex(OracleError, "exceeds declared search budget"):
            evaluate_dataset(self.datasets[0], bad, self.prior)

    def test_formal_results_equal_authenticated_tomagi_materialization(self):
        self.assertEqual(
            (VAL / "learner_authority.direct.json").read_bytes(),
            (VAL / "learner_authority.materialized.json").read_bytes(),
        )
        self.assertEqual(
            (VAL / "promotion_authority.direct.json").read_bytes(),
            (VAL / "promotion_authority.materialized.json").read_bytes(),
        )
        learner_proof = load(VAL / "learner_authority_proof.json")
        promotion_proof = load(VAL / "promotion_authority_proof.json")
        release_proof = load(VAL / "learner06_release_artifact.proof.json")
        self.assertTrue(verify_hash(learner_proof) and learner_proof["status"] == "pass")
        self.assertTrue(verify_hash(promotion_proof) and promotion_proof["status"] == "pass")
        self.assertTrue(verify_hash(release_proof) and release_proof["status"] == "pass")
        self.assertTrue(learner_proof["tomagi_chain"]["execution"]["python_c_full_trace_equal"])
        self.assertTrue(promotion_proof["tomagi_chain"]["execution"]["python_c_full_trace_equal"])
        self.assertEqual(release_proof["family_registry_hash"], self.registry["content_hash"])
        self.assertEqual(release_proof["learner_proof_hash"], learner_proof["content_hash"])
        self.assertEqual(release_proof["promotion_proof_hash"], promotion_proof["content_hash"])

    def test_continuation_plan_and_store_reconstruct_from_pinned_parent(self):
        plan = validate_plan(self.promotion["value"]["publication_plan"])
        self.assertEqual(plan["schema"], "TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.1")
        self.assertEqual(plan["initial_head"], load(BASE / "prior_authority.json")["prior_terminal_head"])
        self.assertEqual([p["sequence"] for p in plan["publications"]], list(range(20, 36)))
        audit = ImmutablePublicationStore(BASE / "promotion_store").audit_plan(plan)
        self.assertTrue(audit["valid"], audit["errors"])
        reconstruction = load(VAL / "promotion_store_reconstruction.json")
        self.assertTrue(verify_hash(reconstruction))
        self.assertEqual(reconstruction["commit_count"], 16)
        self.assertEqual(reconstruction["accepted_count"], 9)
        self.assertEqual(reconstruction["rejected_count"], 7)

    def test_source_generator_is_byte_deterministic(self):
        paths = [
            BASE / "family_registry.json",
            BASE / "partition_policy.json",
            BASE / "dataset_bundle.json",
            BASE / "learner06_family_authority.formal.json",
            BASE / "learner06_family_authority.literal.json",
            BASE / "learner06_promotion_authority.formal.json",
        ]
        before = {path: path.read_bytes() for path in paths}
        subprocess.run(
            [sys.executable, "tools/generate_learner06_sources.py"],
            cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
        )
        self.assertEqual(before, {path: path.read_bytes() for path in paths})

    def test_repair_handoff_proof_is_preserved(self):
        proof = load(BASE / "repair_handoff_proof.json")
        self.assertTrue(verify_hash(proof))
        self.assertEqual(proof["status"], "pass")
        self.assertTrue(proof["execution"]["python_c_full_trace_equal"])
        self.assertTrue(proof["execution"]["python_c_emit_sequence_equal"])


if __name__ == "__main__":
    unittest.main()
