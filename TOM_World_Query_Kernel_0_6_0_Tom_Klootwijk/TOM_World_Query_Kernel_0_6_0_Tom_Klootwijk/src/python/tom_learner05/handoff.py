"""Verification of the 0.4.2 literal-only handoff boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from tom_world03.canonical import attach_hash, require_hash

from .model import BASE_HANDOFF_HASH, BASE_WORLD_HASH, CANONICAL_SEED_SHA256

HANDOFF_SCHEMA = "TOM-LITERAL-HANDOFF-0.4.2"
CORRECTIVE_HANDOFF_SCHEMA = "TOM-CORRECTIVE-HANDOFF-0.5.1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def verify_literal_handoff(root: str | Path, handoff_path: str | Path | None = None) -> dict[str, Any]:
    base = Path(root).resolve()
    path = Path(handoff_path).resolve() if handoff_path is not None else base / "sources/TOM_LITERAL_HANDOFF_0_4_2.json"
    handoff = json.loads(path.read_text(encoding="utf-8"))
    require_hash(handoff, label="literal handoff")
    if handoff.get("schema") != HANDOFF_SCHEMA:
        raise ValueError(f"literal handoff schema must be {HANDOFF_SCHEMA}")
    if handoff.get("content_hash") != BASE_HANDOFF_HASH:
        raise ValueError("literal handoff identity differs from the learner base binding")
    if handoff.get("semantic_change") is not False:
        raise ValueError("0.4.2 literal handoff must declare no semantic change")
    if handoff.get("canonical_seed_sha256") != "sha256:" + CANONICAL_SEED_SHA256:
        raise ValueError("literal handoff canonical seed binding mismatch")

    records = handoff.get("authoritative_files")
    if not isinstance(records, list) or not records:
        raise ValueError("literal handoff requires authoritative_files")
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    paths: set[str] = set()
    for item in records:
        if not isinstance(item, Mapping):
            errors.append("authoritative file entry is not an object")
            continue
        rel = str(item.get("path", ""))
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            errors.append(f"unsafe authoritative path {rel!r}")
            continue
        if rel in paths:
            errors.append(f"duplicate authoritative path {rel}")
            continue
        paths.add(rel)
        candidate = base / rel
        expected_size = int(item.get("bytes", -1))
        expected_hash = str(item.get("sha256", ""))
        exists = candidate.is_file()
        actual_size = candidate.stat().st_size if exists else None
        actual_hash = _sha256(candidate) if exists else None
        equal = exists and actual_size == expected_size and actual_hash == expected_hash
        if not equal:
            errors.append(
                f"authoritative file mismatch {rel}: expected {expected_size}/{expected_hash}, "
                f"actual {actual_size}/{actual_hash}"
            )
        results.append({
            "path": rel,
            "expected_bytes": expected_size,
            "actual_bytes": actual_size,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "equal": equal,
        })

    seed = base / "TOM_seed_genome_2026-09-01.txt"
    seed_ok = seed.is_file() and seed.stat().st_size == 244 and not seed.read_bytes().endswith((b"\n", b"\r")) and _sha256(seed) == "sha256:" + CANONICAL_SEED_SHA256
    if not seed_ok:
        errors.append("canonical seed bytes fail the literal handoff contract")

    return attach_hash({
        "schema": "TOM-LITERAL-HANDOFF-VERIFICATION-0.4.2",
        "handoff_hash": handoff["content_hash"],
        "base_world_hash": BASE_WORLD_HASH,
        "root": base.name,
        "authoritative_file_count": len(records),
        "canonical_seed_verified": seed_ok,
        "files": results,
        "valid": not errors,
        "errors": errors,
    })


def _safe_relative(value: Any, *, label: str) -> str:
    rel = str(value)
    parts = Path(rel).parts
    if not rel or Path(rel).is_absolute() or ".." in parts:
        raise ValueError(f"unsafe {label} path {rel!r}")
    return rel


def verify_corrective_handoff(
    root: str | Path,
    corrective_path: str | Path | None = None,
) -> dict[str, Any]:
    """Verify the 0.4.2 base plus explicit, byte-preserved 0.5.1 changes.

    This does not relabel modified files as an unchanged 0.4.2 handoff.  Every
    replaced base file is checked against both its original literal bytes and
    its declared corrective bytes, while every other base file must remain
    byte-identical in place.
    """

    base = Path(root).resolve()
    base_path = base / "sources/TOM_LITERAL_HANDOFF_0_4_2.json"
    overlay_path = (
        Path(corrective_path).resolve()
        if corrective_path is not None
        else base / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"
    )
    old = json.loads(base_path.read_text(encoding="utf-8"))
    require_hash(old, label="literal handoff")
    if old.get("schema") != HANDOFF_SCHEMA or old.get("content_hash") != BASE_HANDOFF_HASH:
        raise ValueError("corrective handoff base identity mismatch")

    corrective = json.loads(overlay_path.read_text(encoding="utf-8"))
    require_hash(corrective, label="corrective handoff")
    if corrective.get("schema") != CORRECTIVE_HANDOFF_SCHEMA:
        raise ValueError(f"corrective handoff schema must be {CORRECTIVE_HANDOFF_SCHEMA}")
    if corrective.get("base_handoff_hash") != BASE_HANDOFF_HASH:
        raise ValueError("corrective handoff does not bind the 0.4.2 base")
    if corrective.get("canonical_seed_sha256") != "sha256:" + CANONICAL_SEED_SHA256:
        raise ValueError("corrective handoff canonical seed binding mismatch")
    if corrective.get("semantic_change") is not True:
        raise ValueError("0.5.1 corrective handoff must declare its semantic change")

    old_records = old.get("authoritative_files")
    replacements = corrective.get("replacements")
    additions = corrective.get("additions")
    if not isinstance(old_records, list) or not old_records:
        raise ValueError("base handoff requires authoritative_files")
    if not isinstance(replacements, list) or not replacements:
        raise ValueError("corrective handoff requires replacements")
    if not isinstance(additions, list) or not additions:
        raise ValueError("corrective handoff requires additions")

    old_by_path = {str(item.get("path")): item for item in old_records if isinstance(item, Mapping)}
    replacement_by_path: dict[str, Mapping[str, Any]] = {}
    errors: list[str] = []
    replacement_results: list[dict[str, Any]] = []
    for item in replacements:
        if not isinstance(item, Mapping):
            errors.append("replacement entry is not an object")
            continue
        try:
            rel = _safe_relative(item.get("path"), label="replacement")
            prior_rel = _safe_relative(item.get("prior_copy"), label="prior-copy")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if rel in replacement_by_path:
            errors.append(f"duplicate replacement path {rel}")
            continue
        replacement_by_path[rel] = item
        inherited = old_by_path.get(rel)
        prior_bytes = int(item.get("prior_bytes", -1))
        prior_hash = str(item.get("prior_sha256", ""))
        current_bytes = int(item.get("bytes", -1))
        current_hash = str(item.get("sha256", ""))
        base_binding_equal = bool(
            inherited
            and inherited.get("bytes") == prior_bytes
            and inherited.get("sha256") == prior_hash
        )
        prior = base / prior_rel
        current = base / rel
        prior_equal = bool(
            prior.is_file()
            and prior.stat().st_size == prior_bytes
            and _sha256(prior) == prior_hash
        )
        current_equal = bool(
            current.is_file()
            and current.stat().st_size == current_bytes
            and _sha256(current) == current_hash
        )
        if not base_binding_equal:
            errors.append(f"replacement prior binding differs from base handoff: {rel}")
        if not prior_equal:
            errors.append(f"preserved prior bytes mismatch: {prior_rel}")
        if not current_equal:
            errors.append(f"corrective replacement bytes mismatch: {rel}")
        replacement_results.append({
            "path": rel,
            "prior_copy": prior_rel,
            "base_binding_equal": base_binding_equal,
            "prior_bytes_equal": prior_equal,
            "corrective_bytes_equal": current_equal,
            "prior_sha256": prior_hash,
            "corrective_sha256": current_hash,
            "reason": item.get("reason"),
        })

    unchanged_results: list[dict[str, Any]] = []
    for rel, item in sorted(old_by_path.items()):
        if rel in replacement_by_path:
            continue
        try:
            safe = _safe_relative(rel, label="base-authority")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        path = base / safe
        equal = bool(
            path.is_file()
            and path.stat().st_size == int(item.get("bytes", -1))
            and _sha256(path) == str(item.get("sha256", ""))
        )
        if not equal:
            errors.append(f"unchanged base authority mismatch: {rel}")
        unchanged_results.append({"path": rel, "equal": equal})

    if set(replacement_by_path) - set(old_by_path):
        errors.append("corrective replacement names a path absent from the base handoff")

    addition_results: list[dict[str, Any]] = []
    addition_paths: set[str] = set()
    for item in additions:
        if not isinstance(item, Mapping):
            errors.append("addition entry is not an object")
            continue
        try:
            rel = _safe_relative(item.get("path"), label="addition")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if rel in addition_paths or rel in old_by_path:
            errors.append(f"duplicate or inherited addition path {rel}")
            continue
        addition_paths.add(rel)
        path = base / rel
        equal = bool(
            path.is_file()
            and path.stat().st_size == int(item.get("bytes", -1))
            and _sha256(path) == str(item.get("sha256", ""))
        )
        if not equal:
            errors.append(f"corrective addition bytes mismatch: {rel}")
        addition_results.append({
            "path": rel,
            "bytes": item.get("bytes"),
            "sha256": item.get("sha256"),
            "equal": equal,
            "role": item.get("role"),
        })

    seed = base / "TOM_seed_genome_2026-09-01.txt"
    seed_ok = bool(
        seed.is_file()
        and seed.stat().st_size == 244
        and not seed.read_bytes().endswith((b"\n", b"\r"))
        and _sha256(seed) == "sha256:" + CANONICAL_SEED_SHA256
    )
    if not seed_ok:
        errors.append("canonical seed bytes fail the corrective handoff contract")

    return attach_hash({
        "schema": "TOM-CORRECTIVE-HANDOFF-VERIFICATION-0.5.1",
        "base_handoff_hash": old["content_hash"],
        "handoff_hash": old["content_hash"],
        "corrective_handoff_hash": corrective["content_hash"],
        "base_world_hash": BASE_WORLD_HASH,
        "root": base.name,
        "canonical_seed_verified": seed_ok,
        "base_authoritative_file_count": len(old_records),
        "unchanged_base_file_count": len(unchanged_results),
        "replacement_count": len(replacement_results),
        "addition_count": len(addition_results),
        "unchanged_files": unchanged_results,
        "replacements": replacement_results,
        "additions": addition_results,
        "valid": not errors,
        "errors": errors,
    })
