from __future__ import annotations

"""Rebuild 0.2 from literal sources and compare fixed files plus world trees."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world.canonical import attach_hash, canonical_bytes, digest_file

FIXED_BOUNDARIES = [
    "examples/polar_loop.tmg",
    "examples/polar_loop.expected.json",
    "examples/exact19_rule.tmg",
    "examples/exact19_rule.expected.json",
    "examples/nineteen_hinge.expected.json",
    "examples/world_counter/counter_program.json",
    "examples/world_counter/counter_program.tmg",
    "examples/world_counter/initial_transaction.json",
    "examples/artifacts/roadmap_and_starter.source.json",
    "examples/artifacts/roadmap_and_starter.tmg",
    "examples/artifacts/roadmap_and_starter.tmg.compile.json",
    "artifacts/TOM_AGI_ROADMAP_AND_STARTER.md",
    "validation/roadmap_artifact.python.trace.json",
    "validation/roadmap_artifact.c.trace.json",
    "validation/roadmap_artifact.emit_records.json",
    "validation/roadmap_artifact_proof.json",
    "examples/artifacts/world_query_kernel_0_2_release.source.json",
    "examples/artifacts/world_query_kernel_0_2_release.tmg",
    "examples/artifacts/world_query_kernel_0_2_release.tmg.compile.json",
    "artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md",
    "validation/release_0_2_artifact.python.trace.json",
    "validation/release_0_2_artifact.c.trace.json",
    "validation/release_0_2_artifact.emit_records.json",
    "validation/release_0_2_artifact_proof.json",
    "validation/counter_initial_commit.json",
    "validation/counter_event_commit.json",
    "validation/state_at_3.json",
    "validation/next_event.json",
    "validation/events_in_support.json",
    "validation/compatible.json",
    "validation/incompatible.json",
    "validation/grammar_expansion.json",
    "validation/reconstruction.json",
    "validation/lineage_reconstruction.json",
    "validation/counter_python_trace.json",
    "validation/counter_c_trace.json",
    "validation/counter_world_manifest.json",
    "validation/index_benchmark/initial_commit.json",
    "validation/index_benchmark/checkpoint_commit.json",
    "validation/index_benchmark/postings.json",
    "validation/index_benchmark/events_indexed.json",
    "validation/index_benchmark/events_exhaustive.json",
    "validation/index_benchmark/state_at_999_indexed.json",
    "validation/index_benchmark/state_at_999_exhaustive.json",
    "validation/index_benchmark/batch_indexed.json",
    "validation/index_benchmark/batch_exhaustive.json",
    "validation/index_benchmark/index_rebuild.json",
    "validation/index_benchmark/audit.json",
    "validation/index_benchmark/report.json",
    "validation/static_assets.json",
]

TREE_BOUNDARIES = [
    "world/counter_store",
    "world/index_benchmark_store",
]


def run(cmd: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / "src/python")
    process = subprocess.Popen(
        cmd, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    started = time.monotonic()
    next_heartbeat = started + 10.0
    while process.poll() is None:
        now = time.monotonic()
        if now - started > timeout:
            process.kill()
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"command timed out: {' '.join(cmd)}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
        if now >= next_heartbeat:
            print(f"  clean rebuild command active after {int(now - started)}s: {' '.join(cmd)}", flush=True)
            next_heartbeat = now + 10.0
        time.sleep(0.25)
    stdout, stderr = process.communicate()
    result = subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        data = path.read_bytes()
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return entries


def tree_manifest(root: Path) -> dict[str, Any]:
    entries = tree_entries(root)
    fold = bytearray()
    for item in entries:
        data = canonical_bytes(item)
        fold.extend(len(data).to_bytes(8, "little"))
        fold.extend(data)
    return {
        "file_count": len(entries),
        "total_bytes": sum(int(item["bytes"]) for item in entries),
        "tree_sha256": "sha256:" + hashlib.sha256(fold).hexdigest(),
        "entries_sha256": "sha256:" + hashlib.sha256(canonical_bytes(entries)).hexdigest(),
    }


def compare_trees(outer: Path, rebuilt: Path) -> tuple[bool, dict[str, Any]]:
    outer_entries = tree_entries(outer)
    rebuilt_entries = tree_entries(rebuilt)
    outer_by_path = {str(item["path"]): item for item in outer_entries}
    rebuilt_by_path = {str(item["path"]): item for item in rebuilt_entries}
    mismatches: list[dict[str, Any]] = []
    for relative in sorted(set(outer_by_path) | set(rebuilt_by_path)):
        left = outer_by_path.get(relative)
        right = rebuilt_by_path.get(relative)
        if left != right:
            mismatches.append({"path": relative, "outer": left, "rebuilt": right})
    outer_manifest = tree_manifest(outer)
    rebuilt_manifest = tree_manifest(rebuilt)
    equal = not mismatches and outer_manifest == rebuilt_manifest
    return equal, {
        "outer": outer_manifest,
        "rebuilt": rebuilt_manifest,
        "equal": equal,
        "mismatch_count": len(mismatches),
        "mismatch_sample": mismatches[:16],
    }


def main() -> int:
    missing = [relative for relative in FIXED_BOUNDARIES if not (ROOT / relative).is_file()]
    missing += [relative for relative in TREE_BOUNDARIES if not (ROOT / relative).is_dir()]
    if missing:
        raise FileNotFoundError("outer build is missing boundaries: " + ", ".join(missing))
    expected = {relative: digest_file(ROOT / relative) for relative in FIXED_BOUNDARIES}
    expected_trees = {relative: tree_manifest(ROOT / relative) for relative in TREE_BOUNDARIES}

    with tempfile.TemporaryDirectory(prefix="tom-world-clean-rebuild-") as directory:
        copy_root = Path(directory) / ROOT.name
        print("  copying source capsule for clean rebuild", flush=True)
        shutil.copytree(
            ROOT,
            copy_root,
            ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc", "*.pyo"),
        )
        run(["make", "clean-generated"], copy_root)
        print("  rebuilding generated boundaries from literal sources", flush=True)
        run(["make", "validate-core"], copy_root)
        print("  comparing fixed files and content-addressed world trees", flush=True)

        comparisons: dict[str, dict[str, object]] = {}
        equal = True
        for relative, outer_hash in expected.items():
            path = copy_root / relative
            inner_hash = digest_file(path) if path.is_file() else None
            same = inner_hash == outer_hash
            equal &= same
            comparisons[relative] = {
                "outer_sha256": outer_hash,
                "rebuilt_sha256": inner_hash,
                "equal": same,
            }

        tree_comparisons: dict[str, Any] = {}
        for relative, outer_manifest in expected_trees.items():
            tree_equal, detail = compare_trees(ROOT / relative, copy_root / relative)
            detail["outer_expected"] = outer_manifest
            equal &= tree_equal
            tree_comparisons[relative] = detail

        if not equal:
            failed_files = [relative for relative, result in comparisons.items() if not result["equal"]]
            failed_trees = [relative for relative, result in tree_comparisons.items() if not result["equal"]]
            raise RuntimeError(
                "clean rebuild boundary mismatch: files=" + ", ".join(failed_files)
                + "; trees=" + ", ".join(failed_trees)
            )

    record = attach_hash({
        "schema": "TOM-WORLD-CLEAN-REBUILD-0.2",
        "version": "0.2.0",
        "generated": "2026-09-01",
        "status": "pass",
        "source_profile": "literal sources after make clean-generated",
        "command": "make validate-core",
        "compared_boundaries": len(comparisons) + len(tree_comparisons),
        "file_boundaries": comparisons,
        "tree_boundaries": tree_comparisons,
        "all_boundaries_equal": True,
    })
    (ROOT / "validation/clean_rebuild.json").write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({
        "status": record["status"],
        "compared_boundaries": record["compared_boundaries"],
        "file_boundaries": len(comparisons),
        "tree_boundaries": len(tree_comparisons),
        "content_hash": record["content_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
