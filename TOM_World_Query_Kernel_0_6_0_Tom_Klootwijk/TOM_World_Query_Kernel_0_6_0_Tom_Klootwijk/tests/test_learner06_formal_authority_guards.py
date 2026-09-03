from __future__ import annotations

import copy
import json
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import content_hash, verify_hash
from tomagi.formal import (
    FormalAssertionError,
    Limits,
    run_program,
    verify_program_hash,
)
from tomagi.immutable_store import validate_plan


GENERATOR = runpy.run_path(str(ROOT / "tools/generate_learner06_sources.py"))
BUILD_REGISTRY = GENERATOR["build_registry"]
BUILD_PRIOR_AUTHORITY = GENERATOR["build_prior_authority"]
BUILD_DATASETS = GENERATOR["build_datasets"]
BUILD_LEARNER_PROGRAM = GENERATOR["build_learner_program"]
BUILD_DATASET_BUNDLE = GENERATOR["build_dataset_bundle"]
BUILD_PROMOTION_CONTEXT = GENERATOR["build_promotion_context"]
BUILD_PROMOTION_PROGRAM = GENERATOR["build_promotion_program"]

LIMITS = Limits(
    max_steps=4_000_000,
    max_depth=256,
    max_collection_items=20_000,
    max_value_nodes=4_000_000,
    max_canonical_bytes=16_000_000,
)
WRONG_HASH = "sha256:" + "00" * 32


def rehash(record: dict) -> None:
    record["content_hash"] = content_hash(record)


