from __future__ import annotations

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
OUT = ROOT.parent
PACKAGE_NAME = ROOT.name
ZIP_PATH = OUT / f"{PACKAGE_NAME}.zip"
FIXED_TIME = (2026, 9, 1, 0, 0, 0)

MANIFEST = ROOT / "validation/world03/package_manifest.json"
CHECKSUMS = ROOT / "checksums/SHA256SUMS.txt"
RELEASE_MANIFEST = OUT / "TOM_World_Query_Kernel_0_3_0_release_manifest.json"
RELEASE_CHECKSUMS = OUT / "TOM_World_Query_Kernel_0_3_0_SHA256SUMS.txt"

EXCLUDE_PARTS = {".git", ".pytest_cache", "__pycache__", "build", "dist"}
GENERATED_BOUNDARIES = (
    "examples/world03/affine_reference.tmg",
    "validation/world03/affine_reference.python.trace.json",
    "validation/world03/affine_reference.c.trace.json",
    "validation/world03/certified_crossing_x5.json",
    "validation/world03/events_0_10.json",
    "validation/world03/next_event_set.json",
    "validation/world03/simultaneous_transition.json",
    "validation/world03/trusted_baseline_comparison.json",
    "validation/world03/tomagi_trajectory_baseline.json",
    "validation/world03/simultaneous_conflict_rejection.json",
    "validation/world03/fixture_report.json",
    "examples/world03/world03_release_artifact.tmg",
    "examples/world03/world03_release_artifact.tmg.compile.json",
    "validation/world03/TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.materialized.md",
    "validation/world03/world03_release_artifact.python.trace.json",
    "validation/world03/world03_release_artifact.c.trace.json",
    "validation/world03/world03_release_artifact.emit_records.json",
    "validation/world03/world03_release_artifact.proof.json",
    "validation/world03/rejection_capsule.json",
    "validation/world03/clean_rebuild.json",
    "validation/world03/validation_report.json",
    "validation/world03/VALIDATION.md",
)

COMPANIONS = {
    "TOM_WORLD_QUERY_KERNEL_0_3.md": "spec/TOM_WORLD_QUERY_KERNEL_0_3.md",
    "TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.md": "TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.md",
    "TOM_AGI_ROADMAP_AND_STARTER_0_3.md": "TOM_AGI_ROADMAP_AND_STARTER_0_3.md",
    "TOM_World_Query_Kernel_0_3_validation_report.json": "validation/world03/validation_report.json",
    "TOM_World_Query_Kernel_0_3_clean_rebuild.json": "validation/world03/clean_rebuild.json",
    "TOM_World_Query_Kernel_0_3_certified_crossing.json": "validation/world03/certified_crossing_x5.json",
    "TOM_World_Query_Kernel_0_3_next_event_set.json": "validation/world03/next_event_set.json",
    "TOM_World_Query_Kernel_0_3_simultaneous_transition.json": "validation/world03/simultaneous_transition.json",
    "TOM_World_Query_Kernel_0_3_baseline_comparison.json": "validation/world03/trusted_baseline_comparison.json",
    "TOM_World_Query_Kernel_0_3_tomagi_baseline.json": "validation/world03/tomagi_trajectory_baseline.json",
    "TOM_World_Query_Kernel_0_3_release_artifact_proof.json": "validation/world03/world03_release_artifact.proof.json",
    "TOM_World_Query_Kernel_0_3_interval_world.json": "examples/world03/interval_event_world.json",
    "TOM_World_Query_Kernel_0_3_affine_reference.tmg": "examples/world03/affine_reference.tmg",
    "TOM_seed_genome_2026-09-01.txt": "TOM_seed_genome_2026-09-01.txt",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    for path in (
        ROOT / "validation/world03/build_fixture.status",
        ROOT / "validation/world03/tests.status",
        ROOT / "validation/world03/full_tests.status",
        ROOT / "validation/world03/run_validation.status",
        ROOT / "validation/world03/release_artifact.refresh.stdout.json",
    ):
        path.unlink(missing_ok=True)
    MANIFEST.unlink(missing_ok=True)
    CHECKSUMS.unlink(missing_ok=True)


def files(*, exclude_inventory: bool = False) -> list[Path]:
    excluded = {MANIFEST, CHECKSUMS} if exclude_inventory else set()
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path in excluded:
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(ROOT).as_posix())


def write_inventory() -> dict[str, Any]:
    listed = files(exclude_inventory=True)
    validation = json.loads((ROOT / "validation/world03/validation_report.json").read_text())
    record = {
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-PACKAGE-MANIFEST",
        "package": PACKAGE_NAME,
        "release": "0.3.0",
        "generated": "2026-09-01T00:00:00Z",
        "status": validation["status"],
        "canonical_seed_sha256": validation["canonical_seed_sha256"],
        "validation_content_hash": validation["content_hash"],
        "file_count_excluding_inventory": len(listed),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in listed
        ],
    }
    canonical_write(MANIFEST, record)
    checksum_files = [path for path in files() if path != CHECKSUMS]
    CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUMS.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in checksum_files),
        encoding="utf-8",
    )
    return record


def make_zip() -> list[str]:
    ZIP_PATH.unlink(missing_ok=True)
    names: list[str] = []
    with zipfile.ZipFile(ZIP_PATH, "w") as archive:
        for path in files():
            rel = path.relative_to(ROOT).as_posix()
            name = f"{PACKAGE_NAME}/{rel}"
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            names.append(name)
    return names


