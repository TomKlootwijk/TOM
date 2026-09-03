from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

from tom_world03.canonical import attach_hash, canonical_bytes, content_hash, verify_hash
from tom_world03.rational import Q
from tom_learner05.affine import candidate_coefficients
from tom_learner05.baseline import trusted_affine_learning_baseline
from tom_learner05.handoff import verify_corrective_handoff, verify_literal_handoff
from tom_learner05.io import load_observation_set
from tom_learner05.learner import learn_observation_set
from tom_learner05.model import (
    BASE_HANDOFF_HASH, BASE_WORLD_HASH, CANONICAL_SEED_SHA256, ObservationSet,
)
from tom_learner05.split import deterministic_split
from tom_learner05.store import LearnerStore

DATASET_DIR = ROOT / "examples/learner05/datasets"
VALIDATION = ROOT / "validation/learner05"
CORRECTIVE_HANDOFF = ROOT / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"
BASE_0_5_1_AUTHORITY = ROOT / "sources/base_0_5_1_authority_tree"


def load_dataset(name: str) -> tuple[dict, ObservationSet]:
    return load_observation_set(DATASET_DIR / f"dataset_{name}.json")


def selected_coefficients(run) -> dict | None:
    wanted = run.selection.get("selected_candidate_hash")
    if wanted is None:
        return None
    candidate = next(item for item in run.candidates if item["content_hash"] == wanted)
    a, b = candidate_coefficients(candidate)
    return {"a": a.to_record(), "b": b.to_record()}


def rehash(record: dict) -> None:
    record["content_hash"] = content_hash(record)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def copy_pristine_base(destination: Path) -> dict:
    handoff = json.loads((ROOT / "sources/TOM_LITERAL_HANDOFF_0_4_2.json").read_text())
    corrective = json.loads(CORRECTIVE_HANDOFF.read_text())
    prior_by_path = {item["path"]: item["prior_copy"] for item in corrective["replacements"]}
    copy_file(BASE_0_5_1_AUTHORITY / "sources/TOM_LITERAL_HANDOFF_0_4_2.json",
              destination / "sources/TOM_LITERAL_HANDOFF_0_4_2.json")
    copy_file(BASE_0_5_1_AUTHORITY / "TOM_seed_genome_2026-09-01.txt",
              destination / "TOM_seed_genome_2026-09-01.txt")
    for item in handoff["authoritative_files"]:
        relative = item["path"]
        source_relative = prior_by_path.get(relative, relative)
        copy_file(BASE_0_5_1_AUTHORITY / source_relative, destination / relative)
    return handoff


