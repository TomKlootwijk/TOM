from __future__ import annotations

import copy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from tom_learner05.baseline import trusted_affine_learning_baseline
from tomagi.formal import (
    FormalValidationError,
    Limits,
    canonical_bytes,
    content_address,
    evaluate,
    run_program,
    verify_program_hash,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "examples/learner05/learner05_affine_authority.formal.json"
DATASETS = ROOT / "examples/learner05/datasets"
FIXTURE = ROOT / "validation/learner05/fixture_report.json"

AUTHORITY_LIMITS = Limits(
    max_steps=2_000_000,
    max_depth=192,
    max_collection_items=20_000,
    max_value_nodes=300_000,
    max_canonical_bytes=8_000_000,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def q_complexity(value: dict[str, int]) -> int:
    numerator = value["num"]
    denominator = value["den"]
    return (
        int(numerator < 0)
        + max(1, abs(numerator).bit_length())
        + denominator.bit_length()
    )


def model_complexity(coefficients: dict[str, dict[str, int]]) -> int:
    a = coefficients["a"]
    b = coefficients["b"]
    return (
        q_complexity(a)
        + q_complexity(b)
        + int(a != {"num": 0, "den": 1})
        + int(b != {"num": 0, "den": 1})
    )


def shifted(value: dict[str, int], offset: Fraction) -> dict[str, int]:
    result = Fraction(value["num"], value["den"]) + offset
    return {"num": result.numerator, "den": result.denominator}


class FormalLearnerAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset_paths = sorted(DATASETS.glob("*.json"))
        cls.datasets = [load_json(path) for path in cls.dataset_paths]
        cls.program = load_json(AUTHORITY)
        cls.execution = run_program(
            cls.program, {"datasets": cls.datasets}, limits=AUTHORITY_LIMITS
        )
        cls.value = cls.execution["value"]
        cls.rows = {row["dataset_id"]: row for row in cls.value["results"]}
        cls.baselines = {
            dataset["id"]: trusted_affine_learning_baseline(dataset)["semantic"]
            for dataset in cls.datasets
        }
        fixture = load_json(FIXTURE)
        cls.fixture = fixture
        cls.fixture_rows = {row["observation_set_id"]: row for row in fixture["results"]}
        cls.output_bytes = len(canonical_bytes(cls.value, limits=AUTHORITY_LIMITS))

    def test_static_program_is_canonical_and_content_addressed(self):
        raw = AUTHORITY.read_bytes()
        self.assertEqual(raw, canonical_bytes(self.program, limits=AUTHORITY_LIMITS) + b"\n")
        self.assertTrue(verify_program_hash(self.program, limits=AUTHORITY_LIMITS))
        self.assertEqual(
            self.program["content_hash"],
            "sha256:dd710388744a71861c90c15ef63bd85411f0652a2077f6f9ef9421997d626b28",
        )
        self.assertEqual(self.value["content_hash"], content_address({
            key: value for key, value in self.value.items() if key != "content_hash"
        }, limits=AUTHORITY_LIMITS))

    def test_all_19_rows_match_independent_baseline_and_fixture(self):
        expected_ids = [dataset["id"] for dataset in self.datasets]
        self.assertEqual(len(expected_ids), 19)
        self.assertEqual([row["dataset_id"] for row in self.value["results"]], expected_ids)
        self.assertEqual(
            self.value["inputs"],
            [{"id": dataset["id"], "content_hash": dataset["content_hash"]}
             for dataset in self.datasets],
        )

        for dataset in self.datasets:
            with self.subTest(dataset=dataset["id"]):
                row = self.rows[dataset["id"]]
                baseline = self.baselines[dataset["id"]]
                fixture = self.fixture_rows[dataset["id"]]

                self.assertEqual(row["dataset_content_hash"], dataset["content_hash"])
                self.assertEqual(row["split_ids"], baseline["splits"])
                self.assertEqual(
                    row["split_counts"],
                    {name: len(baseline["splits"][name])
                     for name in ("train", "validation", "holdout")},
                )
                self.assertEqual(row["candidate_count"], baseline["candidate_count"])
                self.assertEqual(
                    row["exact_training_candidate_count"],
                    baseline["exact_training_candidate_count"],
                )
                self.assertEqual(row["selected_coefficients"], baseline["selected_coefficients"])
                self.assertEqual(row["contradiction_count"], len(baseline["contradictions"]))
                self.assertEqual(row["accepted"], baseline["accepted"])

                if baseline["selected_coefficients"] is None:
                    expected_nonzero = {"train": None, "validation": None, "holdout": None}
                    self.assertIsNone(row["model_complexity"])
                else:
                    expected_nonzero = {
                        name: baseline["residual_summary"][name]["nonzero_count"]
                        for name in ("train", "validation", "holdout")
                    }
                    self.assertEqual(
                        row["model_complexity"],
                        model_complexity(baseline["selected_coefficients"]),
                    )
                self.assertEqual(row["residual_nonzero_counts"], expected_nonzero)

                self.assertEqual(row["candidate_count"], fixture["candidate_count"])
                self.assertEqual(row["selected_coefficients"], fixture["selected_coefficients"])
                self.assertEqual(row["contradiction_count"], fixture["contradiction_count"])
                self.assertEqual(row["accepted"], fixture["accepted"])
                self.assertEqual(row["accepted"], all(
                    check["passed"] for check in row["acceptance_checks"]
                ))
                self.assertEqual(
                    row["acceptance_reasons"],
                    [check["detail"] for check in row["acceptance_checks"] if not check["passed"]],
                )
                self.assertEqual(
                    row["content_hash"],
                    content_address({key: value for key, value in row.items()
                                     if key != "content_hash"}, limits=AUTHORITY_LIMITS),
                )

    def test_benchmark_totals_and_coefficient_recovery(self):
        self.assertEqual(self.value["accepted_count"], 12)
        self.assertEqual(self.value["rejected_count"], 7)
        self.assertEqual(self.fixture["accepted_count"], 12)
        self.assertEqual(self.fixture["negative_cases"], 7)
        self.assertEqual(self.fixture["false_promotions"], 0)

        expected_by_id = {
            case["id"]: case["expected"]
            for case in load_json(ROOT / "examples/learner05/benchmark_plan.json")["cases"]
        }
        coefficient_errors = 0
        for row in self.value["results"]:
            expected = expected_by_id[row["dataset_id"]]
            if expected["accepted"]:
                wanted = {
                    name: value if isinstance(value, dict) else {"num": value, "den": 1}
                    for name, value in (("a", expected["a"]), ("b", expected["b"]))
                }
                coefficient_errors += int(row["selected_coefficients"] != wanted)
        self.assertEqual(coefficient_errors, 0)

    def test_accepted_rows_emit_addressed_executable_sdf0_relations(self):
        accepted_rows = [row for row in self.value["results"] if row["accepted"]]
        self.assertEqual(len(accepted_rows), 12)
        datasets = {dataset["id"]: dataset for dataset in self.datasets}
        for row in accepted_rows:
            with self.subTest(dataset=row["dataset_id"]):
                definition = row["relation_definition"]
                body = {key: value for key, value in definition.items() if key != "content_hash"}
                self.assertEqual(
                    definition["content_hash"], content_address(body, limits=AUTHORITY_LIMITS)
                )
                self.assertEqual(definition["relation_interface"], "SDF0@Def")
                self.assertEqual(definition["coefficients"], row["selected_coefficients"])
                self.assertEqual(
                    definition["provenance"]["source_dataset_hash"],
                    row["dataset_content_hash"],
                )
                observation = datasets[row["dataset_id"]]["observations"][0]
                residual = evaluate(
                    definition["expression"],
                    {"t": observation["t"], "y": observation["y"]},
                    limits=AUTHORITY_LIMITS,
                )
                self.assertEqual(residual, {"num": 0, "den": 1})

        self.assertTrue(all(
            row["relation_definition"] is None
            for row in self.value["results"] if not row["accepted"]
        ))

    def test_value_mutation_cannot_change_split_ids(self):
        mutated = copy.deepcopy(self.datasets)
        for dataset_index, dataset in enumerate(mutated):
            observation = dataset["observations"][0]
            observation["t"] = shifted(observation["t"], Fraction(1000 + dataset_index, 97))
            observation["y"] = shifted(observation["y"], Fraction(-1000 - dataset_index, 101))

        mutated_run = run_program(
            self.program, {"datasets": mutated}, limits=AUTHORITY_LIMITS
        )["value"]
        mutated_rows = {row["dataset_id"]: row for row in mutated_run["results"]}
        for dataset_id, original in self.rows.items():
            self.assertEqual(mutated_rows[dataset_id]["split_ids"], original["split_ids"])

    def test_program_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.program)
        tampered["expression"]["message"] = "tampered authority"
        with self.assertRaisesRegex(FormalValidationError, "content hash mismatch"):
            run_program(tampered, {"datasets": self.datasets}, limits=AUTHORITY_LIMITS)

    def test_observed_budget_is_deterministic_and_reported(self):
        self.assertEqual(self.execution["steps"], 131_478)
        self.assertEqual(self.output_bytes, 77_832)


if __name__ == "__main__":
    unittest.main()