def validate_name(name: str) -> None:
    value = PurePosixPath(name)
    if value.is_absolute() or not value.parts or value.parts[0] != PACKAGE_NAME:
        raise RuntimeError(f"unsafe archive path {name}")
    if any(part in {"", ".", ".."} for part in value.parts):
        raise RuntimeError(f"unsafe archive path {name}")


def verify_zip(expected: list[str]) -> None:
    with zipfile.ZipFile(ZIP_PATH) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != expected or names != sorted(names) or len(names) != len(set(names)):
            raise RuntimeError("archive member order/identity mismatch")
        for info in infos:
            validate_name(info.filename)
            if info.date_time != FIXED_TIME:
                raise RuntimeError("nonfixed archive timestamp")
            if ((info.external_attr >> 16) & 0xFFFF) != 0o100644:
                raise RuntimeError("nonfixed archive mode")
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"archive CRC failed at {bad}")


def verify_internal(root: Path) -> None:
    manifest = json.loads((root / "validation/world03/package_manifest.json").read_text())
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"package manifest mismatch: {item['path']}")
    checksum = root / "checksums/SHA256SUMS.txt"
    seen: set[str] = set()
    for line in checksum.read_text().splitlines():
        digest, rel = line.split("  ", 1)
        path = root / rel
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"checksum mismatch: {rel}")
        seen.add(rel)
    expected = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != checksum
        and not any(part in EXCLUDE_PARTS for part in path.relative_to(root).parts)
    }
    if seen != expected:
        raise RuntimeError("checksum inventory set mismatch")


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / "src/python")
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(
            f"clean replay command failed: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}"
        )


def clean_replay() -> dict[str, Any]:
    expected_hashes = {rel: sha256(ROOT / rel) for rel in GENERATED_BOUNDARIES}
    with tempfile.TemporaryDirectory(prefix="tom-world03-archive-") as td:
        base = Path(td)
        with zipfile.ZipFile(ZIP_PATH) as archive:
            for info in archive.infolist():
                validate_name(info.filename)
            archive.extractall(base)
        extracted = base / PACKAGE_NAME
        verify_internal(extracted)

        shutil.rmtree(extracted / "build", ignore_errors=True)
        (extracted / "examples/world03/affine_reference.tmg").unlink(missing_ok=True)
        for name in ("world03_release_artifact.tmg", "world03_release_artifact.tmg.compile.json"):
            (extracted / "examples/world03" / name).unlink(missing_ok=True)
        shutil.rmtree(extracted / "validation/world03", ignore_errors=True)
        (extracted / "validation/world03").mkdir(parents=True, exist_ok=True)

        run([sys.executable, "tools/run_world03_validation.py"], extracted)
        actual: dict[str, Any] = {}
        all_equal = True
        for rel, expected in expected_hashes.items():
            path = extracted / rel
            digest = sha256(path) if path.is_file() else None
            equal = digest == expected
            all_equal &= equal
            actual[rel] = {"packaged_sha256": expected, "replayed_sha256": digest, "equal": equal}
        if not all_equal:
            raise RuntimeError("clean archive replay boundary mismatch")
        return {
            "zip_crc_and_path_safety": True,
            "internal_manifest_and_checksums": True,
            "validation_rerun": "pass",
            "compared_boundaries": len(actual),
            "all_equal": True,
            "boundaries": actual,
        }


def publish(record: dict[str, Any]) -> dict[str, Any]:
    for name in list(COMPANIONS) + [RELEASE_MANIFEST.name, RELEASE_CHECKSUMS.name]:
        (OUT / name).unlink(missing_ok=True)
    companions: list[dict[str, Any]] = []
    for name, rel in sorted(COMPANIONS.items()):
        source = ROOT / rel
        destination = OUT / name
        destination.write_bytes(source.read_bytes())
        companions.append({
            "path": name,
            "source_in_zip": rel,
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        })
    validation = json.loads((ROOT / "validation/world03/validation_report.json").read_text())
    release = {
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-RELEASE-MANIFEST",
        "release": "0.3.0",
        "generated": "2026-09-01T00:00:00Z",
        "status": "pass",
        "package": {"path": ZIP_PATH.name, "bytes": ZIP_PATH.stat().st_size, "sha256": sha256(ZIP_PATH)},
        "validation": {
            "tests": validation["tests"],
            "checks_passed": validation["checks_passed"],
            "checks_failed": validation["checks_failed"],
            "content_hash": validation["content_hash"],
        },
        "archive_replay": record,
        "accompanying_files": companions,
        "evidence_boundary": validation["evidence_boundary"],
    }
    canonical_write(RELEASE_MANIFEST, release)
    targets = [ZIP_PATH, RELEASE_MANIFEST, *[OUT / name for name in COMPANIONS]]
    RELEASE_CHECKSUMS.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in sorted(targets, key=lambda p: p.name)),
        encoding="utf-8",
    )
    return release


def main() -> None:
    validation = json.loads((ROOT / "validation/world03/validation_report.json").read_text())
    if validation.get("status") != "pass" or validation.get("checks_failed") != 0:
        raise RuntimeError("0.3 validation must pass before packaging")
    clean_transients()
    package_manifest = write_inventory()
    names = make_zip()
    verify_zip(names)
    replay = clean_replay()
    release = publish(replay)
    print(json.dumps({
        "status": "pass",
        "zip": release["package"],
        "zip_entries": len(names),
        "internal_files_excluding_inventory": package_manifest["file_count_excluding_inventory"],
        "clean_replay_boundaries": replay["compared_boundaries"],
        "accompanying_files": len(release["accompanying_files"]),
        "release_manifest": RELEASE_MANIFEST.name,
        "release_checksums": RELEASE_CHECKSUMS.name,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