def copy_corrective_tree(destination: Path) -> dict:
    handoff = json.loads((ROOT / "sources/TOM_LITERAL_HANDOFF_0_4_2.json").read_text())
    corrective = json.loads(CORRECTIVE_HANDOFF.read_text())
    copy_file(BASE_0_5_1_AUTHORITY / "sources/TOM_LITERAL_HANDOFF_0_4_2.json",
              destination / "sources/TOM_LITERAL_HANDOFF_0_4_2.json")
    copy_file(BASE_0_5_1_AUTHORITY / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json",
              destination / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json")
    copy_file(BASE_0_5_1_AUTHORITY / "TOM_seed_genome_2026-09-01.txt",
              destination / "TOM_seed_genome_2026-09-01.txt")
    for item in handoff["authoritative_files"]:
        copy_file(BASE_0_5_1_AUTHORITY / item["path"], destination / item["path"])
    for item in corrective["replacements"]:
        copy_file(BASE_0_5_1_AUTHORITY / item["prior_copy"], destination / item["prior_copy"])
    for item in corrective["additions"]:
        copy_file(BASE_0_5_1_AUTHORITY / item["path"], destination / item["path"])
    return corrective


class LiteralHandoffTests(unittest.TestCase):
    def test_corrective_handoff_verifies_pinned_0_5_1_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_corrective_tree(base)
            record = verify_corrective_handoff(base)
        self.assertTrue(record["valid"], record["errors"])
        self.assertEqual(record["base_handoff_hash"], BASE_HANDOFF_HASH)
        self.assertEqual(record["base_authoritative_file_count"], 47)
        self.assertEqual(record["unchanged_base_file_count"], 44)
        self.assertEqual(record["replacement_count"], 3)
        self.assertEqual(record["addition_count"], 7)
        self.assertTrue(all(item["equal"] for item in record["unchanged_files"]))
        self.assertTrue(all(item["base_binding_equal"] and item["prior_bytes_equal"]
                            and item["corrective_bytes_equal"] for item in record["replacements"]))
        self.assertTrue(all(item["equal"] for item in record["additions"]))

    def test_legacy_handoff_still_verifies_a_pristine_base_tree(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_pristine_base(base)
            record = verify_literal_handoff(base)
            self.assertTrue(record["valid"], record["errors"])
            self.assertEqual(record["handoff_hash"], BASE_HANDOFF_HASH)
            self.assertEqual(record["authoritative_file_count"], 47)
            self.assertTrue(all(item["equal"] for item in record["files"]))

    def test_handoff_detects_authoritative_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = copy_pristine_base(base)
            self.assertTrue(verify_literal_handoff(base)["valid"])
            target = base / source["authoritative_files"][1]["path"]
            target.write_bytes(target.read_bytes() + b"x")
            result = verify_literal_handoff(base)
            self.assertFalse(result["valid"])
            self.assertTrue(any("mismatch" in error for error in result["errors"]))

    def test_corrective_handoff_detects_addition_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            corrective = copy_corrective_tree(base)
            self.assertTrue(verify_corrective_handoff(base)["valid"])
            target = base / corrective["additions"][0]["path"]
            target.write_bytes(target.read_bytes() + b"x")
            result = verify_corrective_handoff(base)
            self.assertFalse(result["valid"])
            self.assertTrue(any("corrective addition bytes mismatch" in error
                                for error in result["errors"]))

    def test_base_0_4_1_validation_identity_is_pinned(self):
        record = json.loads((ROOT / "validation/world04r/validation_report.json").read_text())
        self.assertEqual(record["status"], "pass")
        self.assertEqual(record["test_count"], 144)
        self.assertEqual(record["failure_count"], 0)
        self.assertEqual(record["semantic_chain_sha256"],
                         "sha256:9fd4f3e1ae8550ae3ca99e27e7bf61b22a4935fe764fd443723abfdb3804f226")
        self.assertEqual(record["content_hash"],
                         "sha256:57be1528d1759c5469259a71daa6f0118b006a1f6a38f9d205f29d3230308391")

    def test_superseded_authority_pattern_is_absent(self):
        world = json.loads((ROOT / "examples/world04r/piecewise_world.json").read_text())
        self.assertNotIn("continuation_until", json.dumps(world, sort_keys=True))
        self.assertFalse((ROOT / "src/python/tom_world04").exists())
        self.assertTrue((ROOT / "src/python/tom_world04r").is_dir())


class DatasetAndSplitTests(unittest.TestCase):
    def test_all_literal_datasets_roundtrip_and_hash(self):
        for path in sorted(DATASET_DIR.glob("*.json")):
            raw, dataset = load_observation_set(path)
            self.assertEqual(canonical_bytes(raw), canonical_bytes(dataset.to_record()))
            self.assertTrue(verify_hash(raw))
            self.assertEqual(dataset.seed_sha256, CANONICAL_SEED_SHA256)
            self.assertEqual(dataset.base_world_hash, BASE_WORLD_HASH)
            self.assertEqual(dataset.base_handoff_hash, BASE_HANDOFF_HASH)

    def test_schema_validates_every_dataset(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema unavailable")
        schema = json.loads((ROOT / "spec/tom_learner_affine_0_5.schema.json").read_text())
        for path in sorted(DATASET_DIR.glob("*.json")):
            jsonschema.Draft202012Validator(schema).validate(json.loads(path.read_text()))

    def test_split_is_id_only_and_has_declared_counts(self):
        raw, dataset = load_dataset("clean_double")
        first = deterministic_split(dataset)
        self.assertFalse(first["assignment_uses_values"])
        self.assertEqual(first["counts"], {"train": 12, "validation": 4, "holdout": 4})
        target = first["splits"]["holdout"][0]
        changed = copy.deepcopy(raw)
        item = next(item for item in changed["observations"] if item["id"] == target)
        item["y"] = {"num": 999999, "den": 1}
        rehash(item)
        rehash(changed)
        second = deterministic_split(ObservationSet.from_record(changed))
        self.assertEqual(first["splits"], second["splits"])
        self.assertEqual(first["assignment_basis_hash"], second["assignment_basis_hash"])

    def test_unsorted_observations_reject(self):
        raw, _ = load_dataset("clean_double")
        raw["observations"] = list(reversed(raw["observations"]))
        rehash(raw)
        with self.assertRaisesRegex(ValueError, "sorted"):
            ObservationSet.from_record(raw)

    def test_duplicate_observation_id_rejects(self):
        raw, _ = load_dataset("clean_double")
        raw["observations"][1] = copy.deepcopy(raw["observations"][0])
        rehash(raw)
        with self.assertRaisesRegex(ValueError, "unique"):
            ObservationSet.from_record(raw)

    def test_wrong_root_bindings_reject(self):
        raw, _ = load_dataset("clean_double")
        for field in ("seed_sha256", "base_world_hash", "base_handoff_hash"):
            bad = copy.deepcopy(raw)
            bad[field] = ("0" * 64) if field == "seed_sha256" else "sha256:" + "0" * 64
            rehash(bad)
            with self.assertRaises(ValueError):
                ObservationSet.from_record(bad)

    def test_nested_hash_mutation_rejects(self):
        raw, _ = load_dataset("clean_double")
        raw["observations"][0]["y"] = {"num": 500, "den": 1}
        rehash(raw)
        with self.assertRaisesRegex(ValueError, "observation content hash mismatch"):
            ObservationSet.from_record(raw)


class LearningSemanticsTests(unittest.TestCase):
    def test_fixture_binds_corrective_handoff_verification(self):
        report = json.loads((VALIDATION / "fixture_report.json").read_text())
        verification = json.loads((VALIDATION / "corrective_handoff_verification.json").read_text())
        self.assertTrue(verify_hash(report))
        self.assertTrue(verify_hash(verification))
        self.assertTrue(verification["valid"], verification["errors"])
        self.assertEqual(report["corrective_handoff_verification_hash"], verification["content_hash"])
        self.assertEqual(report["corrective_handoff_hash"], verification["corrective_handoff_hash"])

    def test_twelve_clean_affine_cases_are_exactly_recovered(self):
        report = json.loads((VALIDATION / "fixture_report.json").read_text())
        clean = [row for row in report["results"] if row["expected_accepted"]]
        self.assertEqual(len(clean), 12)
        for row in clean:
            self.assertTrue(row["accepted"], row["observation_set_id"])
            self.assertEqual(row["selected_coefficients"], row["expected_coefficients"])
            self.assertEqual(row["counterexample_count"], 0)
            self.assertTrue(row["baseline_equal"])

    def test_all_seven_negative_cases_are_rejected(self):
        report = json.loads((VALIDATION / "fixture_report.json").read_text())
        negative = [row for row in report["results"] if not row["expected_accepted"]]
        self.assertEqual(len(negative), 7)
        self.assertTrue(all(not row["accepted"] for row in negative))
        self.assertEqual(report["false_promotions"], 0)

    def test_validation_and_holdout_outliers_do_not_change_fit(self):
        _, clean = load_dataset("clean_double")
        clean_run = learn_observation_set(clean)
        for name in ("validation_outlier", "holdout_outlier"):
            _, outlier = load_dataset(name)
            run = learn_observation_set(outlier)
            # Dataset and observation IDs differ in these frozen named cases.
            # The dedicated same-ID leakage certificate below proves assignment
            # and fit-input invariance.  Here we confirm the train-only model
            # semantics and the independent acceptance gates.
            self.assertEqual(selected_coefficients(run), {"a": {"num": 2, "den": 1}, "b": {"num": 1, "den": 1}})
            self.assertFalse(run.accepted)
            self.assertEqual(len(run.counterexamples), 1)

    def test_mutation_leakage_certificate_passes(self):
        record = json.loads((VALIDATION / "leakage_certificate.json").read_text())
        self.assertTrue(record["valid"])
        for probe in record["probes"]:
            self.assertTrue(probe["split_ids_equal"])
            self.assertTrue(probe["assignment_basis_hash_equal"])
            self.assertTrue(probe["fit_input_hash_equal"])
            self.assertTrue(probe["selected_coefficients_equal"])
            self.assertFalse(probe["mutated_accepted"])

    def test_train_outlier_has_no_exact_training_candidate(self):
        _, dataset = load_dataset("train_outlier")
        run = learn_observation_set(dataset)
        self.assertFalse(run.accepted)
        self.assertIsNone(run.selection["selected_candidate_hash"])
        self.assertGreater(run.selection["candidate_count"], 1)
        self.assertEqual(run.selection["exact_training_candidate_count"], 0)

    def test_contradiction_is_retained_and_blocks_promotion(self):
        _, dataset = load_dataset("contradictory_exact")
        run = learn_observation_set(dataset)
        self.assertFalse(run.accepted)
        self.assertEqual(len(run.contradictions), 1)
        self.assertIsNotNone(run.rejection_lineage)
        self.assertEqual(run.rejection_lineage["contradiction_hashes"], [run.contradictions[0]["content_hash"]])

    def test_underdetermined_data_produce_no_candidate(self):
        _, dataset = load_dataset("underdetermined_constant_input")
        run = learn_observation_set(dataset)
        self.assertFalse(run.accepted)
        self.assertEqual(len(run.candidates), 0)
        self.assertIn("no candidate", run.selection["reason"])

    def test_complexity_gate_blocks_exact_large_model(self):
        _, dataset = load_dataset("complexity_rejected")
        run = learn_observation_set(dataset)
        self.assertFalse(run.accepted)
        self.assertIsNotNone(run.selection["selected_candidate_hash"])
        self.assertTrue(any(check["name"] == "model complexity" and not check["passed"] for check in run.decision["checks"]))

    def test_learned_definition_exposes_sdf0_relation(self):
        _, dataset = load_dataset("clean_half")
        run = learn_observation_set(dataset)
        definition = run.learned_definition
        self.assertIsNotNone(definition)
        self.assertEqual(definition["relation_interface"], "SDF0@Def")
        self.assertEqual(definition["coefficients"], {"a": {"num": 1, "den": 2}, "b": {"num": -3, "den": 2}})
        self.assertEqual(definition["base_handoff_hash"], BASE_HANDOFF_HASH)
        self.assertTrue(verify_hash(definition))

    def test_independent_fraction_baseline_matches_every_case(self):
        comparison = json.loads((VALIDATION / "baseline_comparison.json").read_text())
        self.assertTrue(comparison["all_equal"])
        self.assertEqual(comparison["dataset_count"], 19)
        self.assertTrue(all(row["equal"] for row in comparison["rows"]))

    def test_candidate_budget_rejects(self):
        raw, _ = load_dataset("train_outlier")
        raw["hypothesis_family"]["max_candidates"] = 1
        rehash(raw["hypothesis_family"])
        rehash(raw)
        dataset = ObservationSet.from_record(raw)
        with self.assertRaisesRegex(ValueError, "budget"):
            learn_observation_set(dataset)


class PromotionStoreTests(unittest.TestCase):
    def test_shipped_store_audits_and_reconstructs(self):
        store = LearnerStore(ROOT / "examples/learner05/learner_store")
        audit = store.audit()
        self.assertTrue(audit["valid"], audit["errors"])
        self.assertEqual(audit["commit_count"], 20)
        reconstruction = store.reconstruct()
        self.assertEqual(len(reconstruction["semantic"]["sessions"]), 19)
        self.assertEqual(len(reconstruction["semantic"]["accepted_definitions"]), 12)

    def test_parent_bound_promotion_and_stale_parent_rejection(self):
        _, accepted = load_dataset("clean_identity")
        _, rejected = load_dataset("holdout_outlier")
        with tempfile.TemporaryDirectory() as td:
            store = LearnerStore.initialize(Path(td) / "store", (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes())
            genesis = store.head()
            store.commit_learning(learn_observation_set(accepted), expected_parent=genesis)
            with self.assertRaisesRegex(ValueError, "stale"):
                store.commit_learning(learn_observation_set(rejected), expected_parent=genesis)
            current = store.head()
            store.commit_learning(learn_observation_set(rejected), expected_parent=current)
            self.assertTrue(store.audit()["valid"])
            reconstructed = store.reconstruct()["semantic"]
            self.assertEqual(len(reconstructed["accepted_definitions"]), 1)
            self.assertEqual([item["accepted"] for item in reconstructed["sessions"]], [True, False])

    def test_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            copied = Path(td) / "store"
            shutil.copytree(ROOT / "examples/learner05/learner_store", copied)
            target = sorted((copied / "objects").glob("*.json"))[0]
            target.write_bytes(target.read_bytes() + b" ")
            audit = LearnerStore(copied).audit()
            self.assertFalse(audit["valid"])
            self.assertTrue(any("canonical JSON" in error or "hash mismatch" in error or "Extra data" in error for error in audit["errors"]))

    def test_orphan_policy_is_explicit(self):
        _, dataset = load_dataset("clean_zero")
        with tempfile.TemporaryDirectory() as td:
            store = LearnerStore.initialize(Path(td) / "store", (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes())
            orphan = attach_hash({"schema": "TOM-ORPHAN-TEST", "value": dataset.id})
            store._put("objects", orphan)
            strict = store.audit(require_no_orphans=True)
            permissive = store.audit(require_no_orphans=False)
            self.assertFalse(strict["valid"])
            self.assertTrue(permissive["valid"])
            self.assertTrue(permissive["warnings"])

    def test_every_transaction_enumerates_all_evidence_objects(self):
        store = LearnerStore(ROOT / "examples/learner05/learner_store")
        for commit in store.chain()[1:]:
            transaction = store._get("transactions", commit["transaction_hash"])
            hashes = transaction["evidence_record_hashes"]
            self.assertEqual(len(hashes), len(set(hashes)))
            self.assertGreater(len(hashes), 10)
            for content_hash in hashes:
                self.assertEqual(store._get("objects", content_hash)["content_hash"], content_hash)


class CliTests(unittest.TestCase):
    def test_cli_verifies_corrective_handoff_and_writes_canonical_output(self):
        env = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src/python")}
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base"
            copy_corrective_tree(base)
            output = Path(td) / "verification.json"
            verify = subprocess.run([
                sys.executable, "-m", "tom_learner05", "verify-corrective-handoff", str(base),
                "--corrective", str(base / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"), "--output", str(output),
            ], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            record = json.loads(verify.stdout)
            self.assertTrue(record["valid"], record["errors"])
            self.assertEqual(record["schema"], "TOM-CORRECTIVE-HANDOFF-VERIFICATION-0.5.1")
            self.assertEqual(output.read_bytes(), canonical_bytes(record) + b"\n")

    def test_legacy_cli_still_verifies_pristine_base_tree(self):
        env = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src/python")}
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_pristine_base(base)
            verify = subprocess.run([
                sys.executable, "-m", "tom_learner05", "verify-handoff", str(base),
            ], cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertTrue(json.loads(verify.stdout)["valid"])

    def test_cli_validate_and_baseline(self):
        env = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src/python")}
        dataset = str(DATASET_DIR / "dataset_clean_identity.json")
        validate = subprocess.run([sys.executable, "-m", "tom_learner05", "validate-dataset", dataset], cwd=ROOT, env=env, text=True, capture_output=True)
        self.assertEqual(validate.returncode, 0, validate.stderr)
        self.assertEqual(json.loads(validate.stdout)["status"], "valid")
        baseline = subprocess.run([sys.executable, "-m", "tom_learner05", "baseline", dataset], cwd=ROOT, env=env, text=True, capture_output=True)
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        self.assertTrue(json.loads(baseline.stdout)["semantic"]["accepted"])


if __name__ == "__main__":
    unittest.main()
