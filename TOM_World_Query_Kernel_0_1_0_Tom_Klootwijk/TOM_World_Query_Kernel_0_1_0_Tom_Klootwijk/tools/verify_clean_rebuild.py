from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

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
    "validation/roadmap_artifact.python.trace.json",
    "validation/roadmap_artifact.c.trace.json",
    "validation/roadmap_artifact.emit_records.json",
    "validation/roadmap_artifact_proof.json",
    "validation/static_assets.json",
    "validation/validation_report.json",
]


def run(cmd: list[str], cwd: Path, timeout: int = 420) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / "src/python")
    process = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if process.returncode:
        raise RuntimeError(
            f"command failed ({process.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
        )
    return process


def world_files(root: Path) -> list[str]:
    base = root / "world/counter_store"
    return sorted(path.relative_to(root).as_posix() for path in base.rglob("*") if path.is_file())


def main() -> int:
    boundaries = FIXED_BOUNDARIES + world_files(ROOT)
    missing = [relative for relative in boundaries if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError("outer build is missing boundaries: " + ", ".join(missing))
    expected = {relative: digest_file(ROOT / relative) for relative in boundaries}

    with tempfile.TemporaryDirectory(prefix="tom-world-clean-rebuild-") as directory:
        copy_root = Path(directory) / ROOT.name
        shutil.copytree(
            ROOT,
            copy_root,
            ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc", "*.pyo"),
        )
        run(["make", "clean-generated"], copy_root)
        build = run(["make", "validate-core"], copy_root)
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
        if not equal:
            failed = [relative for relative, result in comparisons.items() if not result["equal"]]
            raise RuntimeError("clean rebuild boundary mismatch: " + ", ".join(failed))

    record = attach_hash({
        "schema": "TOM-WORLD-CLEAN-REBUILD-0.1",
        "generated": "2026-09-01",
        "status": "pass",
        "source_profile": "literal sources after make clean-generated",
        "command": "make validate-core",
        "compared_boundaries": len(comparisons),
        "all_boundaries_equal": True,
        "boundaries": comparisons,
    })
    (ROOT / "validation/clean_rebuild.json").write_bytes(canonical_bytes(record) + b"\n")
    print(json.dumps({
        "status": record["status"],
        "compared_boundaries": record["compared_boundaries"],
        "content_hash": record["content_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
