from __future__ import annotations

"""Generated-output-free replay for the corrective WQK 0.5.1 handoff."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation/learner05"

CACHE_DIRECTORY_NAMES = {"__pycache__", ".pytest_cache"}
CACHE_FILE_NAMES = {".DS_Store"}
CACHE_SUFFIXES = {".pyc", ".pyo"}
TEST_SUMMARY_RE = re.compile(r"^Ran ([0-9]+) tests in [0-9]+(?:\.[0-9]+)?s$", re.MULTILINE)
MINIMUM_TEST_COUNT = 172

FILE_BOUNDARIES = (
    "examples/learner05/benchmark_manifest.json",
    "examples/learner05/benchmark_oracle.json",
    "validation/learner05/corrective_handoff_verification.json",
    "validation/learner05/baseline_comparison.json",
    "validation/learner05/leakage_certificate.json",
    "validation/learner05/store_audit.json",
    "validation/learner05/store_reconstruction.json",
    "validation/learner05/fixture_report.json",
    "examples/learner05/learner05_formal_authority.tmg",
    "examples/learner05/learner05_formal_authority.tmg.compile.json",
    "validation/learner05/learner05_formal_authority.materialized.json",
    "validation/learner05/learner05_formal_authority.proof.json",
    "examples/learner05/corrective_handoff_0_5_1.tmg",
    "examples/learner05/corrective_handoff_0_5_1.tmg.compile.json",
    "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md",
    "validation/learner05/corrective_handoff_0_5_1.python.trace.json",
    "validation/learner05/corrective_handoff_0_5_1.c.trace.json",
    "validation/learner05/corrective_handoff_0_5_1.emit_records.json",
    "validation/learner05/corrective_handoff_0_5_1.proof.json",
    "examples/learner05/learner05_release_artifact.tmg",
    "examples/learner05/learner05_release_artifact.tmg.compile.json",
    "validation/learner05/TOM_WORLD_QUERY_KERNEL_0_5_RELEASE.materialized.md",
    "validation/learner05/learner05_release_artifact.python.trace.json",
    "validation/learner05/learner05_release_artifact.c.trace.json",
    "validation/learner05/learner05_release_artifact.emit_records.json",
    "validation/learner05/learner05_release_artifact.proof.json",
    "validation/learner05/rejection_capsule.json",
    "validation/learner05/tests.txt",
)


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_files(path: Path) -> list[Path]:
    files = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(path)
        if (
            any(part in CACHE_DIRECTORY_NAMES for part in relative.parts)
            or item.name in CACHE_FILE_NAMES
            or item.suffix in CACHE_SUFFIXES
        ):
            continue
        files.append(item)
    return sorted(files, key=lambda item: item.relative_to(path).as_posix())


def tree_hash(path: Path) -> str:
    h = hashlib.sha256()
    for item in _tree_files(path):
        rel = item.relative_to(path).as_posix().encode("utf-8")
        data = item.read_bytes()
        h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return "sha256:" + h.hexdigest()


def canonicalize_test_log(text: str) -> tuple[str, int, bool]:
    """Remove unittest wall-clock timing while preserving its full evidence."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(TEST_SUMMARY_RE.finditer(normalized))
    if len(matches) != 1:
        raise ValueError("test output must contain exactly one unittest timing summary")
    count = int(matches[0].group(1))
    status_tail = normalized[matches[0].end():]
    status_lines = re.findall(
        r"^(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)$",
        status_tail,
        re.MULTILINE,
    )
    normalized = TEST_SUMMARY_RE.sub(f"Ran {count} tests", normalized, count=1)
    passed = len(status_lines) == 1 and status_lines[0].startswith("OK")
    return normalized, count, passed


def write_canonical_test_log(path: Path, text: str) -> tuple[int, bool]:
    canonical, count, passed = canonicalize_test_log(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical.encode("utf-8"))
    return count, passed


def run(
    cmd: list[str],
    cwd: Path,
    *,
    timeout: int = 420,
    merge_stderr: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(cwd / "src/python"),
    }
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        timeout=timeout,
    )
    if proc.returncode:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr or ''}"
        )
    return proc


