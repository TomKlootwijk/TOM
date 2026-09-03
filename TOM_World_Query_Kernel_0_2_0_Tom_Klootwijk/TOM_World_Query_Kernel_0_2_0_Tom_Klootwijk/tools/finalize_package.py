from __future__ import annotations

"""Finalize, verify, replay, and publish TOM World & Query Kernel 0.2.

The ZIP is deterministic at the container layer: regular files only, sorted
members, one fixed timestamp and mode, and no build/cache products.  The
finalizer validates internal inventories, safely extracts the archive, removes
all generated boundaries, runs the complete validation again, and compares
selected files plus aggregate manifests of both content-addressed world trees.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT.parent
PACKAGE_NAME = ROOT.name
ZIP_PATH = OUT_DIR / f"{PACKAGE_NAME}.zip"
FIXED_ZIP_TIME = (2026, 9, 1, 0, 0, 0)
GENERATED = "2026-09-01T00:00:00Z"

PACKAGE_MANIFEST = ROOT / "checksums/PACKAGE_MANIFEST.json"
PACKAGE_CHECKSUMS = ROOT / "checksums/SHA256SUMS.txt"
RELEASE_MANIFEST = OUT_DIR / "TOM_World_Query_Kernel_0_2_0_release_manifest.json"
RELEASE_CHECKSUMS = OUT_DIR / "TOM_World_Query_Kernel_0_2_0_SHA256SUMS.txt"

# unittest writes elapsed wall time; the deterministic count/result are in the
# content-addressed validation report, so the raw log is excluded.
EXCLUDED_RELEASE_FILES = {
    Path("validation/tests.txt"),
    Path("validation/package_manifest.json"),
}

REPLAY_FILE_BOUNDARIES = [
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
    "validation/clean_rebuild.json",
    "validation/validation_report.json",
    "validation/VALIDATION.md",
]

REPLAY_TREE_BOUNDARIES = [
    "world/counter_store",
    "world/index_benchmark_store",
]

COMPANION_COPIES = {
    "TOM_AGI_ROADMAP_AND_STARTER_0_2.md": "artifacts/TOM_AGI_ROADMAP_AND_STARTER.md",
    "TOM_WORLD_QUERY_KERNEL_0_2.md": "spec/TOM_WORLD_QUERY_KERNEL_0_2.md",
    "TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md": "artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md",
    "TOM_World_Query_Kernel_0_2_benchmark_report.json": "validation/index_benchmark/report.json",
    "TOM_World_Query_Kernel_0_2_events_indexed.json": "validation/index_benchmark/events_indexed.json",
    "TOM_World_Query_Kernel_0_2_state_at_999_indexed.json": "validation/index_benchmark/state_at_999_indexed.json",
    "TOM_World_Query_Kernel_0_2_batch_indexed.json": "validation/index_benchmark/batch_indexed.json",
    "TOM_World_Query_Kernel_0_2_audit.json": "validation/index_benchmark/audit.json",
    "TOM_World_Query_Kernel_0_2_release_artifact_proof.json": "validation/release_0_2_artifact_proof.json",
    "TOM_World_Query_Kernel_0_2_validation_report.json": "validation/validation_report.json",
    "TOM_World_Query_Kernel_0_2_clean_rebuild.json": "validation/clean_rebuild.json",
    "TOM_seed_genome_2026-09-01.txt": "TOM_seed_genome_2026-09-01.txt",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return entries


def tree_manifest(root: Path) -> dict[str, Any]:
    entries = tree_entries(root)
    fold = bytearray()
    for item in entries:
        data = json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")
        fold.extend(len(data).to_bytes(8, "little"))
        fold.extend(data)
    canonical_entries = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "file_count": len(entries),
        "total_bytes": sum(int(item["bytes"]) for item in entries),
        "tree_sha256": "sha256:" + hashlib.sha256(fold).hexdigest(),
        "entries_sha256": "sha256:" + hashlib.sha256(canonical_entries).hexdigest(),
    }


def verify_prerequisites() -> dict[str, Any]:
    required = [
        "TOM_seed_genome_2026-09-01.txt",
        "AGENTS.md",
        "README.md",
        "docs/ROADMAP.md",
        "docs/ROADMAP_AND_STARTER.md",
        "docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md",
        "docs/BENCHMARK_10000.md",
        "spec/TOM_WORLD_QUERY_KERNEL_0_2.md",
        "src/python/tom_world/indexes.py",
        "src/python/tom_world/planner.py",
        "src/python/tom_world/audit.py",
        "examples/index_benchmark/initial_transaction.json",
        "examples/index_benchmark/checkpoint_transaction.json",
        "world/counter_store/HEAD",
        "world/index_benchmark_store/HEAD",
        "artifacts/TOM_AGI_ROADMAP_AND_STARTER.md",
        "artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md",
        "validation/roadmap_artifact_proof.json",
        "validation/release_0_2_artifact_proof.json",
        "validation/index_benchmark/report.json",
        "validation/index_benchmark/audit.json",
        "validation/clean_rebuild.json",
        "validation/validation_report.json",
    ]
    missing = [relative for relative in required if not (ROOT / relative).is_file()]
    if missing:
        raise RuntimeError("missing release prerequisites: " + ", ".join(missing))

    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    expected_seed = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
    if len(seed) != 244 or seed.endswith((b"\n", b"\r")) or sha256_bytes(seed) != expected_seed:
        raise RuntimeError("canonical seed prerequisite mismatch")

    validation = json.loads((ROOT / "validation/validation_report.json").read_text(encoding="utf-8"))
    test_checks = [
        item
        for item in validation.get("checks", [])
        if isinstance(item, dict) and item.get("name") == "conformance tests"
    ]
    if len(test_checks) != 1 or test_checks[0].get("status") != "pass":
        raise RuntimeError("validation report must have one passing conformance-tests check")
    test_check = test_checks[0]
    test_evidence = test_check.get("evidence")
    test_count = test_evidence.get("count") if type(test_evidence) is dict else None
    if type(test_count) is not int or test_count < 60:
        raise RuntimeError("validation report has no valid conformance test count")
    clean = json.loads((ROOT / "validation/clean_rebuild.json").read_text(encoding="utf-8"))
    benchmark = json.loads((ROOT / "validation/index_benchmark/report.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "validation/index_benchmark/audit.json").read_text(encoding="utf-8"))
    roadmap = json.loads((ROOT / "validation/roadmap_artifact_proof.json").read_text(encoding="utf-8"))
    release_artifact = json.loads((ROOT / "validation/release_0_2_artifact_proof.json").read_text(encoding="utf-8"))
    if validation.get("status") != "pass" or validation.get("failed") != 0 or validation.get("passed") != 20:
        raise RuntimeError("final validation report is not the expected 20-check passing report")
    if clean.get("status") != "pass" or clean.get("all_boundaries_equal") is not True:
        raise RuntimeError("clean-rebuild evidence is not passing")
    if benchmark.get("status") != "pass" or benchmark.get("world", {}).get("record_count") != 10_000:
        raise RuntimeError("10,000-record benchmark prerequisite is not passing")
    if not all(benchmark.get("acceptance", {}).values()):
        raise RuntimeError("benchmark acceptance map contains a failure")
    if audit.get("valid") is not True or audit.get("errors") or any(v.get("count") for v in audit.get("orphans", {}).values()):
        raise RuntimeError("full ancestry audit prerequisite is not passing")
    for name, proof in (("roadmap", roadmap), ("release", release_artifact)):
        if (
            proof.get("status") != "pass"
            or proof.get("artifact", {}).get("source_byte_equal") is not True
            or proof.get("execution", {}).get("python_c_full_trace_equal") is not True
        ):
            raise RuntimeError(f"{name} documentation artifact proof is not passing")

    return {
        "seed_sha256": expected_seed,
        "validation_content_hash": validation.get("content_hash"),
        "validation_checks": validation.get("passed"),
        "test_count": test_count,
        "clean_rebuild_content_hash": clean.get("content_hash"),
        "clean_rebuild_boundaries": clean.get("compared_boundaries"),
        "benchmark_content_hash": benchmark.get("content_hash"),
        "benchmark_records": benchmark["world"]["record_count"],
        "benchmark_candidate_path": benchmark["events_in_support"]["candidate_count_path"],
        "checkpoint_steps_saved": benchmark["checkpoint_replay"]["saved_steps"],
        "audit_content_hash": audit.get("content_hash"),
        "roadmap_artifact_sha256": roadmap["artifact"].get("sha256"),
        "release_artifact_sha256": release_artifact["artifact"].get("sha256"),
    }


def clean_transients() -> None:
    shutil.rmtree(ROOT / "build", ignore_errors=True)
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)
    for directory in sorted(ROOT.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for pattern in ("*.pyc", "*.pyo", ".DS_Store"):
        for path in ROOT.rglob(pattern):
            if path.is_file():
                path.unlink()
    for relative in EXCLUDED_RELEASE_FILES:
        (ROOT / relative).unlink(missing_ok=True)
    PACKAGE_MANIFEST.unlink(missing_ok=True)
    PACKAGE_CHECKSUMS.unlink(missing_ok=True)


def payload_files(*, exclude_inventory: bool = False) -> list[Path]:
    excluded = set(EXCLUDED_RELEASE_FILES)
    if exclude_inventory:
        excluded.update({PACKAGE_MANIFEST.relative_to(ROOT), PACKAGE_CHECKSUMS.relative_to(ROOT)})
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if relative in excluded:
            continue
        if any(part in {".git", ".pytest_cache", "dist", "build", "__pycache__"} for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def write_internal_inventory(prerequisites: dict[str, Any]) -> tuple[dict[str, Any], int]:
    files = payload_files(exclude_inventory=True)
    manifest = {
        "schema": "TOM-WORLD-QUERY-PACKAGE-MANIFEST-0.2",
        "package": PACKAGE_NAME,
        "release": "0.2.0",
        "generated": GENERATED,
        "profile": "TOM-WORLD-QUERY-KERNEL-0.2",
        "tomagi_abi": "1.0",
        "prerequisites": prerequisites,
        "world_tree_manifests": {
            relative: tree_manifest(ROOT / relative) for relative in REPLAY_TREE_BOUNDARIES
        },
        "file_count_excluding_manifest_and_checksum": len(files),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }
    write_json(PACKAGE_MANIFEST, manifest)

    checksum_files = [path for path in payload_files() if path != PACKAGE_CHECKSUMS]
    lines = [f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}" for path in checksum_files]
    PACKAGE_CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    PACKAGE_CHECKSUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest, len(lines)


def write_deterministic_zip() -> list[str]:
    ZIP_PATH.unlink(missing_ok=True)
    names: list[str] = []
    with zipfile.ZipFile(ZIP_PATH, "w") as archive:
        for path in payload_files():
            relative = path.relative_to(ROOT).as_posix()
            arcname = f"{PACKAGE_NAME}/{relative}"
            info = zipfile.ZipInfo(arcname, date_time=FIXED_ZIP_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.flag_bits |= 0x800
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
            names.append(arcname)
    return names


def validate_member_name(name: str) -> None:
    member = PurePosixPath(name)
    if member.is_absolute() or not member.parts or member.parts[0] != PACKAGE_NAME:
        raise RuntimeError(f"unsafe ZIP member: {name!r}")
    if any(part in {"", ".", ".."} for part in member.parts):
        raise RuntimeError(f"unsafe ZIP member: {name!r}")


def verify_zip(expected_names: list[str]) -> None:
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != expected_names or names != sorted(names) or len(names) != len(set(names)):
            raise RuntimeError("ZIP members are not the expected unique sorted sequence")
        for info in infos:
            validate_member_name(info.filename)
            if info.date_time != FIXED_ZIP_TIME:
                raise RuntimeError(f"unexpected ZIP timestamp: {info.filename}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode != 0o100644:
                raise RuntimeError(f"unexpected ZIP mode {oct(mode)}: {info.filename}")
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failure: {bad}")


def verify_extracted_inventory(extracted_root: Path) -> None:
    manifest_path = extracted_root / "checksums/PACKAGE_MANIFEST.json"
    checksum_path = extracted_root / "checksums/SHA256SUMS.txt"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed: set[str] = set()
    for record in manifest.get("files", []):
        path = extracted_root / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"package-manifest mismatch: {record['path']}")
        listed.add(record["path"])
    expected_manifest_set = {
        path.relative_to(extracted_root).as_posix()
        for path in extracted_root.rglob("*")
        if path.is_file() and path not in {manifest_path, checksum_path}
    }
    if listed != expected_manifest_set:
        raise RuntimeError(
            "package manifest inventory mismatch: "
            f"missing={sorted(expected_manifest_set - listed)[:16]}, extra={sorted(listed - expected_manifest_set)[:16]}"
        )

    checked: set[str] = set()
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = extracted_root / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"internal checksum mismatch: {relative}")
        checked.add(relative)
    expected_checksums = {
        path.relative_to(extracted_root).as_posix()
        for path in extracted_root.rglob("*")
        if path.is_file() and path != checksum_path
    }
    if checked != expected_checksums:
        raise RuntimeError(
            "internal checksum inventory mismatch: "
            f"missing={sorted(expected_checksums - checked)[:16]}, extra={sorted(checked - expected_checksums)[:16]}"
        )


def run_command(command: list[str], *, cwd: Path, timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(cwd / "src/python")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = time.monotonic()
    next_heartbeat = started + 10.0
    while process.poll() is None:
        now = time.monotonic()
        if now - started > timeout:
            process.kill()
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"command timed out: {' '.join(command)}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
        if now >= next_heartbeat:
            print(f"    still running after {int(now - started)}s: {' '.join(command)}", flush=True)
            next_heartbeat = now + 10.0
        time.sleep(0.25)
    stdout, stderr = process.communicate()
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def compare_tree_manifests(expected_root: Path, rebuilt_root: Path) -> tuple[bool, dict[str, Any]]:
    expected = tree_manifest(expected_root)
    rebuilt = tree_manifest(rebuilt_root)
    return expected == rebuilt, {"expected": expected, "replayed": rebuilt, "equal": expected == rebuilt}


def verify_clean_archive_replay() -> dict[str, Any]:
    expected_files = {relative: sha256_file(ROOT / relative) for relative in REPLAY_FILE_BOUNDARIES}
    expected_trees = {relative: tree_manifest(ROOT / relative) for relative in REPLAY_TREE_BOUNDARIES}

    with tempfile.TemporaryDirectory(prefix="tom-world-query-0-2-release-") as directory:
        extraction = Path(directory)
        with zipfile.ZipFile(ZIP_PATH, "r") as archive:
            for info in archive.infolist():
                validate_member_name(info.filename)
            archive.extractall(extraction)
        extracted_root = extraction / PACKAGE_NAME
        verify_extracted_inventory(extracted_root)

        run_command(["make", "clean-generated"], cwd=extracted_root)
        run_command(["make", "validate"], cwd=extracted_root)

        file_comparisons: dict[str, Any] = {}
        equal = True
        for relative, expected_hash in expected_files.items():
            rebuilt = extracted_root / relative
            actual_hash = sha256_file(rebuilt) if rebuilt.is_file() else None
            same = actual_hash == expected_hash
            equal &= same
            file_comparisons[relative] = {
                "expected_sha256": expected_hash,
                "replayed_sha256": actual_hash,
                "equal": same,
            }

        tree_comparisons: dict[str, Any] = {}
        for relative, expected_manifest in expected_trees.items():
            actual_manifest = tree_manifest(extracted_root / relative)
            same = actual_manifest == expected_manifest
            equal &= same
            tree_comparisons[relative] = {
                "expected": expected_manifest,
                "replayed": actual_manifest,
                "equal": same,
            }

        if not equal:
            failed_files = [relative for relative, item in file_comparisons.items() if not item["equal"]]
            failed_trees = [relative for relative, item in tree_comparisons.items() if not item["equal"]]
            raise RuntimeError(
                "archive clean replay mismatch: files=" + ", ".join(failed_files)
                + "; trees=" + ", ".join(failed_trees)
            )

    return {
        "status": "pass",
        "zip_crc_and_path_safety": True,
        "internal_manifest_and_checksums": True,
        "command": "make clean-generated && make validate",
        "file_boundaries": len(file_comparisons),
        "tree_boundaries": len(tree_comparisons),
        "compared_boundaries": len(file_comparisons) + len(tree_comparisons),
        "all_boundaries_equal": True,
        "world_trees": tree_comparisons,
    }


def publish_companions(prerequisites: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    for name in list(COMPANION_COPIES) + [RELEASE_MANIFEST.name, RELEASE_CHECKSUMS.name]:
        (OUT_DIR / name).unlink(missing_ok=True)

    companions: list[dict[str, Any]] = []
    for destination_name, source_relative in sorted(COMPANION_COPIES.items()):
        source = ROOT / source_relative
        destination = OUT_DIR / destination_name
        destination.write_bytes(source.read_bytes())
        companions.append({
            "path": destination.name,
            "source_in_package": source_relative,
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        })

    benchmark = json.loads((ROOT / "validation/index_benchmark/report.json").read_text(encoding="utf-8"))
    release = {
        "schema": "TOM-WORLD-QUERY-RELEASE-MANIFEST-0.2",
        "release": "TOM World & Query Kernel 0.2.0",
        "generated": GENERATED,
        "status": "pass",
        "package": {
            "path": ZIP_PATH.name,
            "bytes": ZIP_PATH.stat().st_size,
            "sha256": sha256_file(ZIP_PATH),
            "root": PACKAGE_NAME,
            "entries": len(payload_files()),
        },
        "validation": prerequisites,
        "archive_replay": replay,
        "benchmark": {
            "records": 10_000,
            "candidate_path": benchmark["events_in_support"]["candidate_count_path"],
            "event_ticks": benchmark["events_in_support"]["event_ticks"],
            "checkpoint_replayed_steps": benchmark["checkpoint_replay"]["indexed_replayed_steps"],
            "root_replayed_steps": benchmark["checkpoint_replay"]["exhaustive_replayed_steps"],
            "steps_saved": benchmark["checkpoint_replay"]["saved_steps"],
            "batch_semantic_equal": benchmark["batch"]["semantic_equal"],
            "audit_valid": benchmark["audit"]["valid"],
            "audit_errors": benchmark["audit"]["errors"],
            "store_tree": benchmark["world"]["store_tree"],
        },
        "implemented": [
            "immutable content-addressed secondary indexes",
            "deterministic indexed and exhaustive query plans",
            "active interval relation filtering",
            "ancestry-bound exact replay checkpoints",
            "stable declared-order batch queries",
            "stored transaction bodies and full ancestry/reachability audit",
            "10,000-record frozen benchmark",
            "literal TOMAGI EMIT 0.2 release documentation artifact",
        ],
        "next_target": (
            "World & Query Kernel 0.3: typed relation intervals, certified crossing brackets, "
            "simultaneous-event sets, deterministic ordering, and trusted baseline comparison."
        ),
        "not_claimed": [
            "continuous or interval-certified root solving",
            "simultaneous-event resolution",
            "autonomous definition learning",
            "general planning or external tool execution",
            "grounded multimodal perception",
            "new physical GPU execution evidence",
            "AGI",
        ],
        "accompanying_files": companions,
    }
    write_json(RELEASE_MANIFEST, release)

    checksum_targets = [ZIP_PATH, RELEASE_MANIFEST] + [OUT_DIR / name for name in COMPANION_COPIES]
    checksum_targets = sorted(set(checksum_targets), key=lambda path: path.name)
    RELEASE_CHECKSUMS.write_text(
        "\n".join(f"{sha256_file(path)}  {path.name}" for path in checksum_targets) + "\n",
        encoding="utf-8",
    )
    return release


def main() -> None:
    print("[1/7] verifying 0.2 release prerequisites", flush=True)
    prerequisites = verify_prerequisites()
    print("[2/7] removing transient and non-reproducible build logs", flush=True)
    clean_transients()
    print("[3/7] writing internal manifest and SHA-256 inventory", flush=True)
    manifest, checksum_count = write_internal_inventory(prerequisites)
    print("[4/7] writing deterministic ZIP", flush=True)
    zip_names = write_deterministic_zip()
    print("[5/7] verifying ZIP structure and CRC", flush=True)
    verify_zip(zip_names)
    print("[6/7] extracting, cleaning, rebuilding, and comparing archive boundaries", flush=True)
    replay = verify_clean_archive_replay()
    print("[7/7] publishing companion files and release manifest", flush=True)
    release = publish_companions(prerequisites, replay)

    result = {
        "status": "pass",
        "package": release["package"],
        "zip_entries": len(zip_names),
        "internal_files_excluding_manifest_and_checksum": manifest["file_count_excluding_manifest_and_checksum"],
        "internal_checksum_entries": checksum_count,
        "archive_replay_boundaries": replay["compared_boundaries"],
        "accompanying_files": len(release["accompanying_files"]),
        "release_manifest": {
            "path": RELEASE_MANIFEST.name,
            "sha256": sha256_file(RELEASE_MANIFEST),
        },
        "release_checksums": {
            "path": RELEASE_CHECKSUMS.name,
            "sha256": sha256_file(RELEASE_CHECKSUMS),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
