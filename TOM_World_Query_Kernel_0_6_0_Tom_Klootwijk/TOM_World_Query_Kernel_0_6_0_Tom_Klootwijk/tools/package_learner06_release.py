from __future__ import annotations

"""Build, verify, replay, and publish the deterministic WQK 0.6 release ZIP."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parents[1]
PACKAGE_NAME = "TOM_World_Query_Kernel_0_6_0_Tom_Klootwijk"
ZIP = OUT / f"{PACKAGE_NAME}.zip"
ALIAS = OUT / "TOM_WQK_0_6_FIXED.zip"
FIXED_TIME = (2026, 9, 2, 0, 0, 0)
MANIFEST_REL = Path("checksums/PACKAGE_MANIFEST.json")
CHECKSUMS_REL = Path("checksums/SHA256SUMS.txt")

from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from verify_learner06_clean_rebuild import GENERATED_BOUNDARIES, SOURCE_BOUNDARIES, tree_record

EXTERNAL_FILES = {
    "TOM_LEARNER_0_2_WORLD_QUERY_KERNEL_0_6.md": "spec/TOM_LEARNER_0_2_WORLD_QUERY_KERNEL_0_6.md",
    "TOM_WORLD_QUERY_KERNEL_0_6_RELEASE.md": "TOM_WORLD_QUERY_KERNEL_0_6_RELEASE.md",
    "TOM_AGI_ROADMAP_AND_STARTER_0_6.md": "TOM_AGI_ROADMAP_AND_STARTER_0_6.md",
    "CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md": "docs/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md",
    "CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json": "sources/codex_0_5_2_repair/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json",
    "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.md": "validation/learner06/CODEX_KERNEL_0_6_VALIDATION_HANDOFF.materialized.md",
    "CODEX_KERNEL_0_6_VALIDATION_HANDOFF_PROOF.json": "validation/learner06/kernel06_validation_handoff.proof.json",
    "TOM_CONTINUATION_HANDOFF_0_6.json": "TOM_CONTINUATION_HANDOFF_0_6.json",
    "TOM_Learner_0_2_family_registry.json": "examples/learner06/family_registry.json",
    "TOM_Learner_0_2_family_authority.formal.json": "examples/learner06/learner06_family_authority.formal.json",
    "TOM_Learner_0_2_family_authority.literal.json": "examples/learner06/learner06_family_authority.literal.json",
    "TOM_Learner_0_2_family_authority.tmg": "examples/learner06/learner06_family_authority.tmg",
    "TOM_Learner_0_2_family_authority_result.json": "examples/learner06/learner06_family_authority.result.json",
    "TOM_Learner_0_2_promotion_authority.formal.json": "examples/learner06/learner06_promotion_authority.formal.json",
    "TOM_Learner_0_2_promotion_authority.literal.json": "examples/learner06/learner06_promotion_authority.literal.json",
    "TOM_Learner_0_2_promotion_authority.tmg": "examples/learner06/learner06_promotion_authority.tmg",
    "TOM_Learner_0_2_promotion_authority_result.json": "validation/learner06/promotion_authority.materialized.json",
    "TOM_Learner_0_2_fixture_report.json": "validation/learner06/fixture_report.json",
    "TOM_Learner_0_2_oracle_comparison.json": "validation/learner06/oracle_comparison.json",
    "TOM_Learner_0_2_learner_authority_proof.json": "validation/learner06/learner_authority_proof.json",
    "TOM_Learner_0_2_promotion_authority_proof.json": "validation/learner06/promotion_authority_proof.json",
    "TOM_Learner_0_2_promotion_store_audit.json": "validation/learner06/promotion_store_audit.json",
    "TOM_Learner_0_2_promotion_store_reconstruction.json": "validation/learner06/promotion_store_reconstruction.json",
    "TOM_World_Query_Kernel_0_6_rejection_capsule.json": "validation/learner06/rejection_capsule.json",
    "TOM_World_Query_Kernel_0_6_validation_report.json": "validation/learner06/validation_report.json",
    "TOM_World_Query_Kernel_0_6_clean_rebuild.json": "validation/learner06/clean_rebuild.json",
    "TOM_World_Query_Kernel_0_6_release_artifact_proof.json": "validation/learner06/learner06_release_artifact.proof.json",
    "TOM_seed_genome_2026-09-01.txt": "TOM_seed_genome_2026-09-01.txt",
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_prefixed(path: Path) -> str:
    return "sha256:" + sha_bytes(path.read_bytes())


def safe_rel(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError(f"unsafe archive path: {value!r}")
    if path.parts[0] != PACKAGE_NAME:
        raise RuntimeError(f"archive member outside package root: {value!r}")


def reject_links(root: Path) -> None:
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise RuntimeError(f"symbolic link is not permitted in release: {path.relative_to(root)}")
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise RuntimeError(f"non-regular filesystem object is not permitted: {path.relative_to(root)}")


def clean_transients() -> None:
    shutil.rmtree(ROOT / "build", ignore_errors=True)
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)
    for directory in sorted(ROOT.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for path in ROOT.rglob("*.pyc"):
        path.unlink(missing_ok=True)
    for path in ROOT.rglob("*.pyo"):
        path.unlink(missing_ok=True)
    for path in ROOT.rglob(".publication.lock"):
        path.unlink(missing_ok=True)
    (ROOT / MANIFEST_REL).unlink(missing_ok=True)
    (ROOT / CHECKSUMS_REL).unlink(missing_ok=True)


def package_files(*, exclude_inventory: bool = False) -> list[Path]:
    excluded = {ROOT / MANIFEST_REL, ROOT / CHECKSUMS_REL} if exclude_inventory else set()
    out = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path in excluded:
            continue
        rel = path.relative_to(ROOT)
        if any(part in {"build", "dist", ".pytest_cache", "__pycache__", ".git"} for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"} or path.name == ".publication.lock":
            continue
        out.append(path)
    return sorted(out, key=lambda path: path.relative_to(ROOT).as_posix())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def make_continuation_handoff() -> dict[str, Any]:
    validation = json.loads((ROOT / "validation/learner06/validation_report.json").read_text())
    clean = json.loads((ROOT / "validation/learner06/clean_rebuild.json").read_text())
    fixture = json.loads((ROOT / "validation/learner06/fixture_report.json").read_text())
    learner = json.loads((ROOT / "validation/learner06/learner_authority_proof.json").read_text())
    promotion = json.loads((ROOT / "validation/learner06/promotion_authority_proof.json").read_text())
    validation_handoff = json.loads(
        (ROOT / "validation/learner06/kernel06_validation_handoff.proof.json").read_text()
    )
    handoff = attach_hash({
        "schema": "TOM-CONTINUATION-HANDOFF-0.6",
        "release": "0.6.0",
        "date": "2026-09-03",
        "status": "pass",
        "canonical_seed": {"bytes": 244, "sha256": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5", "terminal_newline": False},
        "repair_basis": {
            "handoff": "docs/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md",
            "proof_hash": "sha256:88f1b383fbedfdc15e22001940d65cbc0b518ce3a9f8d9aa27447a9f44f44f3d",
            "repairs_preserved": [
                "defined C wrap32 arithmetic",
                "all-six reserved-header rejection",
                "same-host thread/process publication lock",
                "intermediate formal-result limits",
                "two-build reproducible packaging",
                "audit-store SOURCE STORE CLI order",
            ],
        },
        "completed_boundary": {
            "family_registry_hash": fixture["family_registry_hash"],
            "families": fixture["family_count"],
            "candidates": fixture["candidate_count"],
            "datasets": fixture["dataset_count"],
            "accepted": fixture["accepted_count"],
            "rejected": fixture["rejected_count"],
            "ambiguities": fixture["ambiguity_count"],
            "false_promotions": fixture["false_promotions"],
            "learner_proof_hash": learner["content_hash"],
            "promotion_proof_hash": promotion["content_hash"],
            "publication_plan_hash": promotion["publication_plan_hash"],
            "initial_head": promotion["initial_head"],
            "terminal_head": promotion["terminal_head"],
            "promotion_store_tree": promotion["store_tree"],
        },
        "validation": {
            "validation_hash": validation["content_hash"],
            "status": validation["status"],
            "tests": validation["test_count"],
            "checks_passed": validation["checks_passed"],
            "checks_failed": validation["checks_failed"],
            "clean_rebuild_hash": clean["content_hash"],
            "two_builds_equal": clean["two_builds_equal"],
            "compared_boundaries": clean["compared_boundaries"],
            "store_trees_equal": clean["store_trees_equal"],
        },
        "validation_handoff": {
            "artifact": "validation/learner06/CODEX_KERNEL_0_6_VALIDATION_HANDOFF.materialized.md",
            "artifact_sha256": validation_handoff["artifact"]["sha256"],
            "proof_hash": validation_handoff["content_hash"],
            "literal_source": validation_handoff["literal_source"]["path"],
            "program": validation_handoff["program"]["path"],
        },
        "next_permitted_milestone": {
            "name": "TOM Learner 0.3 / WQK 0.7",
            "scope": "typed interval observations, finite noise families, explicit calibration/coverage and distribution-shift records, ambiguity-preserving robust scoring, and unchanged parent-bound promotion",
            "mandatory_rule": "confidence remains content-addressed evidence and may not silently alter TOMAGI opcode semantics or bypass support, compatibility, guard, decision, and promotion authority",
        },
        "claim_boundary": "finite exact four-family hypothesis search and promotion; not noisy learning, open-domain induction, cognition or AGI",
    })
    write_json(ROOT / "TOM_CONTINUATION_HANDOFF_0_6.json", handoff)
    return handoff


def write_internal_inventory() -> tuple[dict[str, Any], int]:
    files = package_files(exclude_inventory=True)
    manifest = attach_hash({
        "schema": "TOM-WQK-0.6-PACKAGE-MANIFEST-1.0",
        "release": "0.6.0",
        "package": PACKAGE_NAME,
        "canonical_seed_sha256": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
        "file_count_excluding_manifest_and_checksum": len(files),
        "files": [
            {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha_prefixed(path)}
            for path in files
        ],
    })
    write_json(ROOT / MANIFEST_REL, manifest)
    checksum_files = [path for path in package_files() if path != ROOT / CHECKSUMS_REL]
    (ROOT / CHECKSUMS_REL).write_text(
        "".join(f"{sha_bytes(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n" for path in checksum_files),
        encoding="utf-8",
    )
    return manifest, len(checksum_files)


def write_zip(path: Path) -> list[str]:
    path.unlink(missing_ok=True)
    names = []
    with zipfile.ZipFile(path, "w") as archive:
        for source in package_files():
            rel = source.relative_to(ROOT).as_posix()
            name = f"{PACKAGE_NAME}/{rel}"
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            names.append(name)
    return names


def verify_zip(path: Path, expected: list[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != expected or names != sorted(names) or len(names) != len(set(names)):
            raise RuntimeError("ZIP member order or uniqueness failure")
        for info in infos:
            safe_rel(info.filename)
            if info.date_time != FIXED_TIME:
                raise RuntimeError(f"non-fixed ZIP timestamp: {info.filename}")
            if ((info.external_attr >> 16) & 0xFFFF) != 0o100644:
                raise RuntimeError(f"non-fixed ZIP mode: {info.filename}")
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC failure: {bad}")


def verify_internal(extracted: Path) -> tuple[int, int]:
    manifest = json.loads((extracted / MANIFEST_REL).read_text())
    if not verify_hash(manifest):
        raise RuntimeError("internal package manifest content hash mismatch")
    seen = set()
    for item in manifest["files"]:
        rel = item["path"]
        path = extracted / rel
        if rel in seen or not path.is_file() or path.stat().st_size != item["bytes"] or sha_prefixed(path) != item["sha256"]:
            raise RuntimeError(f"internal package manifest mismatch: {rel}")
        seen.add(rel)
    expected_manifest = {path.relative_to(extracted).as_posix() for path in extracted.rglob("*") if path.is_file() and path not in {extracted / MANIFEST_REL, extracted / CHECKSUMS_REL}}
    if seen != expected_manifest:
        raise RuntimeError("internal package manifest inventory differs from extracted files")

    checksum_seen = set()
    for line in (extracted / CHECKSUMS_REL).read_text().splitlines():
        digest, rel = line.split("  ", 1)
        path = extracted / rel
        if rel in checksum_seen or not path.is_file() or sha_bytes(path.read_bytes()) != digest:
            raise RuntimeError(f"internal checksum mismatch: {rel}")
        checksum_seen.add(rel)
    expected_checksums = {path.relative_to(extracted).as_posix() for path in extracted.rglob("*") if path.is_file() and path != extracted / CHECKSUMS_REL}
    if checksum_seen != expected_checksums:
        raise RuntimeError("internal checksum inventory differs from extracted files")
    return len(seen), len(checksum_seen)


def remove_replay_outputs(root: Path) -> None:
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


def run_replay(root: Path) -> None:
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
            raise RuntimeError(f"final archive replay failed: {' '.join(command)}\n{proc.stdout[-12000:]}")


def archive_replay() -> dict[str, Any]:
    expected = {rel: sha_prefixed(ROOT / rel) for rel in GENERATED_BOUNDARIES}
    expected_store = tree_record(ROOT / "examples/learner06/promotion_store")
    with tempfile.TemporaryDirectory(prefix="tom-wqk-060-archive-") as td:
        destination = Path(td)
        with zipfile.ZipFile(ZIP) as archive:
            for info in archive.infolist():
                safe_rel(info.filename)
            archive.extractall(destination)
        extracted = destination / PACKAGE_NAME
        manifest_count, checksum_count = verify_internal(extracted)
        remove_replay_outputs(extracted)
        run_replay(extracted)
        comparisons = {}
        all_equal = True
        for rel, expected_hash in expected.items():
            path = extracted / rel
            actual = sha_prefixed(path) if path.is_file() else None
            equal = actual == expected_hash
            all_equal &= equal
            comparisons[rel] = {"expected_sha256": expected_hash, "replayed_sha256": actual, "equal": equal}
        replay_store = tree_record(extracted / "examples/learner06/promotion_store")
        store_equal = replay_store == expected_store
        if not all_equal or not store_equal:
            failures = [rel for rel, item in comparisons.items() if not item["equal"]]
            raise RuntimeError(f"final ZIP replay mismatch: {failures}; store_equal={store_equal}")
        return {
            "status": "pass",
            "zip_crc_and_path_safety": True,
            "internal_manifest_files": manifest_count,
            "internal_checksum_entries": checksum_count,
            "compared_file_boundaries": len(comparisons),
            "all_file_boundaries_equal": True,
            "promotion_store_tree_equal": True,
            "promotion_store_tree": expected_store,
            "files": comparisons,
        }


def prerequisites() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validation = json.loads((ROOT / "validation/learner06/validation_report.json").read_text())
    clean = json.loads((ROOT / "validation/learner06/clean_rebuild.json").read_text())
    release_proof = json.loads((ROOT / "validation/learner06/learner06_release_artifact.proof.json").read_text())
    handoff_proof = json.loads((ROOT / "validation/learner06/kernel06_validation_handoff.proof.json").read_text())
    if not (
        verify_hash(validation) and validation.get("status") == "pass"
        and validation.get("test_count") == 283
        and validation.get("checks_passed") == 19
        and validation.get("checks_failed") == 0
        and verify_hash(clean) and clean.get("status") == "pass" and clean.get("two_builds_equal") and clean.get("all_boundaries_equal") and clean.get("store_trees_equal")
        and validation.get("clean_rebuild_hash") == clean.get("content_hash")
        and verify_hash(release_proof) and release_proof.get("status") == "pass" and release_proof["execution"]["python_c_full_trace_equal"]
        and verify_hash(handoff_proof) and handoff_proof.get("status") == "pass" and handoff_proof["execution"]["python_c_full_trace_equal"] and handoff_proof["execution"]["python_c_emit_sequence_equal"]
    ):
        raise RuntimeError("WQK 0.6 release prerequisites are not passing")
    return validation, clean, release_proof


def publish_external(replay: dict[str, Any], manifest: dict[str, Any], checksum_count: int, zip_reproducible: bool) -> dict[str, Any]:
    ALIAS.write_bytes(ZIP.read_bytes())
    companions = []
    for name, rel in sorted(EXTERNAL_FILES.items()):
        source = ROOT / rel
        destination = OUT / name
        destination.write_bytes(source.read_bytes())
        companions.append({"path": name, "source_in_package": rel, "bytes": destination.stat().st_size, "sha256": sha_prefixed(destination)})

    clean = json.loads((ROOT / "validation/learner06/clean_rebuild.json").read_text())
    fixture = json.loads((ROOT / "validation/learner06/fixture_report.json").read_text())
    validation = json.loads((ROOT / "validation/learner06/validation_report.json").read_text())
    release = attach_hash({
        "schema": "TOM-WQK-0.6-EXTERNAL-RELEASE-MANIFEST-1.0",
        "release": "0.6.0",
        "date": "2026-09-03",
        "status": "pass",
        "package": {
            "path": ZIP.name,
            "alias": ALIAS.name,
            "bytes": ZIP.stat().st_size,
            "sha256": sha_prefixed(ZIP),
            "byte_identical_alias": ZIP.read_bytes() == ALIAS.read_bytes(),
            "entries": len(package_files()),
        },
        "repair_basis": {
            "handoff": "CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md",
            "proof_hash": "sha256:88f1b383fbedfdc15e22001940d65cbc0b518ce3a9f8d9aa27447a9f44f44f3d",
            "preserved": True,
        },
        "canonical_boundaries": {
            "seed": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
            "family_registry": fixture["family_registry_hash"],
            "learner_proof": json.loads((ROOT / "validation/learner06/learner_authority_proof.json").read_text())["content_hash"],
            "promotion_proof": json.loads((ROOT / "validation/learner06/promotion_authority_proof.json").read_text())["content_hash"],
            "terminal_head": fixture["terminal_head"],
            "promotion_store_tree": fixture["store_tree"]["sha256"],
            "validation": validation["content_hash"],
            "validation_handoff": json.loads(
                (ROOT / "validation/learner06/kernel06_validation_handoff.proof.json").read_text()
            )["content_hash"],
        },
        "two_clean_builds": {
            "status": clean["status"],
            "content_hash": clean["content_hash"],
            "two_builds_equal": clean["two_builds_equal"],
            "compared_boundaries": clean["compared_boundaries"],
            "store_trees_equal": clean["store_trees_equal"],
        },
        "archive_replay": {
            **replay,
            "clean_build_count": 2,
            "package_byte_reproducible": zip_reproducible,
        },
        "internal_manifest_hash": manifest["content_hash"],
        "internal_checksum_entries": checksum_count,
        "accompanying_files": companions,
        "claim_boundary": "finite exact four-family learner with explicit ambiguity, supersession/regression impact and repaired parent-bound promotion; not noisy learning or AGI",
    })
    release_path = OUT / "TOM_World_Query_Kernel_0_6_0_release_manifest.json"
    write_json(release_path, release)

    audit = attach_hash({
        "schema": "TOM-WQK-0.6-EXTERNAL-ARCHIVE-AUDIT-1.0",
        "status": "pass",
        "zip": {"path": ZIP.name, "bytes": ZIP.stat().st_size, "sha256": sha_prefixed(ZIP)},
        "package_byte_reproducible": zip_reproducible,
        "archive_replay": replay,
        "internal_manifest_hash": manifest["content_hash"],
        "internal_checksum_entries": checksum_count,
    })
    audit_path = OUT / "TOM_World_Query_Kernel_0_6_EXTERNAL_ARCHIVE_AUDIT.json"
    write_json(audit_path, audit)

    summary = f"""# TOM World & Query Kernel 0.6.0 — Delivery summary

