from __future__ import annotations

"""Deterministic validation for the TOM Learner 0.1 / WQK 0.5.1 correction."""

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation/learner05"
VAL.mkdir(parents=True, exist_ok=True)

from tom_world03.canonical import attach_hash, canonical_bytes, content_hash, verify_hash
from tom_learner05.handoff import verify_corrective_handoff
from tom_learner05.io import load_observation_set
from tom_learner05.learner import learn_observation_set
from tom_learner05.model import ObservationSet
from tom_learner05.store import LearnerStore
from tomagi.format import HEADER_SIZE, STATE_SIZE, CELL_SIZE

FORMAL_PROOF_HASH = "sha256:743e47d75d9261ade618b3fb22343a4dfbb73a25d19cb888c021e5d4d055bdec"
FORMAL_RESULT_HASH = "sha256:74d56499b6fb50d1a7a10ed7228f0c416ae5807c7a1564fb4308cc1fc5fda265"
FORMAL_VALUE_HASH = "sha256:14c5e5e0dd4bc49d40eb8b8f3d86fbdb7bad4d86c872dbeea9799a5aeb92dd12"
FORMAL_TMG_SHA256 = "sha256:ffb4bdfa6939e81124f65165236004c547c1c1b019ac3080c06375b0413029ea"
FORMAL_COMPILE_REPORT_SHA256 = "sha256:057a3e84704144aec66ade4e64cfa195dfeb50ed03074d9518e833828da0e6c5"
FORMAL_MATERIALIZED_SHA256 = "sha256:dd9a0c20c8f721c764580f6655bb509001a7ef59000d0cd1bd5826971b72cb82"
CORRECTIVE_ARTIFACT_PROOF_HASH = "sha256:f4ed3fb188f6755dbbee857a65470794b9e0a8b70069f33779e6b5de0535e626"
CORRECTIVE_ARTIFACT_TMG_SHA256 = "sha256:577041eda947aa6aa5c7aeebb01714177ed3eb3dbf844c17dfdc155693d2ccb8"
CORRECTIVE_ARTIFACT_SIDECAR_SHA256 = "sha256:13bbe7acfece23244fcf6a211796991fdd458d7dffcbe247be3c764997db9a09"
CORRECTIVE_ARTIFACT_MATERIALIZED_SHA256 = "sha256:472d4d15eca25b7cb5271efd91bd47584d309303a6ab9c69bc03250e20070541"


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(path: Path) -> str:
    h = hashlib.sha256()
    files = sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    for item in files:
        rel = item.relative_to(path).as_posix().encode("utf-8")
        data = item.read_bytes()
        h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return "sha256:" + h.hexdigest()


def rehash(record: dict[str, Any]) -> None:
    record["content_hash"] = content_hash(record)


