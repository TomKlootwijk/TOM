from __future__ import annotations

"""Deterministic package and replay for the corrective WQK 0.5.1 handoff."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import zipfile
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.5.1"
PACKAGE_NAME = "TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_Tom_Klootwijk"
# The development checkout is intentionally double-nested; a normal extracted
# package is not. Collapse only the duplicated checkout directory so a shipped
# package writes beside itself instead of escaping two levels upward.
OUT = ROOT.parent.parent if ROOT.parent.name == ROOT.name else ROOT.parent
ZIP = OUT / f"{PACKAGE_NAME}.zip"
ALIAS = OUT / "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.zip"
FIXED_TIME = (2026, 9, 2, 0, 0, 0)

MANIFEST_REL = Path("checksums/PACKAGE_MANIFEST.json")
CHECKSUMS_REL = Path("checksums/SHA256SUMS.txt")
RELEASE_MANIFEST = OUT / "TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_release_manifest.json"
RELEASE_CHECKSUMS = OUT / "TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_SHA256SUMS.txt"
DELIVERY = OUT / "TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_DELIVERY_SUMMARY.md"

EXCLUDED = {".git", ".pytest_cache", "__pycache__", "build", "dist"}
CACHE_FILE_NAMES = {".DS_Store"}
CACHE_SUFFIXES = {".pyc", ".pyo"}
MINIMUM_TEST_COUNT = 172
VALIDATION_SCHEMA = "TOM-LEARNER-0.1-WQK-0.5.1-VALIDATION-REPORT"
PACKAGE_MANIFEST_SCHEMA = "TOM-LEARNER-0.1-WQK-0.5.1-CORRECTIVE-HANDOFF-PACKAGE-MANIFEST"

REPLAY_FILES = (
    "sources/TOM_LITERAL_HANDOFF_0_4_2.json",
    "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json",
    "spec/TOMAGI_1_0_FORMAL_DEFINITION.md",
    "spec/tomagi.schema.json",
    "spec/TOM_SEEDED_COMPILATION_1_0.md",
    "spec/tom_seeded_program.schema.json",
    "spec/tom_seed_token_registry_1_0.json",
    "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md",
    "docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md",
    "examples/learner05/benchmark_plan.json",
    "examples/learner05/benchmark_manifest.json",
    "examples/learner05/benchmark_oracle.json",
    "examples/learner05/learner05_affine_authority.formal.json",
    "examples/learner05/learner05_formal_authority.literal.json",
    "examples/learner05/learner05_release_artifact.literal.json",
    "examples/learner05/corrective_handoff_0_5_1.literal.json",
    "tools/build_corrective_handoff_artifact.py",
    "validation/learner05/corrective_handoff_verification.json",
    "validation/learner05/baseline_comparison.json",
    "validation/learner05/leakage_certificate.json",
    "validation/learner05/store_audit.json",
    "validation/learner05/store_reconstruction.json",
    "validation/learner05/fixture_report.json",
    "validation/learner05/rejection_capsule.json",
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
    "validation/learner05/tests.txt",
    "validation/learner05/clean_rebuild.json",
    "validation/learner05/validation_report.json",
    "validation/learner05/VALIDATION.md",
)

COMPANIONS = {
    "TOM_WQK_0_5_1_SPEC.md": "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md",
    "TOM_WQK_0_5_1_RELEASE.md": "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md",
    "TOM_WQK_0_5_1_BASE_LITERAL_HANDOFF.json": "sources/TOM_LITERAL_HANDOFF_0_4_2.json",
    "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.json": "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json",
    "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF_VERIFICATION.json": "validation/learner05/corrective_handoff_verification.json",
    "TOM_WQK_0_5_1_SEEDED_COMPILATION_SPEC.md": "spec/TOM_SEEDED_COMPILATION_1_0.md",
    "TOM_WQK_0_5_1_SEEDED_PROGRAM_SCHEMA.json": "spec/tom_seeded_program.schema.json",
    "TOM_WQK_0_5_1_FORMAL_AUTHORITY_PROGRAM.json": "examples/learner05/learner05_affine_authority.formal.json",
    "TOM_WQK_0_5_1_FORMAL_AUTHORITY_LITERAL.json": "examples/learner05/learner05_formal_authority.literal.json",
    "TOM_WQK_0_5_1_FORMAL_AUTHORITY_PROOF.json": "validation/learner05/learner05_formal_authority.proof.json",
    "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF_DOCUMENT.md": "docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md",
    "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF_LITERAL.json": "examples/learner05/corrective_handoff_0_5_1.literal.json",
    "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF_ARTIFACT_PROOF.json": "validation/learner05/corrective_handoff_0_5_1.proof.json",
    "TOM_WQK_0_5_1_BENCHMARK_PLAN.json": "examples/learner05/benchmark_plan.json",
    "TOM_WQK_0_5_1_BENCHMARK_MANIFEST.json": "examples/learner05/benchmark_manifest.json",
    "TOM_WQK_0_5_1_BENCHMARK_ORACLE.json": "examples/learner05/benchmark_oracle.json",
    "TOM_WQK_0_5_1_FIXTURE_REPORT.json": "validation/learner05/fixture_report.json",
    "TOM_WQK_0_5_1_LEAKAGE_CERTIFICATE.json": "validation/learner05/leakage_certificate.json",
    "TOM_WQK_0_5_1_BASELINE_COMPARISON.json": "validation/learner05/baseline_comparison.json",
    "TOM_WQK_0_5_1_STORE_AUDIT.json": "validation/learner05/store_audit.json",
    "TOM_WQK_0_5_1_STORE_RECONSTRUCTION.json": "validation/learner05/store_reconstruction.json",
    "TOM_WQK_0_5_1_REJECTION_CAPSULE.json": "validation/learner05/rejection_capsule.json",
    "TOM_WQK_0_5_1_VALIDATION_REPORT.json": "validation/learner05/validation_report.json",
    "TOM_WQK_0_5_1_CLEAN_REBUILD.json": "validation/learner05/clean_rebuild.json",
    "TOM_WQK_0_5_0_HISTORICAL_RELEASE_ARTIFACT_PROOF.json": "validation/learner05/learner05_release_artifact.proof.json",
    "TOM_WQK_0_5_1_CANONICAL_SEED.txt": "TOM_seed_genome_2026-09-01.txt",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def semantic_content_hash(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("content_hash", None)
    data = json.dumps(
        body,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def require_semantic_hash(record: Mapping[str, Any], *, label: str) -> str:
    claimed = record.get("content_hash")
    if not isinstance(claimed, str) or claimed != semantic_content_hash(record):
        raise RuntimeError(f"{label} content hash mismatch")
    return claimed


def safe_relative(value: Any, *, label: str) -> str:
    rel = str(value)
    path = PurePosixPath(rel)
    if (
        "\\" in rel
        or path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise RuntimeError(f"unsafe {label} path {rel!r}")
    return path.as_posix()


def corrective_declared_files(root: Path) -> tuple[str, ...]:
    overlay = json.loads((root / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json").read_text(encoding="utf-8"))
    paths: set[str] = set()
    for index, item in enumerate(overlay.get("replacements", [])):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"corrective replacement {index} is not an object")
        paths.add(safe_relative(item.get("path"), label="corrective replacement"))
        paths.add(safe_relative(item.get("prior_copy"), label="preserved prior copy"))
    for index, item in enumerate(overlay.get("additions", [])):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"corrective addition {index} is not an object")
        paths.add(safe_relative(item.get("path"), label="corrective addition"))
    return tuple(sorted(paths))


def replay_files(root: Path) -> tuple[str, ...]:
    return tuple(sorted(set(REPLAY_FILES) | set(corrective_declared_files(root))))


def _tree_files(path: Path) -> list[Path]:
    result = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(path)
        if (
            any(part in EXCLUDED for part in relative.parts)
            or item.name in CACHE_FILE_NAMES
            or item.suffix in CACHE_SUFFIXES
        ):
            continue
        result.append(item)
    return sorted(result, key=lambda item: item.relative_to(path).as_posix())


def hash_tree(path: Path) -> str:
    h = hashlib.sha256()
    for item in _tree_files(path):
        rel = item.relative_to(path).as_posix().encode("utf-8")
        data = item.read_bytes()
        h.update(len(rel).to_bytes(8, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clean_transients(root: Path = ROOT) -> None:
    for path in (root / "build", root / "dist", root / ".pytest_cache"):
        shutil.rmtree(path, ignore_errors=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for pattern in ("*.pyc", "*.pyo", ".DS_Store"):
        for path in root.rglob(pattern):
            if path.is_file():
                path.unlink()
    (root / MANIFEST_REL).unlink(missing_ok=True)
    (root / CHECKSUMS_REL).unlink(missing_ok=True)


def files(root: Path = ROOT, *, exclude_inventory: bool = False) -> list[Path]:
    manifest = root / MANIFEST_REL
    checksums = root / CHECKSUMS_REL
    excluded = {manifest, checksums} if exclude_inventory else set()
    result = []
    for path in root.rglob("*"):
        if not path.is_file() or path in excluded:
            continue
        rel = path.relative_to(root)
        if (
            any(part in EXCLUDED for part in rel.parts)
            or path.name in CACHE_FILE_NAMES
            or path.suffix in CACHE_SUFFIXES
        ):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix())


def prerequisites(root: Path = ROOT) -> dict[str, Any]:
    validation = json.loads((root / "validation/learner05/validation_report.json").read_text(encoding="utf-8"))
    require_semantic_hash(validation, label="0.5.1 validation report")
    if (
        validation.get("schema") != VALIDATION_SCHEMA
        or validation.get("release") != RELEASE_VERSION
        or validation.get("status") != "pass"
        or validation.get("failure_count") != 0
    ):
        raise RuntimeError("corrective 0.5.1 validation must pass before packaging")
    test_count = int(validation.get("test_count", 0))
    if test_count < MINIMUM_TEST_COUNT:
        raise RuntimeError("learner test count is below the validated release baseline")
    if validation.get("uploaded_0_4_2_archive_used") is not False:
        raise RuntimeError("validation does not preserve the inaccessible-upload boundary")
    overlay_path = root / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    corrective_handoff_hash = require_semantic_hash(overlay, label="corrective handoff")
    if validation.get("corrective_handoff_hash") != corrective_handoff_hash:
        raise RuntimeError("validation does not bind the corrective handoff content hash")
    base_handoff = json.loads((root / "sources/TOM_LITERAL_HANDOFF_0_4_2.json").read_text(encoding="utf-8"))
    base_handoff_hash = require_semantic_hash(base_handoff, label="base literal handoff")
    if validation.get("literal_handoff_hash") != base_handoff_hash:
        raise RuntimeError("validation does not retain the inherited base handoff binding")
    handoff_verification = json.loads(
        (root / "validation/learner05/corrective_handoff_verification.json").read_text(encoding="utf-8")
    )
    require_semantic_hash(handoff_verification, label="corrective handoff verification")
    if not (
        handoff_verification.get("valid") is True
        and handoff_verification.get("corrective_handoff_hash") == corrective_handoff_hash
        and handoff_verification.get("base_handoff_hash") == base_handoff_hash
    ):
        raise RuntimeError("corrective handoff verification is not passing or correctly bound")
    handoff_artifact_proof = json.loads(
        (root / "validation/learner05/corrective_handoff_0_5_1.proof.json").read_text(encoding="utf-8")
    )
    handoff_artifact_proof_hash = require_semantic_hash(
        handoff_artifact_proof,
        label="corrective handoff artifact proof",
    )
    artifact_execution = handoff_artifact_proof.get("execution", {})
    artifact_materialized = handoff_artifact_proof.get("materialized_artifact", {})
    artifact_compiled = handoff_artifact_proof.get("compiled_program", {})
    if not (
        handoff_artifact_proof.get("schema")
        == "TOM-WQK-0.5.1-CORRECTIVE-HANDOFF-ARTIFACT-PROOF-1.0"
        and handoff_artifact_proof.get("status") == "pass"
        and handoff_artifact_proof.get("corrective_overlay", {}).get("content_hash")
        == corrective_handoff_hash
        and artifact_execution.get("python_c_full_trace_equal") is True
        and artifact_execution.get("python_c_emit_equal") is True
        and artifact_materialized.get("matches_authored_document") is True
        and artifact_compiled.get("in_place_recompile_equal") is True
        and validation.get("corrective_handoff_artifact_proof_hash")
        == handoff_artifact_proof_hash
    ):
        raise RuntimeError("corrective handoff artifact proof is not passing or linked to validation")
    formal_authority_proof = json.loads(
        (root / "validation/learner05/learner05_formal_authority.proof.json").read_text(encoding="utf-8")
    )
    formal_authority_proof_hash = require_semantic_hash(
        formal_authority_proof,
        label="formal learner authority proof",
    )
    formal_execution = formal_authority_proof.get("execution", {})
    formal_compiled = formal_authority_proof.get("compiled_program", {})
    formal_materialized = formal_authority_proof.get("materialized_artifact", {})
    if not (
        formal_authority_proof.get("schema") == "TOM-WQK-0.5.1-FORMAL-AUTHORITY-PROOF-1.0"
        and formal_authority_proof.get("status") == "pass"
        and formal_execution.get("python_c_full_trace_equal") is True
        and formal_execution.get("python_c_emit_equal") is True
        and formal_compiled.get("in_place_recompile_equal") is True
        and formal_materialized.get("canonical_json_plus_lf") is True
        and validation.get("formal_authority_proof_hash") == formal_authority_proof_hash
    ):
        raise RuntimeError("formal learner authority proof is not passing or linked to validation")
    clean_rebuild = json.loads((root / "validation/learner05/clean_rebuild.json").read_text(encoding="utf-8"))
    require_semantic_hash(clean_rebuild, label="clean-rebuild certificate")
    if not (
        clean_rebuild.get("status") == "pass"
        and clean_rebuild.get("tests") == test_count
        and clean_rebuild.get("store_tree_equal") is True
        and validation.get("clean_rebuild_hash") == clean_rebuild.get("content_hash")
    ):
        raise RuntimeError("clean-rebuild evidence is not passing or linked to final validation")
    expected_source_tree = "sha256:" + hash_tree(root / "src/python/tom_learner05")
    if clean_rebuild.get("source_inputs", {}).get("learner_source_tree") != expected_source_tree:
        raise RuntimeError("clean-rebuild learner source hash does not match cache-free source files")
    source_inputs = clean_rebuild.get("source_inputs", {})
    expected_sources = {
        "literal_handoff": root / "sources/TOM_LITERAL_HANDOFF_0_4_2.json",
        "corrective_handoff": overlay_path,
        "benchmark_plan": root / "examples/learner05/benchmark_plan.json",
        "release_artifact_literal_source": root / "examples/learner05/learner05_release_artifact.literal.json",
        "formal_authority_literal_source": root / "examples/learner05/learner05_formal_authority.literal.json",
        "formal_authority_program": root / "examples/learner05/learner05_affine_authority.formal.json",
        "corrective_handoff_document": root / "docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md",
        "corrective_handoff_literal_source": root / "examples/learner05/corrective_handoff_0_5_1.literal.json",
        "corrective_handoff_builder": root / "tools/build_corrective_handoff_artifact.py",
        "corrective_learner_spec": root / "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md",
        "tomagi_formal_spec": root / "spec/TOMAGI_1_0_FORMAL_DEFINITION.md",
        "tomagi_schema": root / "spec/tomagi.schema.json",
        "seeded_compilation_spec": root / "spec/TOM_SEEDED_COMPILATION_1_0.md",
        "seeded_program_schema": root / "spec/tom_seeded_program.schema.json",
        "seed_token_registry": root / "spec/tom_seed_token_registry_1_0.json",
    }
    if not isinstance(source_inputs, Mapping) or any(
        source_inputs.get(key) != "sha256:" + sha(path)
        for key, path in expected_sources.items()
    ):
        raise RuntimeError("clean-rebuild certificate does not bind all corrective/formal source inputs")
    tests_text = (root / "validation/learner05/tests.txt").read_text(encoding="utf-8")
    test_summaries = list(re.finditer(r"^Ran ([0-9]+) tests$", tests_text, re.MULTILINE))
    status_lines = (
        re.findall(
            r"^(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)$",
            tests_text[test_summaries[0].end():],
            re.MULTILINE,
        )
        if len(test_summaries) == 1
        else []
    )
    if (
        " tests in " in tests_text
        or len(test_summaries) != 1
        or int(test_summaries[0].group(1)) != test_count
        or len(status_lines) != 1
        or not status_lines[0].startswith("OK")
    ):
        raise RuntimeError("test evidence is not in canonical timing-free form")
    required = [root / rel for rel in replay_files(root)]
    required.extend(root / rel for rel in COMPANIONS.values())
    required.extend(sorted((root / "examples/learner05/datasets").glob("*.json")))
    missing = [path.relative_to(root).as_posix() for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing release prerequisites: {missing}")
    seed = (root / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    if len(seed) != 244 or seed.endswith((b"\n", b"\r")) or hashlib.sha256(seed).hexdigest() != "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5":
        raise RuntimeError("canonical seed identity mismatch")
    return validation


def write_inventory(validation: Mapping[str, Any], root: Path) -> None:
    if root.name != PACKAGE_NAME:
        raise RuntimeError("package inventory must be written beneath the corrective 0.5.1 package root")
    manifest = root / MANIFEST_REL
    checksums = root / CHECKSUMS_REL
    listed = files(root, exclude_inventory=True)
    record = {
        "schema": PACKAGE_MANIFEST_SCHEMA,
        "package": PACKAGE_NAME,
        "release": RELEASE_VERSION,
        "status": "pass",
        "canonical_seed_sha256": "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
        "literal_handoff_hash": validation["literal_handoff_hash"],
        "corrective_handoff_hash": validation["corrective_handoff_hash"],
        "uploaded_0_4_2_archive_used": False,
        "validation_hash": validation["content_hash"],
        "fixture_hash": validation["fixture_hash"],
        "formal_authority_proof_hash": validation["formal_authority_proof_hash"],
        "corrective_handoff_artifact_proof_hash": validation["corrective_handoff_artifact_proof_hash"],
        "test_count": validation["test_count"],
        "file_count_excluding_manifest_and_checksum": len(listed),
        "files": [
            {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in listed
        ],
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    write_json(manifest, record)
    checksum_files = [path for path in files(root) if path != checksums]
    checksums.write_text(
        "\n".join(f"{sha(path)}  {path.relative_to(root).as_posix()}" for path in checksum_files) + "\n",
        encoding="utf-8",
    )


def write_zip(
    source_root: Path,
    destination: Path = ZIP,
    package_name: str = PACKAGE_NAME,
) -> list[str]:
    if source_root.name != package_name:
        raise RuntimeError("ZIP source root and archive root name differ")
    destination.unlink(missing_ok=True)
    names = []
    with zipfile.ZipFile(destination, "w") as archive:
        for path in files(source_root):
            rel = path.relative_to(source_root).as_posix()
            name = f"{package_name}/{rel}"
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            names.append(name)
    return names


def safe_name(name: str, package_name: str = PACKAGE_NAME) -> None:
    p = PurePosixPath(name)
    if (
        "\\" in name
        or p.is_absolute()
        or not p.parts
        or p.parts[0] != package_name
        or any(part in {"", ".", ".."} for part in p.parts)
    ):
        raise RuntimeError(f"unsafe ZIP member {name!r}")


def verify_zip(
    names: list[str],
    path: Path = ZIP,
    package_name: str = PACKAGE_NAME,
) -> None:
    with zipfile.ZipFile(path) as archive:
        actual = [info.filename for info in archive.infolist()]
        if actual != names or actual != sorted(actual) or len(actual) != len(set(actual)):
            raise RuntimeError("ZIP entry order or uniqueness mismatch")
        for info in archive.infolist():
            safe_name(info.filename, package_name)
            if info.date_time != FIXED_TIME:
                raise RuntimeError("ZIP timestamp mismatch")
            if ((info.external_attr >> 16) & 0xFFFF) != 0o100644:
                raise RuntimeError("ZIP file mode mismatch")
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")


def verify_internal(root: Path) -> None:
    manifest = json.loads((root / MANIFEST_REL).read_text(encoding="utf-8"))
    if not (
        manifest.get("schema") == PACKAGE_MANIFEST_SCHEMA
        and manifest.get("package") == PACKAGE_NAME
        and manifest.get("release") == RELEASE_VERSION
        and manifest.get("status") == "pass"
    ):
        raise RuntimeError("internal corrective package manifest identity mismatch")
    manifest_items = manifest.get("files")
    if not isinstance(manifest_items, list):
        raise RuntimeError("internal package manifest files must be a list")
    manifest_seen: set[str] = set()
    for item in manifest_items:
        if not isinstance(item, Mapping):
            raise RuntimeError("internal package manifest entry must be an object")
        rel = safe_relative(item.get("path"), label="internal manifest")
        if rel in manifest_seen:
            raise RuntimeError(f"duplicate internal manifest entry {rel}")
        path = root / rel
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"internal manifest mismatch {rel}")
        manifest_seen.add(rel)
    expected_manifest = {
        path.relative_to(root).as_posix()
        for path in files(root, exclude_inventory=True)
    }
    if (
        manifest_seen != expected_manifest
        or manifest.get("file_count_excluding_manifest_and_checksum") != len(expected_manifest)
    ):
        raise RuntimeError("internal package manifest inventory is incomplete")
    checksum = root / CHECKSUMS_REL
    seen: set[str] = set()
    for line in checksum.read_text().splitlines():
        digest, rel = line.split("  ", 1)
        rel = safe_relative(rel, label="internal checksum")
        if rel in seen:
            raise RuntimeError(f"duplicate internal checksum entry {rel}")
        path = root / rel
        if not path.is_file() or sha(path) != digest:
            raise RuntimeError(f"internal checksum mismatch {rel}")
        seen.add(rel)
    expected = {path.relative_to(root).as_posix() for path in files(root) if path != checksum}
    if seen != expected:
        raise RuntimeError("internal checksum inventory is incomplete")


def remove_replay_outputs(root: Path) -> None:
    """Remove every corrective 0.5.1 generated boundary before replay.

    The inherited corrected 0.4.1 authority remains present and hash-verified.
    The learner data sets, evidence store, validation records, C build, and
    formal/documentation products are regenerated from the base plus corrective
    handoff, source code, benchmark plan, and literal definitions.
    """
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "examples/learner05/datasets", ignore_errors=True)
    shutil.rmtree(root / "examples/learner05/learner_store", ignore_errors=True)
    validation = root / "validation/learner05"
    shutil.rmtree(validation, ignore_errors=True)
    for rel in (
        "examples/learner05/benchmark_manifest.json",
        "examples/learner05/benchmark_oracle.json",
        "examples/learner05/learner05_formal_authority.tmg",
        "examples/learner05/learner05_formal_authority.tmg.compile.json",
        "examples/learner05/corrective_handoff_0_5_1.tmg",
        "examples/learner05/corrective_handoff_0_5_1.tmg.compile.json",
        "examples/learner05/learner05_release_artifact.tmg",
        "examples/learner05/learner05_release_artifact.tmg.compile.json",
        "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md",
    ):
        (root / rel).unlink(missing_ok=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for suffix in CACHE_SUFFIXES:
        for path in root.rglob(f"*{suffix}"):
            path.unlink()
    validation.mkdir(parents=True, exist_ok=True)


def run_full_validation(root: Path, *, label: str) -> None:
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root / "src/python"),
    }
    proc = subprocess.run(
        ["make", "validate-learner05"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=1200,
    )
    if proc.returncode:
        raise RuntimeError(
            f"{label} validation failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def byte_equal(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            a_chunk = a.read(1024 * 1024)
            b_chunk = b.read(1024 * 1024)
            if a_chunk != b_chunk:
                return False
            if not a_chunk:
                return True


def replay(reference_root: Path, zip_path: Path = ZIP) -> dict[str, Any]:
    original_files = {rel: sha(reference_root / rel) for rel in replay_files(reference_root)}
    expected_test_count = int(json.loads(
        (reference_root / "validation/learner05/validation_report.json").read_text(encoding="utf-8")
    ).get("test_count", 0))
    for path in sorted((reference_root / "examples/learner05/datasets").glob("*.json")):
        original_files[path.relative_to(reference_root).as_posix()] = sha(path)
    original_store = hash_tree(reference_root / "examples/learner05/learner_store")
    with tempfile.TemporaryDirectory(prefix="tom-learner05-archive-") as td:
        temp = Path(td)
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                safe_name(info.filename)
            archive.extractall(temp)
        extracted = temp / PACKAGE_NAME
        verify_internal(extracted)
        remove_replay_outputs(extracted)
        run_full_validation(extracted, label="independent archive replay")
        validation = json.loads(
            (extracted / "validation/learner05/validation_report.json").read_text(encoding="utf-8")
        )
        if not (
            validation.get("status") == "pass"
            and validation.get("test_count") == expected_test_count
            and expected_test_count >= MINIMUM_TEST_COUNT
            and validation.get("failure_count") == 0
        ):
            raise RuntimeError("archive clean full validation record did not pass")
        clean_rebuild = json.loads(
            (extracted / "validation/learner05/clean_rebuild.json").read_text(encoding="utf-8")
        )
        if not (
            clean_rebuild.get("status") == "pass"
            and clean_rebuild.get("tests") == expected_test_count
            and clean_rebuild.get("store_tree_equal") is True
            and validation.get("clean_rebuild_hash") == clean_rebuild.get("content_hash")
        ):
            raise RuntimeError("archive clean-rebuild evidence is not linked to final validation")
        prerequisites(extracted)
        comparisons = {}
        equal = True
        for rel, expected in original_files.items():
            path = extracted / rel
            actual = sha(path) if path.is_file() else None
            same = actual == expected
            equal &= same
            comparisons[rel] = {"packaged_sha256": expected, "replayed_sha256": actual, "equal": same}
        replay_store = hash_tree(extracted / "examples/learner05/learner_store")
        store_equal = replay_store == original_store
        equal &= store_equal
        if not equal:
            raise RuntimeError("archive replay boundary mismatch")
        rebuilt_zip = temp / f"{PACKAGE_NAME}.rebuilt.zip"
        rebuilt_names = write_zip(extracted, rebuilt_zip, PACKAGE_NAME)
        verify_zip(rebuilt_names, rebuilt_zip, PACKAGE_NAME)
        package_equal = byte_equal(zip_path, rebuilt_zip)
        if not package_equal:
            raise RuntimeError("archive replay produced a non-identical release ZIP")
        return {
            "release": RELEASE_VERSION,
            "literal_handoff_hash": validation.get("literal_handoff_hash"),
            "corrective_handoff_hash": validation.get("corrective_handoff_hash"),
            "zip_crc_and_path_safety": True,
            "internal_manifest_and_checksums": True,
            "validation_rerun": "pass",
            "replay_mode": "corrective-0.5.1-outputs-removed-before-independent-full-validation-and-byte-identical-repack",
            "validation_hash": validation.get("content_hash"),
            "validation_checks": validation.get("check_count"),
            "clean_rebuild_hash": clean_rebuild.get("content_hash"),
            "core_validation_hash": clean_rebuild.get("clean_core_validation_hash"),
            "compared_file_boundaries": len(comparisons),
            "store_tree_equal": store_equal,
            "packaged_store_tree_sha256": original_store,
            "replayed_store_tree_sha256": replay_store,
            "all_boundaries_equal": True,
            "package_byte_reproducible": True,
            "packaged_zip_bytes": zip_path.stat().st_size,
            "packaged_zip_sha256": sha(zip_path),
            "rebuilt_zip_sha256": sha(rebuilt_zip),
            "boundaries": comparisons,
        }


def publish(
    source_root: Path,
    validation: Mapping[str, Any],
    replay_record: Mapping[str, Any],
    names: list[str],
) -> dict[str, Any]:
    ALIAS.write_bytes(ZIP.read_bytes())
    published = []
    for destination, rel in sorted(COMPANIONS.items()):
        source = source_root / rel
        target = OUT / destination
        target.write_bytes(source.read_bytes())
        published.append({"path": destination, "source": rel, "bytes": target.stat().st_size, "sha256": sha(target)})
    release = {
        "schema": "TOM-LEARNER-0.1-WQK-0.5.1-CORRECTIVE-HANDOFF-RELEASE-MANIFEST",
        "release": RELEASE_VERSION,
        "release_kind": "corrective-handoff",
        "status": "pass",
        "package": {"path": ZIP.name, "bytes": ZIP.stat().st_size, "sha256": sha(ZIP), "entries": len(names), "root": PACKAGE_NAME},
        "alias": {"path": ALIAS.name, "bytes": ALIAS.stat().st_size, "sha256": sha(ALIAS)},
        "validation": {
            "tests": validation["test_count"],
            "checks": validation["check_count"],
            "failures": validation["failure_count"],
            "content_hash": validation["content_hash"],
            "fixture_hash": validation["fixture_hash"],
            "formal_authority_proof_hash": validation["formal_authority_proof_hash"],
            "corrective_handoff_artifact_proof_hash": validation["corrective_handoff_artifact_proof_hash"],
            "accepted": validation["accepted_count"],
            "false_promotions": validation["false_promotions"],
        },
        "literal_handoff_hash": validation["literal_handoff_hash"],
        "corrective_handoff_hash": validation["corrective_handoff_hash"],
        "uploaded_0_4_2_archive_used": False,
        "archive_replay": replay_record,
        "accompanying_files": published,
        "evidence_boundary": validation["evidence_boundary"],
    }
    write_json(RELEASE_MANIFEST, release)
    DELIVERY.write_text(
        "# TOM World & Query Kernel 0.5.1 — Corrective Handoff Delivery\n\n"
        "Status: **pass**\n\n"
        f"- ZIP: `{ZIP.name}`\n"
        f"- Bytes: {ZIP.stat().st_size}\n"
        f"- Entries: {len(names)}\n"
        f"- SHA-256: `{sha(ZIP)}`\n"
        f"- Tests: {validation['test_count']} passed\n"
        f"- Validation: {validation['check_count']} checks, {validation['failure_count']} failures\n"
        f"- Archive replay: {replay_record['compared_file_boundaries'] + 1} file/tree boundaries equal\n"
        f"- Base handoff: `{validation['literal_handoff_hash']}`\n"
        f"- Corrective handoff: `{validation['corrective_handoff_hash']}`\n"
        f"- Benchmark: 12 accepted exact rules, 7 rejected negative cases, {validation['false_promotions']} false promotions\n\n"
        "This release preserves the verified 0.4.2 base handoff and applies only the explicit, content-addressed 0.5.1 corrective overlay. Its formal learner authority and generated evidence were rebuilt in the named package root, replayed independently from the archive, and encoded twice to identical ZIP bytes.\n",
        encoding="utf-8",
    )
    targets = [ZIP, ALIAS, RELEASE_MANIFEST, DELIVERY] + [OUT / name for name in COMPANIONS]
    RELEASE_CHECKSUMS.write_text(
        "\n".join(f"{sha(path)}  {path.name}" for path in sorted(targets, key=lambda item: item.name)) + "\n",
        encoding="utf-8",
    )
    return release


def main() -> None:
    # Refuse to package a live tree whose current evidence is not already tied
    # to the exact corrective overlay. The deliverable itself is then rebuilt
    # under its final archive-root name so path-bearing evidence replays exactly.
    prerequisites(ROOT)
    source_snapshot_before = hash_tree(ROOT)
    with tempfile.TemporaryDirectory(prefix="tom-learner05-package-") as td:
        package_root = Path(td) / PACKAGE_NAME
        shutil.copytree(
            ROOT,
            package_root,
            ignore=shutil.ignore_patterns(
                *sorted(EXCLUDED),
                "*.pyc",
                "*.pyo",
                ".DS_Store",
            ),
        )
        source_snapshot_after = hash_tree(ROOT)
        copied_snapshot = hash_tree(package_root)
        if not (
            source_snapshot_before == source_snapshot_after == copied_snapshot
        ):
            raise RuntimeError("source tree changed while the corrective package snapshot was copied")
        clean_transients(package_root)
        remove_replay_outputs(package_root)
        run_full_validation(package_root, label="corrective package-root rebuild")
        validation = prerequisites(package_root)
        clean_transients(package_root)
        write_inventory(validation, package_root)
        names = write_zip(package_root)
        verify_zip(names)
        replay_record = replay(package_root)
        release = publish(package_root, validation, replay_record, names)
        print(json.dumps({
            "status": "pass",
            "release": RELEASE_VERSION,
            "zip": release["package"],
            "alias": release["alias"],
            "tests": validation["test_count"],
            "validation_checks": validation["check_count"],
            "archive_replay_boundaries": replay_record["compared_file_boundaries"] + 1,
            "release_manifest": RELEASE_MANIFEST.name,
            "release_checksums": RELEASE_CHECKSUMS.name,
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