Status: **pass**

```text
ZIP:       {ZIP.name}
Alias:     {ALIAS.name}
Bytes:     {ZIP.stat().st_size}
Entries:   {len(package_files())}
SHA-256:   {sha_bytes(ZIP.read_bytes())}
Tests:     {validation['test_count']} passed
Checks:    {validation['checks_passed']} passed, {validation['checks_failed']} failed
Clean:     {clean['compared_boundaries']} source/generated boundaries plus store tree equal across two builds
ZIP replay:{replay['compared_file_boundaries']} generated boundaries plus store tree equal
```

WQK 0.6 preserves the CODEX 0.5.2 kernel repair and adds a finite four-family formal learner with deterministic ambiguity, explicit supersession, regression-impact certificates, and parent-bound promotion.
"""
    summary_path = OUT / "TOM_World_Query_Kernel_0_6_0_DELIVERY_SUMMARY.md"
    summary_path.write_text(summary, encoding="utf-8")

    targets = [ZIP, ALIAS, release_path, audit_path, summary_path] + [OUT / name for name in EXTERNAL_FILES]
    sums_path = OUT / "TOM_World_Query_Kernel_0_6_0_SHA256SUMS.txt"
    sums_path.write_text("".join(f"{sha_bytes(path.read_bytes())}  {path.name}\n" for path in sorted(set(targets), key=lambda p: p.name)), encoding="utf-8")
    return release


def main() -> int:
    prerequisites()
    make_continuation_handoff()
    clean_transients()
    reject_links(ROOT)
    manifest, checksum_count = write_internal_inventory()

    with tempfile.TemporaryDirectory(prefix="tom-wqk-060-zip-") as td:
        first = Path(td) / "first.zip"
        second = Path(td) / "second.zip"
        first_names = write_zip(first)
        second_names = write_zip(second)
        if first_names != second_names or first.read_bytes() != second.read_bytes():
            raise RuntimeError("deterministic ZIP byte comparison failed")
        ZIP.write_bytes(first.read_bytes())
    verify_zip(ZIP, first_names)
    replay = archive_replay()
    release = publish_external(replay, manifest, checksum_count, True)
    print(json.dumps({
        "status": "pass",
        "zip": ZIP.name,
        "alias": ALIAS.name,
        "bytes": ZIP.stat().st_size,
        "entries": len(first_names),
        "sha256": sha_prefixed(ZIP),
        "internal_manifest_files": manifest["file_count_excluding_manifest_and_checksum"],
        "internal_checksum_entries": checksum_count,
        "two_clean_builds_equal": True,
        "package_byte_reproducible": True,
        "archive_replay_boundaries": replay["compared_file_boundaries"],
        "archive_store_tree_equal": replay["promotion_store_tree_equal"],
        "release_manifest_hash": release["content_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