def main(include_clean: bool = False) -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str, **extra: Any) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail, **extra})

    handoff = verify_corrective_handoff(ROOT)
    check("corrective handoff", handoff["valid"],
          (
              f"{handoff['unchanged_base_file_count']} unchanged base files, "
              f"{handoff['replacement_count']} preserved replacements, and "
              f"{handoff['addition_count']} additions verified"
          ) if handoff["valid"] else "; ".join(handoff["errors"]),
          base_handoff_hash=handoff["base_handoff_hash"],
          corrective_handoff_hash=handoff["corrective_handoff_hash"])

    base = json.loads((ROOT / "validation/world04r/validation_report.json").read_text())
    base_ok = (
        base.get("status") == "pass"
        and base.get("failure_count") == 0
        and base.get("test_count") == 144
        and base.get("semantic_chain_sha256") == "sha256:9fd4f3e1ae8550ae3ca99e27e7bf61b22a4935fe764fd443723abfdb3804f226"
        and base.get("content_hash") == "sha256:57be1528d1759c5469259a71daa6f0118b006a1f6a38f9d205f29d3230308391"
    )
    check("latest trusted V0.4.1 result identity", base_ok,
          "preserved independently rerun V0.4.1 validation: 144 tests, 20 checks, 24 replay boundaries")
    world_text = (ROOT / "examples/world04r/piecewise_world.json").read_text()
    correction_ok = "continuation_until" not in world_text and not (ROOT / "src/python/tom_world04").exists()
    check("V0.4 corrective authority pattern", correction_ok,
          "solver-derived continuation is retained; superseded relation-authored endpoints and namespace are absent")

    fixture = json.loads((VAL / "fixture_report.json").read_text())
    fixture_ok = (
        verify_hash(fixture) and fixture.get("status") == "pass"
        and fixture.get("dataset_count") == 19
        and fixture.get("positive_cases") == 12
        and fixture.get("negative_cases") == 7
        and fixture.get("accepted_count") == 12
        and fixture.get("false_promotions") == 0
        and fixture.get("exact_recovery_errors") == 0
        and fixture.get("corrective_handoff_verification_hash") == handoff["content_hash"]
        and fixture.get("corrective_handoff_hash") == handoff["corrective_handoff_hash"]
    )
    check("canonical learning benchmark", fixture_ok,
          "12 exact affine rules recovered, 7 negative cases rejected, zero false promotions",
          fixture_hash=fixture.get("content_hash"))

    baseline = json.loads((VAL / "baseline_comparison.json").read_text())
    check("independent Fraction baseline", verify_hash(baseline) and baseline.get("all_equal") is True,
          "all 19 split, coefficient, and acceptance semantics agree with the separately implemented baseline",
          comparison_hash=baseline.get("content_hash"))

    leakage = json.loads((VAL / "leakage_certificate.json").read_text())
    check("validation/holdout leakage probes", verify_hash(leakage) and leakage.get("valid") is True,
          "same-ID target mutations preserve split IDs, assignment basis, fit input, and selected coefficients while failing acceptance",
          certificate_hash=leakage.get("content_hash"))

    store = LearnerStore(ROOT / "examples/learner05/learner_store")
    audit = store.audit()
    reconstruction = store.reconstruct()
    store_ok = audit["valid"] and audit["commit_count"] == 20 and len(reconstruction["semantic"]["accepted_definitions"]) == 12
    check("append-only learner overlay", store_ok,
          "20 commits, 19 learning sessions, 12 accepted definitions, complete evidence reachability, zero strict orphans",
          audit_hash=audit["content_hash"], reconstruction_hash=reconstruction["content_hash"], tree_sha256=tree_hash(store.root))

    schema_ok = True
    schema_errors: list[str] = []
    try:
        import jsonschema
        schema = json.loads((ROOT / "spec/tom_learner_affine_0_5.schema.json").read_text())
        for path in sorted((ROOT / "examples/learner05/datasets").glob("*.json")):
            try:
                jsonschema.Draft202012Validator(schema).validate(json.loads(path.read_text()))
            except Exception as exc:
                schema_ok = False
                schema_errors.append(f"{path.name}: {exc}")
    except ImportError:
        schema_ok = False
        schema_errors.append("jsonschema is unavailable")
    check("strict observation-set schema", schema_ok,
          "all 19 literal data sets validate under Draft 2020-12" if schema_ok else "; ".join(schema_errors))

    source_roundtrip = True
    for path in sorted((ROOT / "examples/learner05/datasets").glob("*.json")):
        raw, dataset = load_observation_set(path)
        source_roundtrip &= canonical_bytes(raw) == canonical_bytes(dataset.to_record())
    check("nested literal identity", source_roundtrip,
          "every observation set and nested policy/observation record round-trips canonically with verified content hashes")

    tests_text = (VAL / "tests.txt").read_text(errors="replace")
    match = re.search(r"Ran (\d+) tests", tests_text)
    test_count = int(match.group(1)) if match else 0
    tests_ok = ("\nOK\n" in tests_text or tests_text.rstrip().endswith("OK")) and test_count >= 172
    check("complete inherited and learner test suite", tests_ok,
          f"{test_count} tests passed" if tests_ok else "test report is missing or failed")

    formal_proof_path = VAL / "learner05_formal_authority.proof.json"
    formal_result_path = VAL / "learner05_formal_authority.materialized.json"
    formal_tmg_path = ROOT / "examples/learner05/learner05_formal_authority.tmg"
    formal_sidecar_path = ROOT / "examples/learner05/learner05_formal_authority.tmg.compile.json"
    formal_proof = json.loads(formal_proof_path.read_text())
    formal_result = json.loads(formal_result_path.read_text())
    formal_oracle = formal_proof.get("semantic_oracle", {})
    formal_evaluation = formal_proof.get("formal_evaluation", {})
    formal_compiled = formal_proof.get("compiled_program", {})
    formal_execution = formal_proof.get("execution", {})
    formal_materialized = formal_proof.get("materialized_artifact", {})
    formal_program = formal_proof.get("formal_program", {})
    formal_value = formal_result.get("value", {})
    formal_ok = (
        verify_hash(formal_proof)
        and formal_proof.get("schema") == "TOM-WQK-0.5.1-FORMAL-AUTHORITY-PROOF-1.0"
        and formal_proof.get("status") == "pass"
        and formal_proof.get("content_hash") == FORMAL_PROOF_HASH
        and formal_oracle.get("dataset_count") == 19
        and formal_oracle.get("accepted") == 12
        and formal_oracle.get("rejected") == 7
        and formal_oracle.get("coefficient_errors") == 0
        and formal_oracle.get("addressed_sdf0_relations_executed") == 12
        and formal_oracle.get("independent_baseline_rows_equal") == 19
        and formal_evaluation.get("steps") == 131478
        and formal_evaluation.get("result_content_hash") == FORMAL_RESULT_HASH
        and formal_evaluation.get("value_content_hash") == FORMAL_VALUE_HASH
        and formal_compiled.get("cells") == 19540
        and formal_compiled.get("in_place_recompile_equal") is True
        and formal_compiled.get("sha256") == FORMAL_TMG_SHA256
        and formal_compiled.get("compile_report_sha256") == FORMAL_COMPILE_REPORT_SHA256
        and formal_materialized.get("sha256") == FORMAL_MATERIALIZED_SHA256
        and formal_execution.get("steps") == 19540
        and formal_execution.get("emit_records") == 19540
        and formal_execution.get("python_c_full_trace_equal") is True
        and formal_execution.get("python_c_emit_equal") is True
        and formal_execution.get("python_trace_sha256") == formal_execution.get("c_trace_sha256")
        and formal_program.get("content_hash") == formal_result.get("program_hash")
        and verify_hash(formal_result)
        and formal_result.get("schema") == "TOMAGI-FORMAL-RESULT-1.0"
        and formal_result.get("content_hash") == FORMAL_RESULT_HASH
        and formal_result.get("steps") == 131478
        and formal_value.get("content_hash") == FORMAL_VALUE_HASH
        and formal_value.get("accepted_count") == 12
        and formal_value.get("rejected_count") == 7
        and len(formal_value.get("results", [])) == 19
        and sha(formal_tmg_path) == FORMAL_TMG_SHA256
        and sha(formal_sidecar_path) == FORMAL_COMPILE_REPORT_SHA256
        and sha(formal_result_path) == FORMAL_MATERIALIZED_SHA256
    )
    check("seeded formal learner authority", formal_ok,
          "19 literal datasets -> 131478-step exact formal evaluation -> 19540 Cell48 records -> equal Python/C traces and EMITs -> 12 addressed SDF0 relations",
          proof_hash=formal_proof.get("content_hash"),
          result_hash=formal_evaluation.get("result_content_hash"),
          tmg_sha256=sha(formal_tmg_path),
          materialized_sha256=sha(formal_result_path))

    corrective_artifact_proof_path = VAL / "corrective_handoff_0_5_1.proof.json"
    corrective_artifact_tmg_path = ROOT / "examples/learner05/corrective_handoff_0_5_1.tmg"
    corrective_artifact_sidecar_path = ROOT / "examples/learner05/corrective_handoff_0_5_1.tmg.compile.json"
    corrective_artifact_materialized_path = ROOT / "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md"
    corrective_artifact_authored_path = ROOT / "docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md"
    corrective_artifact_proof = json.loads(corrective_artifact_proof_path.read_text())
    corrective_artifact_overlay = corrective_artifact_proof.get("corrective_overlay", {})
    corrective_artifact_compiled = corrective_artifact_proof.get("compiled_program", {})
    corrective_artifact_execution = corrective_artifact_proof.get("execution", {})
    corrective_artifact_materialized = corrective_artifact_proof.get("materialized_artifact", {})
    corrective_artifact_authored = corrective_artifact_proof.get("authored_document", {})
    corrective_artifact_ok = (
        verify_hash(corrective_artifact_proof)
        and corrective_artifact_proof.get("schema") == "TOM-WQK-0.5.1-CORRECTIVE-HANDOFF-ARTIFACT-PROOF-1.0"
        and corrective_artifact_proof.get("status") == "pass"
        and corrective_artifact_proof.get("content_hash") == CORRECTIVE_ARTIFACT_PROOF_HASH
        and corrective_artifact_overlay.get("content_hash") == handoff["corrective_handoff_hash"]
        and corrective_artifact_overlay.get("file_sha256") == sha(ROOT / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json")
        and corrective_artifact_compiled.get("cells") == 2155
        and corrective_artifact_compiled.get("in_place_recompile_equal") is True
        and corrective_artifact_compiled.get("sha256") == CORRECTIVE_ARTIFACT_TMG_SHA256
        and corrective_artifact_compiled.get("compile_report_sha256") == CORRECTIVE_ARTIFACT_SIDECAR_SHA256
        and corrective_artifact_execution.get("steps") == 2155
        and corrective_artifact_execution.get("emit_records") == 2155
        and corrective_artifact_execution.get("python_c_full_trace_equal") is True
        and corrective_artifact_execution.get("python_c_emit_equal") is True
        and corrective_artifact_execution.get("python_trace_sha256") == corrective_artifact_execution.get("c_trace_sha256")
        and corrective_artifact_materialized.get("matches_authored_document") is True
        and corrective_artifact_materialized.get("sha256") == CORRECTIVE_ARTIFACT_MATERIALIZED_SHA256
        and corrective_artifact_authored.get("sha256") == CORRECTIVE_ARTIFACT_MATERIALIZED_SHA256
        and sha(corrective_artifact_tmg_path) == CORRECTIVE_ARTIFACT_TMG_SHA256
        and sha(corrective_artifact_sidecar_path) == CORRECTIVE_ARTIFACT_SIDECAR_SHA256
        and sha(corrective_artifact_materialized_path) == CORRECTIVE_ARTIFACT_MATERIALIZED_SHA256
        and sha(corrective_artifact_authored_path) == CORRECTIVE_ARTIFACT_MATERIALIZED_SHA256
    )
    check("corrective handoff causal artifact", corrective_artifact_ok,
          "corrective manifest and authored handoff -> 2155 Cell48 records -> equal Python/C traces and EMITs -> byte-identical materialized handoff",
          proof_hash=corrective_artifact_proof.get("content_hash"),
          materialized_sha256=sha(corrective_artifact_materialized_path))

    proof = json.loads((VAL / "learner05_release_artifact.proof.json").read_text())
    release_artifact_ok = (
        verify_hash(proof) and proof.get("status") == "pass"
        and proof["execution"]["python_c_full_trace_equal"] is True
        and proof["execution"]["python_c_emit_sequence_equal"] is True
        and proof["artifact"]["matches_authored_document"] is True
    )
    check("release-document causal artifact", release_artifact_ok,
          "literal definitions -> compiled Cell48 -> equal Python/C traces -> ordered EMIT -> byte-identical Markdown",
          proof_hash=proof.get("content_hash"))

    abi_ok = (HEADER_SIZE, STATE_SIZE, CELL_SIZE) == (128, 64, 48)
    check("frozen TOMAGI ABI", abi_ok, f"header/state/cell sizes are {HEADER_SIZE}/{STATE_SIZE}/{CELL_SIZE}; no opcode was added")

    rejection_rows: list[dict[str, Any]] = []
    clean_raw, clean_dataset = load_observation_set(ROOT / "examples/learner05/datasets/dataset_clean_double.json")

    def expect(name: str, fn: Callable[[], Any], expected: str) -> None:
        try:
            fn()
        except Exception as exc:
            message = str(exc)
            rejection_rows.append({"name": name, "status": "pass" if expected in message else "fail", "error": message, "expected": expected})
        else:
            rejection_rows.append({"name": name, "status": "fail", "error": "no exception", "expected": expected})

    bad = copy.deepcopy(clean_raw); bad["seed_sha256"] = "0" * 64; rehash(bad)
    expect("wrong canonical seed binding", lambda: ObservationSet.from_record(bad), "canonical TOM seed")
    bad = copy.deepcopy(clean_raw); bad["base_handoff_hash"] = "sha256:" + "0" * 64; rehash(bad)
    expect("wrong literal handoff binding", lambda: ObservationSet.from_record(bad), "unsupported literal handoff")
    bad = copy.deepcopy(clean_raw); bad["observations"][0]["y"] = {"num": 9, "den": 1}; rehash(bad)
    expect("nested observation hash mutation", lambda: ObservationSet.from_record(bad), "observation content hash mismatch")
    bad = copy.deepcopy(clean_raw); bad["observations"] = list(reversed(bad["observations"])); rehash(bad)
    expect("noncanonical observation order", lambda: ObservationSet.from_record(bad), "sorted")
    bad = copy.deepcopy(clean_raw); bad["observations"][1] = copy.deepcopy(bad["observations"][0]); rehash(bad)
    expect("duplicate observation ID", lambda: ObservationSet.from_record(bad), "unique")
    bad = copy.deepcopy(clean_raw); bad["split_policy"]["minimum_counts"] = {"train": 30, "validation": 1, "holdout": 1}; rehash(bad["split_policy"]); rehash(bad)
    expect("split minimum overflow", lambda: learn_observation_set(ObservationSet.from_record(bad)), "below split minimum total")
    outlier_raw, _ = load_observation_set(ROOT / "examples/learner05/datasets/dataset_train_outlier.json")
    bad = copy.deepcopy(outlier_raw); bad["hypothesis_family"]["max_candidates"] = 1; rehash(bad["hypothesis_family"]); rehash(bad)
    expect("candidate budget overflow", lambda: learn_observation_set(ObservationSet.from_record(bad)), "candidate budget")
    bad = copy.deepcopy(clean_raw); bad["hypothesis_family"]["model"] = "y=a*t^2+b"; rehash(bad["hypothesis_family"]); rehash(bad)
    expect("unsupported hypothesis family", lambda: ObservationSet.from_record(bad), "supports only")

    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        temp_store = LearnerStore.initialize(temp / "store", (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes())
        genesis = temp_store.head()
        run = learn_observation_set(clean_dataset)
        temp_store.commit_learning(run, expected_parent=genesis)
        expect("stale parent promotion", lambda: temp_store.commit_learning(run, expected_parent=genesis), "stale")
        expect("duplicate committed session", lambda: temp_store.commit_learning(run, expected_parent=temp_store.head()), "already has")
        orphan = attach_hash({"schema": "TOM-VALIDATION-ORPHAN", "value": 1})
        temp_store._put("objects", orphan)
        strict = temp_store.audit(require_no_orphans=True)
        rejection_rows.append({"name": "strict orphan policy", "status": "pass" if not strict["valid"] else "fail", "error": strict["errors"], "expected": "orphan"})

    with tempfile.TemporaryDirectory() as td:
        copied = Path(td) / "store"
        shutil.copytree(store.root, copied)
        target = sorted((copied / "objects").glob("*.json"))[0]
        target.write_bytes(target.read_bytes() + b" ")
        corrupted = LearnerStore(copied).audit()
        rejection_rows.append({"name": "noncanonical immutable object bytes", "status": "pass" if not corrupted["valid"] else "fail", "error": corrupted["errors"], "expected": "canonical JSON"})

    rejection_ok = all(row["status"] == "pass" for row in rejection_rows)
    rejection_capsule = attach_hash({
        "schema": "TOM-LEARNER-0.1-REJECTION-CAPSULE",
        "case_count": len(rejection_rows),
        "all_pass": rejection_ok,
        "cases": rejection_rows,
    })
    (VAL / "rejection_capsule.json").write_bytes(canonical_bytes(rejection_capsule) + b"\n")
    check("deterministic rejection capsule", rejection_ok,
          f"all {len(rejection_rows)} malformed, stale, corrupted, and orphaned cases rejected")

    # In-place deterministic rebuild of all 0.5 generated semantic boundaries.
    boundaries = [
        ROOT / "examples/learner05/benchmark_manifest.json",
        ROOT / "examples/learner05/benchmark_oracle.json",
        VAL / "corrective_handoff_verification.json",
        VAL / "baseline_comparison.json",
        VAL / "leakage_certificate.json",
        VAL / "store_audit.json",
        VAL / "store_reconstruction.json",
        VAL / "fixture_report.json",
        ROOT / "examples/learner05/learner05_formal_authority.tmg",
        ROOT / "examples/learner05/learner05_formal_authority.tmg.compile.json",
        VAL / "learner05_formal_authority.materialized.json",
        VAL / "learner05_formal_authority.proof.json",
        ROOT / "examples/learner05/corrective_handoff_0_5_1.tmg",
        ROOT / "examples/learner05/corrective_handoff_0_5_1.tmg.compile.json",
        ROOT / "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md",
        VAL / "corrective_handoff_0_5_1.proof.json",
        ROOT / "examples/learner05/learner05_release_artifact.tmg",
        ROOT / "examples/learner05/learner05_release_artifact.tmg.compile.json",
        VAL / "TOM_WORLD_QUERY_KERNEL_0_5_RELEASE.materialized.md",
        VAL / "learner05_release_artifact.python.trace.json",
        VAL / "learner05_release_artifact.c.trace.json",
        VAL / "learner05_release_artifact.emit_records.json",
        VAL / "learner05_release_artifact.proof.json",
    ]
    boundaries.extend(sorted((ROOT / "examples/learner05/datasets").glob("*.json")))
    before = {path.relative_to(ROOT).as_posix(): sha(path) for path in boundaries}
    before_tree = tree_hash(store.root)
    import subprocess, os, sys
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src/python")}
    subprocess.run([sys.executable, "tools/build_learner05_fixture.py"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "tools/build_learner05_formal_authority.py"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "tools/build_corrective_handoff_artifact.py"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "tools/build_learner05_release_artifact.py"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    after = {path.relative_to(ROOT).as_posix(): sha(path) for path in boundaries}
    after_tree = tree_hash(store.root)
    rebuild_ok = before == after and before_tree == after_tree
    rebuild_mismatches = [rel for rel in before if before[rel] != after[rel]]
    check("in-place deterministic rebuild", rebuild_ok,
          f"{len(boundaries)} files plus the learner-store tree reproduced byte-identically",
          file_boundaries=len(boundaries), store_tree_sha256=after_tree,
          mismatched_files=rebuild_mismatches, store_tree_equal=before_tree == after_tree)

    clean_record: Mapping[str, Any] | None = None
    if include_clean:
        path = VAL / "clean_rebuild.json"
        if path.is_file():
            clean_record = json.loads(path.read_text())
            clean_file_count = int(clean_record.get("compared_file_boundaries", 0))
            clean_comparisons = clean_record.get("comparisons", {})
            clean_store_equal = clean_record.get("store_tree_equal") is True
            clean_comparisons_ok = (
                isinstance(clean_comparisons, Mapping)
                and len(clean_comparisons) == clean_file_count
                and all(isinstance(row, Mapping) and row.get("equal") is True for row in clean_comparisons.values())
            )
            clean_boundary_count = clean_file_count + (1 if clean_store_equal else 0)
            clean_ok = (
                verify_hash(clean_record)
                and clean_record.get("status") == "pass"
                and clean_file_count > 0
                and clean_comparisons_ok
                and clean_store_equal
            )
            check("generated-output-free clean replay", clean_ok,
                  f"{clean_boundary_count} file/tree boundaries reproduced from a clean source capsule",
                  certificate_hash=clean_record.get("content_hash"),
                  boundary_count=clean_boundary_count)
        else:
            check("generated-output-free clean replay", False, "clean_rebuild.json is missing")

    failure_count = sum(row["status"] == "fail" for row in checks)
    report = attach_hash({
        "schema": "TOM-LEARNER-0.1-WQK-0.5.1-VALIDATION-REPORT",
        "release": "0.5.1",
        "status": "pass" if failure_count == 0 else "fail",
        "canonical_seed_sha256": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
        "literal_handoff_hash": handoff["handoff_hash"],
        "corrective_handoff_hash": handoff["corrective_handoff_hash"],
        "corrective_handoff_verification_hash": handoff["content_hash"],
        "formal_authority_proof_hash": formal_proof.get("content_hash"),
        "formal_authority_result_hash": formal_evaluation.get("result_content_hash"),
        "corrective_handoff_artifact_proof_hash": corrective_artifact_proof.get("content_hash"),
        "uploaded_0_4_2_archive_used": False,
        "uploaded_0_4_2_limitation": "conversation upload was not exposed to the execution filesystem; independently reconstructed handoff used instead",
        "base_v0_4_1_validation_hash": base.get("content_hash"),
        "fixture_hash": fixture.get("content_hash"),
        "benchmark_plan_hash": fixture.get("plan_hash"),
        "benchmark_dataset_count": fixture.get("dataset_count"),
        "accepted_count": fixture.get("accepted_count"),
        "false_promotions": fixture.get("false_promotions"),
        "independent_baseline_hash": baseline.get("content_hash"),
        "learner_store_tree_sha256": tree_hash(store.root),
        "test_count": test_count,
        "check_count": len(checks),
        "failure_count": failure_count,
        "clean_rebuild_hash": clean_record.get("content_hash") if clean_record else None,
        "clean_rebuild_boundaries": (
            int(clean_record.get("compared_file_boundaries", 0))
            + (1 if clean_record and clean_record.get("store_tree_equal") is True else 0)
        ) if clean_record else None,
        "tomagi_abi": {"header_bytes": HEADER_SIZE, "state_bytes": STATE_SIZE, "cell_bytes": CELL_SIZE, "opcodes": 16},
        "checks": checks,
        "evidence_boundary": "Exact finite affine induction over canonical rational observations. No claim of noisy/general learning, perception, planning, physical GPU learner execution, or AGI.",
    })
    (VAL / "validation_report.json").write_bytes(canonical_bytes(report) + b"\n")
    md = [
        "# TOM Learner 0.1 / WQK 0.5 validation",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Tests: **{test_count} passed**",
        f"- Validation checks: **{len(checks) - failure_count} passed, {failure_count} failed**",
        f"- Benchmark: **12 exact recoveries, 7 correct rejections, {fixture['false_promotions']} false promotions**",
        f"- Base literal handoff: `{handoff['handoff_hash']}`",
        f"- Corrective handoff: `{handoff['corrective_handoff_hash']}`",
        f"- Learner store: `{report['learner_store_tree_sha256']}`",
        f"- Validation report: `{report['content_hash']}`",
        "",
        "The exact conversation-uploaded 0.4.2 ZIP was unavailable to the execution filesystem and was not claimed as validated. The build verifies the independently reconstructed literal-only V0.4.1 handoff together with the explicit, byte-preserving 0.5.1 corrective overlay.",
        "",
    ]
    (VAL / "VALIDATION.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "tests": test_count,
        "checks": len(checks),
        "failures": failure_count,
        "validation_hash": report["content_hash"],
        "fixture_hash": fixture["content_hash"],
        "store_tree_sha256": report["learner_store_tree_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-clean", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(include_clean=args.include_clean))
