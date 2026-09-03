from __future__ import annotations

"""Create and independently replay-verify the WQK 0.5.2 release ZIP."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT.parents[1]
PACKAGE_NAME = ROOT.name
ZIP = OUT / f"{PACKAGE_NAME}.zip"
ALIAS = OUT / "TOM_WQK_0_5_2_FIXED.zip"
MANIFEST_REL = "checksums/PACKAGE_MANIFEST.json"
CHECKSUMS_REL = "checksums/SHA256SUMS.txt"
FIXED_TIME = (2026, 9, 2, 0, 0, 0)

from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tools.verify_learner052_clean_rebuild import FILE_BOUNDARIES, tree_record

EXTERNAL = {
    "TOM_WORLD_QUERY_KERNEL_0_5_2_TRANSACTION_AUTHORITY.md": "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_2_TRANSACTION_AUTHORITY.md",
    "TOM_WORLD_QUERY_KERNEL_0_5_2_RELEASE.md": "TOM_WORLD_QUERY_KERNEL_0_5_2_RELEASE.md",
    "TOM_AGI_ROADMAP_AND_STARTER_0_5_2.md": "TOM_AGI_ROADMAP_AND_STARTER_0_5_2.md",
    "TOM_CONTINUATION_HANDOFF_0_5_2.json": "sources/TOM_CONTINUATION_HANDOFF_0_5_2.json",
    "TOM_Learner_0_1_promotion_authority.formal.json": "examples/learner052/promotion_authority.formal.json",
    "TOM_Learner_0_1_promotion_authority.literal.json": "examples/learner052/promotion_authority.literal.json",
    "TOM_Learner_0_1_promotion_authority_result.json": "validation/learner052/promotion_authority.materialized.json",
    "TOM_Learner_0_1_promotion_authority_proof.json": "validation/learner052/promotion_authority.proof.json",
    "TOM_Learner_0_1_promotion_store_audit.json": "validation/learner052/promotion_store_audit.json",
    "TOM_Learner_0_1_promotion_store_reconstruction.json": "validation/learner052/promotion_store_reconstruction.json",
    "TOM_World_Query_Kernel_0_5_2_validation_report.json": "validation/learner052/validation_report.json",
    "TOM_World_Query_Kernel_0_5_2_clean_rebuild.json": "validation/learner052/clean_rebuild.json",
    "TOM_World_Query_Kernel_0_5_2_rejection_capsule.json": "validation/learner052/rejection_capsule.json",
    "TOM_World_Query_Kernel_0_5_2_release_artifact_proof.json": "validation/learner052/learner052_release_artifact.proof.json",
    "TOM_seed_genome_2026-09-01.txt": "TOM_seed_genome_2026-09-01.txt",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_prefixed(path: Path) -> str:
    return "sha256:" + sha(path)


def clean_transients(root: Path) -> None:
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "dist", ignore_errors=True)
    shutil.rmtree(root / ".pytest_cache", ignore_errors=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for path in root.rglob("*.pyc"):
        path.unlink(missing_ok=True)
    for path in root.rglob("*.pyo"):
        path.unlink(missing_ok=True)
    (root / MANIFEST_REL).unlink(missing_ok=True)
    (root / CHECKSUMS_REL).unlink(missing_ok=True)


def files(root: Path, *, exclude_inventory: bool = False) -> list[Path]:
    excluded = {root / MANIFEST_REL, root / CHECKSUMS_REL} if exclude_inventory else set()
    result = []
    for path in root.rglob("*"):
        if not path.is_file() or path in excluded:
            continue
        rel = path.relative_to(root)
        if any(part in {".git", ".pytest_cache", "__pycache__", "build", "dist"} for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        result.append(path)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())


def write_internal_inventory() -> tuple[dict[str, Any], int]:
    listed = files(ROOT, exclude_inventory=True)
    validation = json.loads((ROOT / "validation/learner052/validation_report.json").read_text(encoding="utf-8"))
    clean = json.loads((ROOT / "validation/learner052/clean_rebuild.json").read_text(encoding="utf-8"))
    handoff = json.loads((ROOT / "sources/TOM_CONTINUATION_HANDOFF_0_5_2.json").read_text(encoding="utf-8"))
    record = attach_hash({
        "schema": "TOM-WQK-0.5.2-PACKAGE-MANIFEST-1.0",
        "package": PACKAGE_NAME,
        "release": "0.5.2",
        "status": "pass",
        "canonical_seed_sha256": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
        "corrective_base_archive_sha256": "sha256:0f3bf159536b726fc68fc3e0ff7c1ff896c3bdf1e63a7449d5b507f67f043601",
        "continuation_handoff_hash": handoff["content_hash"],
        "validation_hash": validation["content_hash"],
        "clean_rebuild_hash": clean["content_hash"],
        "test_count": validation["test_count"],
        "file_count_excluding_manifest_and_checksum": len(listed),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha_prefixed(path),
            }
            for path in listed
        ],
    })
    manifest = ROOT / MANIFEST_REL
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(canonical_bytes(record) + b"\n")
    checksum_files = [path for path in files(ROOT) if path != ROOT / CHECKSUMS_REL]
    checksum_lines = [f"{sha(path)}  {path.relative_to(ROOT).as_posix()}" for path in checksum_files]
    (ROOT / CHECKSUMS_REL).write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return record, len(checksum_lines)


def write_zip(destination: Path) -> list[str]:
    destination.unlink(missing_ok=True)
    names: list[str] = []
    with zipfile.ZipFile(destination, "w") as archive:
        for path in files(ROOT):
            rel = path.relative_to(ROOT).as_posix()
            name = f"{PACKAGE_NAME}/{rel}"
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            names.append(name)
    return names


def safe_name(name: str) -> None:
    path = PurePosixPath(name)
    if (
        "\\" in name
        or path.is_absolute()
        or not path.parts
        or path.parts[0] != PACKAGE_NAME
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RuntimeError(f"unsafe ZIP member {name!r}")


def verify_zip(path: Path, expected: list[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != expected or names != sorted(names) or len(names) != len(set(names)):
            raise RuntimeError("ZIP entries are not the expected sorted unique sequence")
        for info in infos:
            safe_name(info.filename)
            if info.date_time != FIXED_TIME:
                raise RuntimeError("ZIP timestamp mismatch")
            if ((info.external_attr >> 16) & 0xFFFF) != 0o100644:
                raise RuntimeError("ZIP mode mismatch")
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")


def verify_internal(root: Path) -> tuple[int, int]:
    manifest = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))
    if not verify_hash(manifest) or manifest.get("status") != "pass" or manifest.get("package") != PACKAGE_NAME:
        raise RuntimeError("internal package manifest is invalid")
    seen: set[str] = set()
    for item in manifest["files"]:
        rel = item["path"]
        if rel in seen:
            raise RuntimeError(f"duplicate manifest path {rel}")
        seen.add(rel)
        path = root / rel
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha_prefixed(path) != item["sha256"]:
            raise RuntimeError(f"internal manifest mismatch {rel}")
    expected_manifest = {
        path.relative_to(root).as_posix()
        for path in files(root, exclude_inventory=True)
    }
    if seen != expected_manifest:
        raise RuntimeError("internal manifest inventory does not equal extracted files")

    checksum_path = root / CHECKSUMS_REL
    checksum_seen: set[str] = set()
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        path = root / rel
        if rel in checksum_seen or not path.is_file() or sha(path) != digest:
            raise RuntimeError(f"internal checksum mismatch {rel}")
        checksum_seen.add(rel)
    expected_checksums = {
        path.relative_to(root).as_posix()
        for path in files(root)
        if path != checksum_path
    }
    if checksum_seen != expected_checksums:
        raise RuntimeError("internal checksum inventory differs from extracted files")
    return len(seen), len(checksum_seen)


def remove_replay_outputs(root: Path) -> None:
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "examples/learner052/promotion_store", ignore_errors=True)
    shutil.rmtree(root / "validation/learner052", ignore_errors=True)
    for rel in (
        "examples/learner052/promotion_authority.tmg",
        "examples/learner052/promotion_authority.tmg.compile.json",
        "examples/learner052/learner052_release_artifact.tmg",
        "examples/learner052/learner052_release_artifact.tmg.compile.json",
    ):
        (root / rel).unlink(missing_ok=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)


def run(cmd: list[str], cwd: Path, timeout: int = 1200) -> None:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(cwd / "src/python")}
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f"archive replay failed: {' '.join(cmd)}\n{proc.stdout}")


def replay_archive() -> dict[str, Any]:
    expected = {rel: sha_prefixed(ROOT / rel) for rel in FILE_BOUNDARIES}
    expected_store = tree_record(ROOT / "examples/learner052/promotion_store")
    with tempfile.TemporaryDirectory(prefix="tom-wqk-052-archive-") as td:
        base = Path(td)
        with zipfile.ZipFile(ZIP) as archive:
            for info in archive.infolist():
                safe_name(info.filename)
            archive.extractall(base)
        extracted = base / PACKAGE_NAME
        manifest_count, checksum_count = verify_internal(extracted)
        remove_replay_outputs(extracted)
        run(["make", "validate-learner052-core"], extracted)
        comparisons: dict[str, Any] = {}
        all_equal = True
        for rel, expected_hash in expected.items():
            path = extracted / rel
            actual = sha_prefixed(path) if path.is_file() else None
            equal = actual == expected_hash
            all_equal &= equal
            comparisons[rel] = {"expected_sha256": expected_hash, "replayed_sha256": actual, "equal": equal}
        actual_store = tree_record(extracted / "examples/learner052/promotion_store")
        store_equal = actual_store == expected_store
        all_equal &= store_equal
        if not all_equal:
            failures = [rel for rel, item in comparisons.items() if not item["equal"]]
            raise RuntimeError(f"archive replay boundaries differ: {failures}; store_equal={store_equal}")
        return {
            "status": "pass",
            "zip_crc_and_paths": True,
            "internal_manifest_files": manifest_count,
            "internal_checksum_entries": checksum_count,
            "compared_file_boundaries": len(comparisons),
            "all_file_boundaries_equal": True,
            "store_tree_equal": True,
            "promotion_store": expected_store,
            "files": comparisons,
        }


def write_external(replay: dict[str, Any], internal_manifest: Mapping[str, Any], checksum_count: int) -> dict[str, Any]:
    alias_bytes = ZIP.read_bytes()
    ALIAS.write_bytes(alias_bytes)
    companions = []
    for destination_name, rel in sorted(EXTERNAL.items()):
        source = ROOT / rel
        destination = OUT / destination_name
        destination.write_bytes(source.read_bytes())
        companions.append({
            "path": destination.name,
            "source_in_package": rel,
            "bytes": destination.stat().st_size,
            "sha256": sha_prefixed(destination),
        })

    record = attach_hash({
        "schema": "TOM-WQK-0.5.2-EXTERNAL-RELEASE-MANIFEST-1.0",
        "release": "0.5.2",
        "status": "pass",
        "package": {
            "path": ZIP.name,
            "alias": ALIAS.name,
            "bytes": ZIP.stat().st_size,
            "sha256": sha_prefixed(ZIP),
            "byte_identical_alias": ZIP.read_bytes() == ALIAS.read_bytes(),
            "entries": len(files(ROOT)),
        },
        "corrective_base": {
            "archive": "TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_Tom_Klootwijk.zip",
            "bytes": 27022938,
            "sha256": "sha256:0f3bf159536b726fc68fc3e0ff7c1ff896c3bdf1e63a7449d5b507f67f043601",
            "used_as_base": True,
        },
        "canonical_boundaries": {
            "seed": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
            "promotion_formal_program": "sha256:f1030e332b5f7358c43603096a64ebca7f9268aaaf2fbbe16dbebc972daa8bdd",
            "publication_plan": "sha256:07b1607745e37c1f3ac7d61a47db96a3d01c884682432c91f1d77568045337e8",
            "terminal_head": "sha256:a3bd8ecd8578b28158b96a3dce814910beb3d627068159dc668a682c85b85448",
            "promotion_tmg": "sha256:f6eacc1e90f63d90b2487d0230fc1a10ecdfe571124dbd317efc12f7dcb93821",
            "promotion_artifact": "sha256:2d6bc5b206545042e13faa5e9b4d9a0ec6b0ccf4929755c01025746b8ab4523c",
        },
        "internal_manifest_hash": internal_manifest["content_hash"],
        "internal_checksum_entries": checksum_count,
        "archive_replay": replay,
        "accompanying_files": companions,
        "claim_boundary": "exact finite affine proposal and literal promotion/evidence transaction authority; not broader learning or AGI",
    })
    manifest_path = OUT / "TOM_World_Query_Kernel_0_5_2_release_manifest.json"
    manifest_path.write_bytes(canonical_bytes(record) + b"\n")

    summary = f"""# TOM World & Query Kernel 0.5.2 — Delivery summary