def source_input_hashes(root: Path) -> dict[str, str]:
    """Hash the immutable inputs whose copied capsule is actually replayed."""
    return {
        "literal_handoff": sha(root / "sources/TOM_LITERAL_HANDOFF_0_4_2.json"),
        "corrective_handoff": sha(root / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"),
        "benchmark_plan": sha(root / "examples/learner05/benchmark_plan.json"),
        "release_artifact_literal_source": sha(root / "examples/learner05/learner05_release_artifact.literal.json"),
        "formal_authority_literal_source": sha(root / "examples/learner05/learner05_formal_authority.literal.json"),
        "formal_authority_program": sha(root / "examples/learner05/learner05_affine_authority.formal.json"),
        "corrective_handoff_document": sha(root / "docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md"),
        "corrective_handoff_literal_source": sha(root / "examples/learner05/corrective_handoff_0_5_1.literal.json"),
        "corrective_handoff_builder": sha(root / "tools/build_corrective_handoff_artifact.py"),
        "corrective_learner_spec": sha(root / "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md"),
        "tomagi_formal_spec": sha(root / "spec/TOMAGI_1_0_FORMAL_DEFINITION.md"),
        "tomagi_schema": sha(root / "spec/tomagi.schema.json"),
        "seeded_compilation_spec": sha(root / "spec/TOM_SEEDED_COMPILATION_1_0.md"),
        "seeded_program_schema": sha(root / "spec/tom_seeded_program.schema.json"),
        "seed_token_registry": sha(root / "spec/tom_seed_token_registry_1_0.json"),
        "learner_source_tree": tree_hash(root / "src/python/tom_learner05"),
    }


def remove_outputs(root: Path) -> None:
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "examples/learner05/datasets", ignore_errors=True)
    shutil.rmtree(root / "examples/learner05/learner_store", ignore_errors=True)
    (root / "examples/learner05/benchmark_manifest.json").unlink(missing_ok=True)
    (root / "examples/learner05/benchmark_oracle.json").unlink(missing_ok=True)
    (root / "examples/learner05/learner05_formal_authority.tmg").unlink(missing_ok=True)
    (root / "examples/learner05/learner05_formal_authority.tmg.compile.json").unlink(missing_ok=True)
    (root / "examples/learner05/corrective_handoff_0_5_1.tmg").unlink(missing_ok=True)
    (root / "examples/learner05/corrective_handoff_0_5_1.tmg.compile.json").unlink(missing_ok=True)
    (root / "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md").unlink(missing_ok=True)
    (root / "examples/learner05/learner05_release_artifact.tmg").unlink(missing_ok=True)
    (root / "examples/learner05/learner05_release_artifact.tmg.compile.json").unlink(missing_ok=True)
    shutil.rmtree(root / "validation/learner05", ignore_errors=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for path in root.rglob("*.pyc"):
        path.unlink()


def verify_clean_rebuild() -> int:
    dataset_paths = sorted((ROOT / "examples/learner05/datasets").glob("*.json"))
    all_files = [ROOT / rel for rel in FILE_BOUNDARIES] + dataset_paths
    missing = [path.relative_to(ROOT).as_posix() for path in all_files if not path.is_file()]
    if missing:
        raise RuntimeError(f"clean rebuild prerequisites missing: {missing}")
    original = {path.relative_to(ROOT).as_posix(): sha(path) for path in all_files}
    original_store = tree_hash(ROOT / "examples/learner05/learner_store")
    source_snapshot_before = source_input_hashes(ROOT)

    with tempfile.TemporaryDirectory(prefix="tom-learner05-clean-") as td:
        clean = Path(td) / ROOT.name
        # A real copy is intentional: TemporaryDirectory may be on another
        # filesystem, and hard links would both fail with EXDEV and risk source
        # mutation if a retained file were ever rewritten by a build command.
        shutil.copytree(
            ROOT, clean,
            ignore=shutil.ignore_patterns("build", "dist", ".pytest_cache", "__pycache__", "*.pyc", "*.pyo"),
        )
        source_snapshot_after = source_input_hashes(ROOT)
        capsule_source_inputs = source_input_hashes(clean)
        if not (
            source_snapshot_before == source_snapshot_after == capsule_source_inputs
        ):
            raise RuntimeError("source inputs changed while the clean replay capsule was copied")
        remove_outputs(clean)
        (clean / "validation/learner05").mkdir(parents=True, exist_ok=True)
        (clean / "build").mkdir(parents=True, exist_ok=True)
        run(["cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Isrc/c",
             "src/c/tomagi.c", "src/c/tomagi_cli.c", "-o", "build/tomagi-c"], clean)
        run([sys.executable, "tools/build_learner05_fixture.py"], clean)
        run([sys.executable, "tools/build_learner05_formal_authority.py"], clean)
        run([sys.executable, "tools/build_corrective_handoff_artifact.py"], clean)
        run([sys.executable, "tools/build_learner05_release_artifact.py"], clean)
        tests = run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            clean,
            merge_stderr=True,
        )
        test_text, test_count, tests_passed = canonicalize_test_log(tests.stdout)
        if not tests_passed:
            raise RuntimeError("clean source capsule tests did not report OK")
        (clean / "validation/learner05/tests.txt").write_bytes(test_text.encode("utf-8"))
        validation = run([sys.executable, "tools/run_learner05_validation.py"], clean)
        clean_validation_record = json.loads(
            (clean / "validation/learner05/validation_report.json").read_text(encoding="utf-8")
        )
        clean_validation_ok = (
            clean_validation_record.get("status") == "pass"
            and test_count >= MINIMUM_TEST_COUNT
            and clean_validation_record.get("test_count") == test_count
            and clean_validation_record.get("failure_count") == 0
        )
        if not clean_validation_ok:
            raise RuntimeError("clean source capsule core validation did not pass")
        if source_input_hashes(clean) != capsule_source_inputs:
            raise RuntimeError("clean replay mutated a certified source input")

        comparisons: dict[str, Any] = {}
        all_equal = True
        for rel, expected in original.items():
            path = clean / rel
            actual = sha(path) if path.is_file() else None
            equal = actual == expected
            all_equal &= equal
            comparisons[rel] = {"packaged_sha256": expected, "replayed_sha256": actual, "equal": equal}
        clean_store = tree_hash(clean / "examples/learner05/learner_store")
        store_equal = clean_store == original_store
        all_equal &= store_equal
        certificate = {
            "schema": "TOM-LEARNER-0.1-CLEAN-REBUILD",
            "status": "pass" if all_equal else "fail",
            "source_inputs": capsule_source_inputs,
            "tests": test_count,
            "validation_rerun": "pass",
            "clean_core_validation_hash": clean_validation_record.get("content_hash"),
            "compared_file_boundaries": len(comparisons),
            "store_tree_equal": store_equal,
            "packaged_store_tree_sha256": original_store,
            "replayed_store_tree_sha256": clean_store,
            "comparisons": comparisons,
        }
        from tom_world03.canonical import attach_hash, canonical_bytes
        record = attach_hash(certificate)
        (VAL / "clean_rebuild.json").write_bytes(canonical_bytes(record) + b"\n")
        print(json.dumps({
            "status": record["status"],
            "tests": test_count,
            "compared_boundaries": len(comparisons) + 1,
            "store_tree_equal": store_equal,
            "content_hash": record["content_hash"],
        }, indent=2, sort_keys=True))
        return 0 if all_equal else 1


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        if len(arguments) != 2 or arguments[0] != "--canonicalize-test-log":
            raise SystemExit(
                "usage: verify_learner05_clean_rebuild.py "
                "[--canonicalize-test-log OUTPUT]"
            )
        raw = sys.stdin.read()
        destination = Path(arguments[1])
        try:
            count, passed = write_canonical_test_log(destination, raw)
        except ValueError as exc:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))
            sys.stdout.write(raw)
            print(f"canonical test log error: {exc}", file=sys.stderr)
            return 1
        sys.stdout.write(destination.read_text(encoding="utf-8"))
        if count <= 0 or not passed:
            print("canonical test log does not contain a passing test result", file=sys.stderr)
            return 1
        return 0
    return verify_clean_rebuild()


if __name__ == "__main__":
    raise SystemExit(main())
