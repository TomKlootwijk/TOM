from __future__ import annotations

"""Perform two generated-output-free WQK 0.6 builds and compare bytes."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation/learner06"
BASE = ROOT / "examples/learner06"

from tomagi.canonical import attach_hash, canonical_bytes

SOURCE_BOUNDARIES = [
    "TOM_seed_genome_2026-09-01.txt",
    "docs/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md",
    "sources/codex_0_5_2_repair/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json",
    "sources/codex_0_5_2_repair/TOM_AGI_ROADMAP_AND_STARTER_0_5_2.md",
    "sources/codex_0_5_2_repair/TOM_CONTINUATION_HANDOFF_0_5_2.json",
    "spec/TOM_LEARNER_0_2_WORLD_QUERY_KERNEL_0_6.md",
    "spec/tom_learner_family_registry_0_6.schema.json",
    "spec/tom_learner_dataset_0_6.schema.json",
    "TOM_WORLD_QUERY_KERNEL_0_6_RELEASE.md",
    "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.md",
    "TOM_AGI_ROADMAP_AND_STARTER_0_6.md",
    "examples/learner06/family_registry.json",
    "examples/learner06/dataset_bundle.json",
    "examples/learner06/prior_authority.json",
    "examples/learner06/partition_policy.json",
    "examples/learner06/benchmark_oracle.json",
    "examples/learner06/repair_handoff_proof.json",
    "examples/learner06/promotion_context.json",
    "examples/learner06/learner06_family_authority.formal.json",
    "examples/learner06/learner06_family_authority.literal.json",
    "examples/learner06/learner06_promotion_authority.formal.json",
    "examples/learner06/learner06_promotion_authority.literal.json",
    "examples/learner06/learner06_release_artifact.literal.json",
    "examples/learner06/kernel06_validation_handoff.literal.json",
]
SOURCE_BOUNDARIES += [
    f"examples/learner06/datasets/{path.name}"
    for path in sorted((BASE / "datasets").glob("*.json"))
]

GENERATED_BOUNDARIES = [
    "examples/learner06/learner06_family_authority.result.json",
    "examples/learner06/learner06_family_authority.tmg",
    "examples/learner06/learner06_family_authority.tmg.compile.json",
    "validation/learner06/learner_authority.direct.json",
    "validation/learner06/learner_authority.materialized.json",
    "validation/learner06/learner_authority.python.trace.json",
    "validation/learner06/learner_authority.c.trace.json",
    "validation/learner06/learner_authority.emit_records.json",
    "validation/learner06/learner_authority_proof.json",
    "validation/learner06/oracle_comparison.json",
    "examples/learner06/learner06_promotion_authority.tmg",
    "examples/learner06/learner06_promotion_authority.tmg.compile.json",
    "validation/learner06/promotion_authority.direct.json",
    "validation/learner06/promotion_authority.materialized.json",
    "validation/learner06/promotion_authority.python.trace.json",
    "validation/learner06/promotion_authority.c.trace.json",
    "validation/learner06/promotion_authority.emit_records.json",
    "validation/learner06/promotion_authority_proof.json",
    "validation/learner06/promotion_store_audit.json",
    "validation/learner06/promotion_store_reconstruction.json",
    "validation/learner06/fixture_report.json",
    "examples/learner06/learner06_release_artifact.tmg",
    "examples/learner06/learner06_release_artifact.tmg.compile.json",
    "validation/learner06/TOM_WORLD_QUERY_KERNEL_0_6_RELEASE.materialized.md",
    "validation/learner06/learner06_release_artifact.python.trace.json",
    "validation/learner06/learner06_release_artifact.c.trace.json",
    "validation/learner06/learner06_release_artifact.emit_records.json",
    "validation/learner06/learner06_release_artifact.proof.json",
    "examples/learner06/kernel06_validation_handoff.tmg",
    "examples/learner06/kernel06_validation_handoff.tmg.compile.json",
    "validation/learner06/CODEX_KERNEL_0_6_VALIDATION_HANDOFF.materialized.md",
    "validation/learner06/kernel06_validation_handoff.python.trace.json",
    "validation/learner06/kernel06_validation_handoff.c.trace.json",
    "validation/learner06/kernel06_validation_handoff.emit_records.json",
    "validation/learner06/kernel06_validation_handoff.proof.json",
    "validation/learner06/tests.txt",
    "validation/learner06/rejection_capsule.json",
    "validation/learner06/validation_report_core.json",
]


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def tree_record(root: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == ".publication.lock":
            continue
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
        count += 1; total += len(data)
    return {"file_count": count, "bytes": total, "sha256": "sha256:" + h.hexdigest()}


def ignore(directory: str, names: list[str]) -> set[str]:
    path = Path(directory)
    ignored: set[str] = set()
    for name in names:
        if name in {"build", "dist", ".pytest_cache", "__pycache__"}:
            ignored.add(name)
        if name.endswith((".pyc", ".pyo")):
            ignored.add(name)
        if path == ROOT / "checksums" and name in {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"}:
            ignored.add(name)
        if path == ROOT / "validation" and name == "learner06":
            ignored.add(name)
        if path == ROOT / "examples/learner06" and name == "promotion_store":
            ignored.add(name)
    return ignored


def remove_generated(root: Path) -> None:
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "validation/learner06", ignore_errors=True)
    shutil.rmtree(root / "examples/learner06/promotion_store", ignore_errors=True)
    for rel in GENERATED_BOUNDARIES:
        if rel.startswith("validation/"):
            continue
        (root / rel).unlink(missing_ok=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for path in root.rglob("*.pyc"):
        path.unlink(missing_ok=True)
    (root / "checksums/PACKAGE_MANIFEST.json").unlink(missing_ok=True)
    (root / "checksums/SHA256SUMS.txt").unlink(missing_ok=True)


def run_build(root: Path) -> None:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src/python")}
    commands = [
        ["make", "build/tomagi-c"],
        [sys.executable, "tools/build_learner06_authority.py"],
        [sys.executable, "tools/build_learner06_release_artifact.py"],
        [sys.executable, "tools/build_kernel06_validation_handoff.py"],
        [sys.executable, "tools/run_learner06_tests.py"],
        [sys.executable, "tools/run_learner06_validation.py"],
    ]
    for command in commands:
        proc = subprocess.run(command, cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
        if proc.returncode:
            raise RuntimeError(f"clean build failed: {' '.join(command)}\n{proc.stdout[-12000:]}")


def compare(rel: str, roots: list[Path]) -> dict[str, Any]:
    values = []
    for root in roots:
        path = root / rel
        values.append({
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": sha_path(path) if path.is_file() else None,
        })
    equal = all(item == values[0] for item in values[1:])
    return {"path": rel, "equal": equal, "instances": values}


def main() -> int:
    missing = [rel for rel in SOURCE_BOUNDARIES if not (ROOT / rel).is_file()]
    if missing:
        raise FileNotFoundError("missing source boundaries: " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="tom-wqk-060-clean-") as td:
        temp = Path(td)
        builds = []
        for index in (1, 2):
            destination = temp / f"build{index}" / ROOT.name
            destination.parent.mkdir(parents=True)
            shutil.copytree(ROOT, destination, ignore=ignore)
            remove_generated(destination)
            run_build(destination)
            builds.append(destination)

        roots = [ROOT, *builds]
        source_records = [compare(rel, roots) for rel in SOURCE_BOUNDARIES]
        generated_records = [compare(rel, roots) for rel in GENERATED_BOUNDARIES]
        source_equal = all(item["equal"] for item in source_records)
        generated_equal = all(item["equal"] for item in generated_records)

        stores = [tree_record(root / "examples/learner06/promotion_store") for root in roots]
        store_equal = all(item == stores[0] for item in stores[1:])
        two_builds_equal = (
            all(item["instances"][1] == item["instances"][2] for item in source_records)
            and all(item["instances"][1] == item["instances"][2] for item in generated_records)
            and stores[1] == stores[2]
        )
        all_equal = source_equal and generated_equal and store_equal
        record = attach_hash({
            "schema": "TOM-WQK-0.6-TWO-BUILD-CLEAN-REPLAY-1.0",
            "release": "0.6.0",
            "status": "pass" if all_equal and two_builds_equal else "fail",
            "two_builds_equal": two_builds_equal,
            "all_boundaries_equal": source_equal and generated_equal,
            "source_boundaries_equal": source_equal,
            "generated_boundaries_equal": generated_equal,
            "store_trees_equal": store_equal,
            "compared_boundaries": len(source_records) + len(generated_records),
            "source_boundary_count": len(source_records),
            "generated_boundary_count": len(generated_records),
            "source_boundaries": source_records,
            "generated_boundaries": generated_records,
            "promotion_store_trees": stores,
            "claim": "two generated-output-free builds preserve literal authority and reproduce declared programs, traces, artifacts, validation evidence, and the immutable store tree",
        })
        VAL.mkdir(parents=True, exist_ok=True)
        (VAL / "clean_rebuild.json").write_bytes(canonical_bytes(record) + b"\n")
        print(json.dumps({
            "status": record["status"],
            "compared_boundaries": record["compared_boundaries"],
            "source_boundaries": len(source_records),
            "generated_boundaries": len(generated_records),
            "two_builds_equal": two_builds_equal,
            "store_trees_equal": store_equal,
            "content_hash": record["content_hash"],
        }, indent=2, sort_keys=True))
        return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
