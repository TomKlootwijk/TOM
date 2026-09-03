from __future__ import annotations

"""Generated-output-free replay for WQK 0.5.2 transaction authority."""

import argparse
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
VAL = ROOT / "validation/learner052"

from tomagi.canonical import attach_hash, canonical_bytes

FILE_BOUNDARIES = (
    "validation/learner052/corrective_handoff_verification.json",
    "validation/learner052/continuation_handoff_verification.json",
    "validation/learner052/promotion_authority.direct_formal.json",
    "validation/learner052/promotion_authority.oracle.json",
    "examples/learner052/promotion_authority.tmg",
    "examples/learner052/promotion_authority.tmg.compile.json",
    "validation/learner052/promotion_authority.materialized.json",
    "validation/learner052/promotion_authority.proof.json",
    "validation/learner052/promotion_store_audit.json",
    "validation/learner052/promotion_store_reconstruction.json",
    "examples/learner052/learner052_release_artifact.tmg",
    "examples/learner052/learner052_release_artifact.tmg.compile.json",
    "validation/learner052/TOM_WORLD_QUERY_KERNEL_0_5_2_RELEASE.materialized.md",
    "validation/learner052/learner052_release_artifact.python.trace.json",
    "validation/learner052/learner052_release_artifact.c.trace.json",
    "validation/learner052/learner052_release_artifact.emit_records.json",
    "validation/learner052/learner052_release_artifact.proof.json",
    "validation/learner052/rejection_capsule.json",
    "validation/learner052/tests.txt",
    "validation/learner052/validation_report_core.json",
)

SOURCE_BOUNDARIES = (
    "TOM_seed_genome_2026-09-01.txt",
    "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json",
    "sources/TOM_CONTINUATION_HANDOFF_0_5_2.json",
    "examples/learner052/promotion_authority.formal.json",
    "examples/learner052/promotion_authority.literal.json",
    "examples/learner052/promotion_context.json",
    "examples/learner052/learner052_release_artifact.literal.json",
    "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_2_TRANSACTION_AUTHORITY.md",
    "spec/tom_learner_promotion_authority_0_5_2.schema.json",
    "src/python/tomagi/immutable_store.py",
    "src/python/tom_learner052/oracle.py",
    "tools/build_learner052_promotion_authority.py",
    "tools/build_learner052_release_artifact.py",
    "tools/run_learner052_validation.py",
    "tests/test_learner052_transaction_authority.py",
)

TEST_SUMMARY_RE = re.compile(r"^Ran ([0-9]+) tests in [0-9]+(?:\.[0-9]+)?s$", re.MULTILINE)


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def tree_record(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    byte_count = 0
    for item in sorted((p for p in path.rglob("*") if p.is_file()), key=lambda p: p.relative_to(path).as_posix()):
        rel = item.relative_to(path).as_posix().encode("utf-8")
        data = item.read_bytes()
        digest.update(len(rel).to_bytes(8, "big")); digest.update(rel)
        digest.update(len(data).to_bytes(8, "big")); digest.update(data)
        count += 1; byte_count += len(data)
    return {"file_count": count, "bytes": byte_count, "sha256": "sha256:" + digest.hexdigest()}


def canonicalize_test_log(text: str) -> tuple[str, int, bool]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(TEST_SUMMARY_RE.finditer(normalized))
    if len(matches) != 1:
        raise ValueError("test output must contain exactly one unittest timing summary")
    count = int(matches[0].group(1))
    status_tail = normalized[matches[0].end():]
    status_lines = re.findall(r"^(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)$", status_tail, re.MULTILINE)
    normalized = TEST_SUMMARY_RE.sub(f"Ran {count} tests", normalized, count=1)
    return normalized, count, len(status_lines) == 1 and status_lines[0].startswith("OK")


def write_canonical_test_log(path: Path, text: str) -> tuple[int, bool]:
    value, count, passed = canonicalize_test_log(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return count, passed


def run(cmd: list[str], cwd: Path, *, timeout: int = 600, merge_stderr: bool = False) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(cwd / "src/python")}
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
            f"command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr or ''}"
        )
    return proc


