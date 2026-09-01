from __future__ import annotations

"""Finalize, verify, and publish TOM World & Query Kernel 0.1.

The release archive is deterministic at the ZIP-container layer: entries are
sorted, timestamps and file modes are fixed, and only regular repository files
are included.  The finalizer verifies internal hashes, safely extracts the ZIP,
performs a generated-output-free ``make validate`` replay, and compares all
claimed reproducible boundaries before publishing the archive.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
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

# The raw unittest log contains a wall-time duration and is therefore omitted
# from the release.  Its deterministic result/count are preserved in the
# content-addressed validation report.
EXCLUDED_RELEASE_FILES = {
    Path("validation/tests.txt"),
    Path("validation/package_manifest.json"),  # stale TOMAGI 1.0 finalizer path
}

REPLAY_BOUNDARIES = [
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
    "validation/clean_rebuild.json",
    "validation/validation_report.json",
    "validation/VALIDATION.md",
]

COMPANION_COPIES = {
    "TOM_AGI_ROADMAP_AND_STARTER.md": "artifacts/TOM_AGI_ROADMAP_AND_STARTER.md",
    "TOM_WORLD_QUERY_KERNEL_0_1.md": "spec/TOM_WORLD_QUERY_KERNEL_0_1.md",
    "TOM_World_Query_Kernel_validation_report.json": "validation/validation_report.json",
    "TOM_World_Query_Kernel_clean_rebuild.json": "validation/clean_rebuild.json",
    "TOM_World_Query_Kernel_next_event_certificate.json": "validation/next_event.json",
    "TOM_World_Query_Kernel_roadmap_artifact_proof.json": "validation/roadmap_artifact_proof.json",
}

RELEASE_MANIFEST = OUT_DIR / "TOM_World_Query_Kernel_0_1_0_release_manifest.json"
RELEASE_CHECKSUMS = OUT_DIR / "TOM_World_Query_Kernel_0_1_0_SHA256SUMS.txt"


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


def verify_prerequisites() -> dict[str, Any]:
    required = [
        "TOM_seed_genome_2026-09-01.txt",
        "AGENTS.md",
        "README.md",
        "docs/ROADMAP.md",
        "docs/ROADMAP_AND_STARTER.md",
        "docs/IMPLEMENTATION_STATUS.md",
        "spec/TOM_WORLD_QUERY_KERNEL_0_1.md",
        "src/python/tom_world/query.py",
        "examples/world_counter/world_source.json",
        "world/counter_store/HEAD",
        "artifacts/TOM_AGI_ROADMAP_AND_STARTER.md",
        "validation/roadmap_artifact_proof.json",
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
    clean = json.loads((ROOT / "validation/clean_rebuild.json").read_text(encoding="utf-8"))
    roadmap = json.loads((ROOT / "validation/roadmap_artifact_proof.json").read_text(encoding="utf-8"))
    if validation.get("status") != "pass" or validation.get("failed") != 0 or validation.get("passed") != 16:
        raise RuntimeError("final validation report is not the expected 16-check passing report")
    if clean.get("status") != "pass" or clean.get("all_boundaries_equal") is not True:
        raise RuntimeError("clean-rebuild evidence is not passing")
    if roadmap.get("status") != "pass" or roadmap["artifact"].get("source_byte_equal") is not True:
        raise RuntimeError("roadmap artifact proof is not passing")
    if roadmap["execution"].get("python_c_full_trace_equal") is not True:
        raise RuntimeError("roadmap Python/C trace equality is not passing")

    return {
        "seed_sha256": expected_seed,
        "validation_content_hash": validation.get("content_hash"),
        "validation_checks": validation.get("passed"),
        "clean_rebuild_content_hash": clean.get("content_hash"),
        "clean_rebuild_boundaries": clean.get("compared_boundaries"),
        "roadmap_artifact_sha256": roadmap["artifact"].get("sha256"),
        "roadmap_program_sha256": roadmap["program"].get("sha256"),
        "roadmap_cells": roadmap["program"].get("cells"),
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
        excluded.update({
            PACKAGE_MANIFEST.relative_to(ROOT),
            PACKAGE_CHECKSUMS.relative_to(ROOT),
        })
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
        "schema": "TOM-WORLD-QUERY-PACKAGE-MANIFEST-0.1",
        "package": PACKAGE_NAME,
        "release": "0.1.0",
        "generated": GENERATED,
        "profile": "TOM-WORLD-QUERY-KERNEL-0.1",
        "tomagi_abi": "1.0",
        "prerequisites": prerequisites,
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
    lines = [
        f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}"
        for path in checksum_files
    ]
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
    manifest = json.loads((extracted_root / "checksums/PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    for record in manifest.get("files", []):
        path = extracted_root / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"package-manifest mismatch: {record['path']}")

    checksum_path = extracted_root / "checksums/SHA256SUMS.txt"
    checked: set[str] = set()
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = extracted_root / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"internal checksum mismatch: {relative}")
        checked.add(relative)
    expected = {
        path.relative_to(extracted_root).as_posix()
        for path in extracted_root.rglob("*")
        if path.is_file() and path != checksum_path
    }
    if checked != expected:
        raise RuntimeError(
            "internal checksum inventory mismatch: "
            f"missing={sorted(expected - checked)}, extra={sorted(checked - expected)}"
        )


def run_command(command: list[str], *, cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(cwd / "src/python")
    process = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if process.returncode:
        raise RuntimeError(
            f"command failed ({process.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
        )
    return process


def world_store_files(root: Path) -> list[str]:
    base = root / "world/counter_store"
    return sorted(path.relative_to(root).as_posix() for path in base.rglob("*") if path.is_file())


def verify_clean_archive_replay() -> dict[str, Any]:
    boundary_names = REPLAY_BOUNDARIES + world_store_files(ROOT)
    expected = {relative: sha256_file(ROOT / relative) for relative in boundary_names}

    with tempfile.TemporaryDirectory(prefix="tom-world-query-release-") as directory:
        extraction = Path(directory)
        with zipfile.ZipFile(ZIP_PATH, "r") as archive:
            for info in archive.infolist():
                validate_member_name(info.filename)
            archive.extractall(extraction)
        extracted_root = extraction / PACKAGE_NAME
        verify_extracted_inventory(extracted_root)

        run_command(["make", "clean-generated"], cwd=extracted_root)
        run_command(["make", "validate"], cwd=extracted_root)

        comparisons: dict[str, Any] = {}
        equal = True
        for relative, expected_hash in expected.items():
            rebuilt = extracted_root / relative
            actual_hash = sha256_file(rebuilt) if rebuilt.is_file() else None
            same = actual_hash == expected_hash
            equal &= same
            comparisons[relative] = {
                "expected_sha256": expected_hash,
                "replayed_sha256": actual_hash,
                "equal": same,
            }
        if not equal:
            failed = [relative for relative, item in comparisons.items() if not item["equal"]]
            raise RuntimeError("archive clean replay mismatch: " + ", ".join(failed))

    return {
        "status": "pass",
        "zip_crc_and_path_safety": True,
        "internal_manifest_and_checksums": True,
        "command": "make clean-generated && make validate",
        "compared_boundaries": len(comparisons),
        "all_boundaries_equal": True,
        "boundaries": comparisons,
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

    release = {
        "schema": "TOM-WORLD-QUERY-RELEASE-MANIFEST-0.1",
        "release": "TOM World & Query Kernel 0.1.0",
        "generated": GENERATED,
        "status": "pass",
        "package": {
            "path": ZIP_PATH.name,
            "bytes": ZIP_PATH.stat().st_size,
            "sha256": sha256_file(ZIP_PATH),
            "root": PACKAGE_NAME,
        },
        "validation": prerequisites,
        "archive_replay": replay,
        "implemented_start": [
            "persistent content-addressed local world store",
            "definition_at and verify_definition",
            "exact discrete state_at and trace",
            "support- and compatibility-gated next_event",
            "events_in_support and compatible(q1,q2)",
            "event transition, lineage commit, and reconstruction",
            "bounded branch-selected grammar",
            "literal TOMAGI EMIT documentation artifact",
        ],
        "next_target": (
            "World & Query Kernel 0.2: immutable secondary indexes, deterministic query plans, "
            "checkpoints, corruption audit, and a published 10,000-record benchmark."
        ),
        "not_claimed": [
            "continuous or interval-certified root solving",
            "autonomous definition learning",
            "general planning or tool execution",
            "grounded multimodal perception",
            "large-world scalability",
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
    print("[1/7] verifying release prerequisites", flush=True)
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