Status: **pass**

```text
ZIP:       {ZIP.name}
Alias:     {ALIAS.name}
Bytes:     {ZIP.stat().st_size}
Entries:   {len(files(ROOT))}
SHA-256:   {sha(ZIP)}
Tests:     238 passed
Replay:    {replay['compared_file_boundaries']} file boundaries plus promotion-store tree equal
```

Version 0.5.2 follows the CODEX 0.5.1 correction exactly: no broader learner family was added. The release formalizes acceptance/rejection, complete evidence enumeration, expected-parent promotion, snapshots, transactions, commits, and publication sequencing as content-addressed bounded formal definitions. The host performs generic immutable writes and compare-and-swap only.

The previous corrective base archive is pinned as `{record['corrective_base']['sha256']}`.
"""
    summary_path = OUT / "TOM_World_Query_Kernel_0_5_2_DELIVERY_SUMMARY.md"
    summary_path.write_text(summary, encoding="utf-8")

    checksum_targets = [ZIP, ALIAS, manifest_path, summary_path] + [OUT / name for name in EXTERNAL]
    checksum_path = OUT / "TOM_World_Query_Kernel_0_5_2_SHA256SUMS.txt"
    checksum_path.write_text(
        "\n".join(f"{sha(path)}  {path.name}" for path in sorted(set(checksum_targets), key=lambda p: p.name)) + "\n",
        encoding="utf-8",
    )
    return record


def prerequisites() -> tuple[dict[str, Any], dict[str, Any]]:
    validation = json.loads((ROOT / "validation/learner052/validation_report.json").read_text(encoding="utf-8"))
    clean = json.loads((ROOT / "validation/learner052/clean_rebuild.json").read_text(encoding="utf-8"))
    proof = json.loads((ROOT / "validation/learner052/promotion_authority.proof.json").read_text(encoding="utf-8"))
    continuation = json.loads((ROOT / "validation/learner052/continuation_handoff_verification.json").read_text(encoding="utf-8"))
    if not (
        verify_hash(validation) and validation.get("status") == "pass" and validation.get("test_count") >= 238
        and verify_hash(clean) and clean.get("status") == "pass" and clean.get("all_boundaries_equal") is True
        and verify_hash(proof) and proof.get("status") == "pass"
        and verify_hash(continuation) and continuation.get("valid") is True
    ):
        raise RuntimeError("release prerequisites are not passing")
    return validation, clean


def main() -> int:
    prerequisites()
    clean_transients(ROOT)
    internal, checksum_count = write_internal_inventory()
    names = write_zip(ZIP)
    verify_zip(ZIP, names)
    replay = replay_archive()
    record = write_external(replay, internal, checksum_count)
    print(json.dumps({
        "status": "pass",
        "zip": ZIP.name,
        "alias": ALIAS.name,
        "bytes": ZIP.stat().st_size,
        "entries": len(names),
        "sha256": sha_prefixed(ZIP),
        "internal_manifest_files": internal["file_count_excluding_manifest_and_checksum"],
        "internal_checksum_entries": checksum_count,
        "archive_replay_file_boundaries": replay["compared_file_boundaries"],
        "store_tree_equal": replay["store_tree_equal"],
        "release_manifest_hash": record["content_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