def copy_ignore(directory: str, names: list[str]) -> set[str]:
    path = Path(directory)
    ignored: set[str] = set()
    for name in names:
        if name in {"__pycache__", ".pytest_cache", "build", "dist"}:
            ignored.add(name)
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return ignored
    if rel == "validation" and "learner052" in names:
        ignored.add("learner052")
    if rel == "examples/learner052":
        ignored.update({
            "promotion_store",
            "promotion_authority.tmg",
            "promotion_authority.tmg.compile.json",
            "learner052_release_artifact.tmg",
            "learner052_release_artifact.tmg.compile.json",
        } & set(names))
    return ignored


def source_hashes(root: Path) -> dict[str, str]:
    result = {rel: sha(root / rel) for rel in SOURCE_BOUNDARIES}
    authority_inputs = root / "examples/learner052/authority_inputs"
    result["examples/learner052/authority_inputs/*"] = tree_record(authority_inputs)["sha256"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonicalize-test-log", metavar="OUTPUT")
    args = parser.parse_args()
    if args.canonicalize_test_log:
        text = sys.stdin.read()
        count, passed = write_canonical_test_log(Path(args.canonicalize_test_log), text)
        sys.stdout.write(text)
        return 0 if passed and count >= 238 else 1

    expected_files = {rel: sha(ROOT / rel) for rel in FILE_BOUNDARIES}
    expected_store = tree_record(ROOT / "examples/learner052/promotion_store")
    expected_sources = source_hashes(ROOT)
    outer_core = json.loads((VAL / "validation_report_core.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="tom-learner052-clean-") as td:
        copied = Path(td) / ROOT.name
        shutil.copytree(ROOT, copied, ignore=copy_ignore)
        proc = run(["make", "validate-learner052-core"], copied, timeout=900)
        (VAL / "clean_rebuild.log").write_text(proc.stdout, encoding="utf-8")

        comparisons: dict[str, Any] = {}
        all_equal = True
        for rel, expected in expected_files.items():
            path = copied / rel
            actual = sha(path) if path.is_file() else None
            equal = actual == expected
            comparisons[rel] = {"expected_sha256": expected, "rebuilt_sha256": actual, "equal": equal}
            all_equal &= equal
        rebuilt_store = tree_record(copied / "examples/learner052/promotion_store")
        store_equal = rebuilt_store == expected_store
        all_equal &= store_equal
        rebuilt_sources = source_hashes(copied)
        sources_equal = rebuilt_sources == expected_sources
        all_equal &= sources_equal
        rebuilt_core = json.loads((copied / "validation/learner052/validation_report_core.json").read_text(encoding="utf-8"))
        core_equal = rebuilt_core.get("content_hash") == outer_core.get("content_hash")
        all_equal &= core_equal

    record = attach_hash({
        "schema": "TOM-WQK-0.5.2-CLEAN-REBUILD-1.0",
        "release": "0.5.2",
        "status": "pass" if all_equal else "fail",
        "generated_outputs_removed": True,
        "make_target": "validate-learner052-core",
        "compared_file_boundaries": len(comparisons),
        "all_file_boundaries_equal": all(item["equal"] for item in comparisons.values()),
        "store_tree_equal": store_equal,
        "source_inputs_equal": sources_equal,
        "core_validation_equal": core_equal,
        "all_boundaries_equal": all_equal,
        "core_validation_hash": outer_core.get("content_hash"),
        "source_inputs": expected_sources,
        "promotion_store_expected": expected_store,
        "promotion_store_rebuilt": rebuilt_store,
        "files": comparisons,
    })
    (VAL / "clean_rebuild.json").write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({
        "status": record["status"],
        "compared_file_boundaries": record["compared_file_boundaries"],
        "store_tree_equal": store_equal,
        "source_inputs_equal": sources_equal,
        "core_validation_equal": core_equal,
        "content_hash": record["content_hash"],
    }, indent=2, sort_keys=True))
    return 0 if all_equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