class Learner06FormalAuthorityGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry, cls.partition_policy = BUILD_REGISTRY()
        cls.prior = BUILD_PRIOR_AUTHORITY()
        generated_datasets, _ = BUILD_DATASETS(cls.partition_policy, cls.prior)
        # Two accepted data sets keep guard tests quick while retaining an order
        # that can be deliberately reversed at the promotion boundary.
        cls.datasets = copy.deepcopy(generated_datasets[:2])
        cls.repair_proof = json.loads(
            (ROOT / "sources/codex_0_5_2_repair/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json")
            .read_text(encoding="utf-8")
        )
        cls.learner_program = BUILD_LEARNER_PROGRAM(len(cls.datasets))
        cls.learner_result = cls.run_learner()
        cls.bundle = BUILD_DATASET_BUNDLE(copy.deepcopy(cls.datasets))
        cls.context = BUILD_PROMOTION_CONTEXT(cls.registry, cls.bundle, cls.prior)
        cls.promotion_program = BUILD_PROMOTION_PROGRAM(
            len(cls.datasets),
            cls.learner_program["content_hash"],
            cls.learner_result["content_hash"],
        )
        cls.promotion_result = cls.run_promotion()

    @classmethod
    def run_learner(
        cls,
        *,
        registry: dict | None = None,
        datasets: list[dict] | None = None,
        repair_proof: dict | None = None,
    ) -> dict:
        selected_datasets = cls.datasets if datasets is None else datasets
        sequence = [
            cls.registry if registry is None else registry,
            cls.partition_policy,
            *selected_datasets,
            cls.prior,
            cls.repair_proof if repair_proof is None else repair_proof,
        ]
        return run_program(
            cls.learner_program,
            {"learner06_inputs": sequence},
            limits=LIMITS,
        )

    @classmethod
    def run_promotion(
        cls,
        *,
        promotion_program: dict | None = None,
        learner_result: dict | None = None,
        registry: dict | None = None,
        context: dict | None = None,
        bundle: dict | None = None,
    ) -> dict:
        selected_program = cls.promotion_program if promotion_program is None else promotion_program
        sequence = [
            cls.learner_result if learner_result is None else learner_result,
            cls.prior,
            cls.registry if registry is None else registry,
            cls.partition_policy,
            cls.repair_proof,
            cls.context if context is None else context,
            cls.bundle if bundle is None else bundle,
        ]
        return run_program(
            selected_program,
            {"promotion06_inputs": sequence},
            limits=LIMITS,
        )

    def assert_dataset_rejected(self, dataset: dict) -> None:
        datasets = [dataset, copy.deepcopy(self.datasets[1])]
        with self.assertRaises(FormalAssertionError):
            self.run_learner(datasets=datasets)

    def test_generator_built_baselines_execute(self):
        self.assertTrue(verify_program_hash(self.learner_program, limits=LIMITS))
        self.assertTrue(verify_program_hash(self.promotion_program, limits=LIMITS))
        self.assertEqual(self.learner_result["value"]["dataset_count"], 2)
        self.assertEqual(self.promotion_result["value"]["publication_count"], 2)
        self.assertEqual(
            validate_plan(self.promotion_result["value"]["publication_plan"])["terminal_head"],
            self.promotion_result["value"]["terminal_head"],
        )

    def test_rehashed_registry_budget_mutation_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        family = registry["families"][0]
        family["search_budget"]["max_candidates"] += 1
        rehash(family)
        rehash(registry)
        self.assertTrue(verify_hash(family) and verify_hash(registry))
        with self.assertRaises(FormalAssertionError):
            self.run_learner(registry=registry)

    def test_unknown_expression_operation_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        family = next(
            family for family in registry["families"]
            if family["id"] == "family:expression-tree:0.2"
        )
        candidate = family["candidates"][0]
        candidate["tree"]["op"] = "undeclared-operation"
        rehash(candidate)
        rehash(family)
        rehash(registry)
        self.assertTrue(verify_hash(candidate) and verify_hash(family) and verify_hash(registry))
        with self.assertRaises(FormalAssertionError):
            self.run_learner(registry=registry)

    def test_schema_invalid_identifiers_and_supersedes_are_rejected(self):
        registry = copy.deepcopy(self.registry)
        candidate = registry["families"][0]["candidates"][0]
        candidate["id"] = ["not", "a", "string"]
        rehash(candidate)
        rehash(registry["families"][0])
        rehash(registry)
        with self.assertRaises(FormalAssertionError):
            self.run_learner(registry=registry)

        dataset_id = copy.deepcopy(self.datasets[0])
        dataset_id["id"] = ["not", "a", "string"]
        dataset_id["assignment_basis"]["dataset_id"] = copy.deepcopy(dataset_id["id"])
        rehash(dataset_id["assignment_basis"])
        rehash(dataset_id)
        self.assert_dataset_rejected(dataset_id)

        observation_id = copy.deepcopy(self.datasets[0])
        old_id = observation_id["observations"][0]["id"]
        new_id = ["not", "a", "string"]
        observation_id["observations"][0]["id"] = new_id
        for partition_ids in observation_id["partitions"].values():
            for index, value in enumerate(partition_ids):
                if value == old_id:
                    partition_ids[index] = copy.deepcopy(new_id)
        observation_id["assignment_basis"]["partitions"] = copy.deepcopy(
            observation_id["partitions"]
        )
        rehash(observation_id["observations"][0])
        rehash(observation_id["assignment_basis"])
        rehash(observation_id)
        self.assert_dataset_rejected(observation_id)

        supersedes = copy.deepcopy(self.datasets[0])
        supersedes["supersedes"] = 7
        rehash(supersedes)
        self.assert_dataset_rejected(supersedes)

    def test_dataset_membership_and_assignment_guards(self):
        cases: dict[str, dict] = {}

        unresolved = copy.deepcopy(self.datasets[0])
        unresolved["partitions"]["train"][0] = "observation:missing"
        unresolved["assignment_basis"]["partitions"] = copy.deepcopy(unresolved["partitions"])
        rehash(unresolved["assignment_basis"])
        rehash(unresolved)
        cases["unresolved partition ID"] = unresolved

        duplicate = copy.deepcopy(self.datasets[0])
        duplicate["observations"].append(copy.deepcopy(duplicate["observations"][0]))
        rehash(duplicate)
        cases["duplicate observation ID"] = duplicate

        overlap = copy.deepcopy(self.datasets[0])
        overlap["partitions"]["train"].append(overlap["partitions"]["validation"][0])
        overlap["assignment_basis"]["partitions"] = copy.deepcopy(overlap["partitions"])
        rehash(overlap["assignment_basis"])
        rehash(overlap)
        cases["overlapping partitions"] = overlap

        assignment_mismatch = copy.deepcopy(self.datasets[0])
        assignment_mismatch["partitions"]["train"] = list(
            reversed(assignment_mismatch["partitions"]["train"])
        )
        rehash(assignment_mismatch)
        cases["assignment mismatch"] = assignment_mismatch

        undeclared_family = copy.deepcopy(self.datasets[0])
        undeclared_family["eligible_families"] = ["family:not-declared:0.2"]
        rehash(undeclared_family)
        cases["undeclared eligible family"] = undeclared_family

        for name, dataset in cases.items():
            with self.subTest(name=name):
                self.assertTrue(verify_hash(dataset))
                self.assert_dataset_rejected(dataset)

    def test_declared_partition_order_controls_training_resolution(self):
        dataset = copy.deepcopy(self.datasets[0])
        dataset["partitions"]["train"] = list(reversed(dataset["partitions"]["train"]))
        dataset["assignment_basis"]["partitions"] = copy.deepcopy(dataset["partitions"])
        rehash(dataset["assignment_basis"])
        rehash(dataset)

        result = self.run_learner(datasets=[dataset, copy.deepcopy(self.datasets[1])])
        row = result["value"]["results"][0]
        declared_ids = dataset["partitions"]["train"]
        observations = {item["id"]: item for item in dataset["observations"]}
        expected_fit_hash = content_hash({
            "schema": "TOM-LEARNER-0.2-TRAIN-FIT-INPUT-1.0",
            "dataset_id": dataset["id"],
            "family_registry_hash": self.registry["content_hash"],
            "eligible_families": dataset["eligible_families"],
            "train_observations": [observations[item]["content_hash"] for item in declared_ids],
        })
        self.assertEqual(row["split_ids"]["train"], declared_ids)
        self.assertEqual(row["derivation_evidence"]["train_ids"], declared_ids)
        self.assertEqual(row["derivation_evidence"]["fit_input_hash"], expected_fit_hash)

    def test_failed_repair_proof_is_rejected_even_when_rehashed(self):
        repair_proof = copy.deepcopy(self.repair_proof)
        repair_proof["status"] = "fail"
        rehash(repair_proof)
        self.assertTrue(verify_hash(repair_proof))
        with self.assertRaises(FormalAssertionError):
            self.run_learner(repair_proof=repair_proof)

    def test_promotion_context_bindings_are_enforced(self):
        mutations = {
            "seed": ("seed_sha256", WRONG_HASH),
            "parent": ("expected_parent", WRONG_HASH),
            "registry": ("family_registry_hash", WRONG_HASH),
            "bundle": ("dataset_bundle_hash", WRONG_HASH),
            "order": ("dataset_order", list(reversed(self.context["dataset_order"]))),
        }
        for name, (field, value) in mutations.items():
            with self.subTest(name=name):
                context = copy.deepcopy(self.context)
                context[field] = value
                rehash(context)
                self.assertTrue(verify_hash(context))
                with self.assertRaises(FormalAssertionError):
                    self.run_promotion(context=context)

    def test_promotion_rejects_learner_result_registry_mismatch(self):
        learner_result = copy.deepcopy(self.learner_result)
        learner_result["value"]["family_registry_hash"] = WRONG_HASH
        rehash(learner_result["value"])
        rehash(learner_result)
        promotion_program = BUILD_PROMOTION_PROGRAM(
            len(self.datasets),
            self.learner_program["content_hash"],
            learner_result["content_hash"],
        )
        self.assertTrue(verify_hash(learner_result["value"]))
        self.assertTrue(verify_hash(learner_result))
        with self.assertRaises(FormalAssertionError):
            self.run_promotion(
                promotion_program=promotion_program,
                learner_result=learner_result,
            )


if __name__ == "__main__":
    unittest.main()
