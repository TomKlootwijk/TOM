from __future__ import annotations

"""Build and verify the exact 0.5.1 -> 0.5.2 corrective continuation record."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tom_learner05.handoff import verify_corrective_handoff

HANDOFF = ROOT / "sources/TOM_CONTINUATION_HANDOFF_0_5_2.json"
VERIFICATION = ROOT / "validation/learner052/continuation_handoff_verification.json"

BASE_ARCHIVE = {
    "filename": "TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_Tom_Klootwijk.zip",
    "bytes": 27022938,
    "sha256": "sha256:0f3bf159536b726fc68fc3e0ff7c1ff896c3bdf1e63a7449d5b507f67f043601",
    "zip_entries": 11197,
    "zip_crc": "pass",
}

REPLACEMENTS = (
    "VERSION",
    "Makefile",
    "pyproject.toml",
    "README.md",
    "CHANGELOG.md",
    "NOTICE.md",
    "docs/ROADMAP.md",
)

STATIC_ADDITIONS = (
    "TOM_AGI_ROADMAP_AND_STARTER_0_5_2.md",
    "TOM_WORLD_QUERY_KERNEL_0_5_2_RELEASE.md",
    "docs/TOM_WQK_0_5_2_TRANSACTION_AUTHORITY.md",
    "spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_2_TRANSACTION_AUTHORITY.md",
    "spec/tom_learner_promotion_authority_0_5_2.schema.json",
    "src/python/tomagi/immutable_store.py",
    "src/python/tom_learner052/__init__.py",
    "src/python/tom_learner052/__main__.py",
    "src/python/tom_learner052/cli.py",
    "src/python/tom_learner052/oracle.py",
    "tests/test_learner052_transaction_authority.py",
    "tools/build_learner052_continuation_handoff.py",
    "tools/build_learner052_promotion_authority.py",
    "tools/build_learner052_release_artifact.py",
    "tools/run_learner052_validation.py",
    "tools/verify_learner052_clean_rebuild.py",
    "tools/package_learner052_release.py",
    "examples/learner052/promotion_authority.formal.json",
    "examples/learner052/promotion_authority.literal.json",
    "examples/learner052/promotion_context.json",
    "examples/learner052/learner052_release_artifact.literal.json",
)


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha_bytes(data),
    }


def authority_input_paths() -> list[Path]:
    base = ROOT / "examples/learner052/authority_inputs"
    return sorted((p for p in base.rglob("*") if p.is_file()), key=lambda p: p.relative_to(ROOT).as_posix())


def build_record() -> dict[str, Any]:
    correction = verify_corrective_handoff(ROOT)
    if not correction.get("valid") or not verify_hash(correction):
        raise RuntimeError("0.5.1 corrective handoff verification failed")

    replacement_records = []
    for rel in REPLACEMENTS:
        old = ROOT / "sources/base_0_5_1_replaced" / rel
        current = ROOT / rel
        if not old.is_file() or not current.is_file():
            raise FileNotFoundError(rel)
        replacement_records.append({
            "path": rel,
            "prior": file_record(old) | {"path": f"sources/base_0_5_1_replaced/{rel}"},
            "replacement": file_record(current),
            "reason": "versioned 0.5.2 transaction-authority integration or documentation",
        })

    additions = [file_record(ROOT / rel) for rel in STATIC_ADDITIONS]
    additions.extend(file_record(path) for path in authority_input_paths())
    additions.sort(key=lambda item: item["path"])
    if len({item["path"] for item in additions}) != len(additions):
        raise RuntimeError("duplicate continuation addition path")

    record = attach_hash({
        "schema": "TOM-CONTINUATION-HANDOFF-0.5.2",
        "release": "0.5.2",
        "date": "2026-09-02",
        "status": "corrective-roadmap-continuation",
        "canonical_seed": {
            "path": "TOM_seed_genome_2026-09-01.txt",
            "bytes": 244,
            "sha256": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
            "terminal_newline": False,
        },
        "base_archive": BASE_ARCHIVE,
        "base_inventory": {
            "manifest": file_record(ROOT / "sources/base_0_5_1_inventory/PACKAGE_MANIFEST_0_5_1.json"),
            "checksums": file_record(ROOT / "sources/base_0_5_1_inventory/SHA256SUMS_0_5_1.txt"),
        },
        "corrective_overlay": {
            "path": "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json",
            "content_hash": "sha256:53951284853681ce239d07ce2ce783250ea78b3457fd221a43d88bd90344f4bf",
            "verification_content_hash": correction["content_hash"],
            "valid": True,
            "unchanged_inherited_files": correction["unchanged_base_file_count"],
            "replacements": correction["replacement_count"],
            "additions": correction["addition_count"],
        },
        "roadmap_discipline": {
            "broader_learner_added": False,
            "completed_boundary": "formal promotion/evidence transaction authority",
            "host_services": [
                "strict parsing and validation",
                "finite formal evaluation",
                "canonical hashing",
                "deterministic Cell48 lowering",
                "TOMAGI execution and trace capture",
                "authenticated byte materialization",
                "generic immutable addressed writes",
                "compare-and-swap publication",
                "audit and independent comparison",
            ],
            "formal_semantics": [
                "acceptance or rejection decision",
                "complete ordered evidence enumeration",
                "expected-parent binding",
                "promotion certificate",
                "snapshot",
                "transaction",
                "commit",
                "publication sequence and terminal head",
            ],
        },
        "replacements": replacement_records,
        "additions": additions,
        "next_permitted_milestone": "TOM Learner 0.2 / WQK 0.6 after clean and final-archive replay",
    })
    return record


def verify_record(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not verify_hash(record):
        errors.append("continuation content hash mismatch")
    if record.get("base_archive") != BASE_ARCHIVE:
        errors.append("base archive identity mismatch")

    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    if len(seed) != 244 or seed.endswith((b"\r", b"\n")) or sha_bytes(seed) != record["canonical_seed"]["sha256"]:
        errors.append("canonical seed mismatch")

    correction = verify_corrective_handoff(ROOT)
    if not correction.get("valid") or correction.get("content_hash") != record["corrective_overlay"]["verification_content_hash"]:
        errors.append("corrective overlay verification mismatch")

    for item in record.get("replacements", []):
        current = ROOT / item["path"]
        prior = ROOT / item["prior"]["path"]
        for label, path, expected in (
            ("replacement", current, item["replacement"]),
            ("prior", prior, item["prior"]),
        ):
            if not path.is_file():
                errors.append(f"missing {label} file {path.relative_to(ROOT)}")
            else:
                actual = file_record(path)
                if actual["bytes"] != expected["bytes"] or actual["sha256"] != expected["sha256"]:
                    errors.append(f"{label} file mismatch {path.relative_to(ROOT)}")

    for item in record.get("additions", []):
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"missing addition {item['path']}")
        else:
            actual = file_record(path)
            if actual["bytes"] != item["bytes"] or actual["sha256"] != item["sha256"]:
                errors.append(f"addition mismatch {item['path']}")

    for key, item in record.get("base_inventory", {}).items():
        path = ROOT / item["path"]
        if not path.is_file() or file_record(path)["sha256"] != item["sha256"]:
            errors.append(f"base inventory mismatch {key}")

    return attach_hash({
        "schema": "TOM-CONTINUATION-HANDOFF-VERIFICATION-0.5.2",
        "release": "0.5.2",
        "valid": not errors,
        "errors": errors,
        "continuation_handoff_hash": record.get("content_hash"),
        "corrective_handoff_verification_hash": correction.get("content_hash"),
        "replacement_count": len(record.get("replacements", [])),
        "addition_count": len(record.get("additions", [])),
        "base_archive_sha256": BASE_ARCHIVE["sha256"],
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", default=str(VERIFICATION))
    args = parser.parse_args()
    if args.write:
        record = build_record()
        HANDOFF.write_bytes(canonical_bytes(record) + b"\n")
    record = json.loads(HANDOFF.read_text(encoding="utf-8"))
    verification = verify_record(record)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(verification) + b"\n")
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0 if verification["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
