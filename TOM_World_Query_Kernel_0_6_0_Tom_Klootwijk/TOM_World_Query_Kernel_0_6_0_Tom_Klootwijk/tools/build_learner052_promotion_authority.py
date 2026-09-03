from __future__ import annotations

"""Build and validate the 0.5.2 formal promotion/evidence authority.

The authoritative domain behavior is the static content-addressed formal
program and its seeded TOMAGI graph.  This host tool performs only generic
source verification, compilation, deterministic execution, cross-backend
comparison, immutable publication, auditing, and independent-oracle comparison.
"""

import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples/learner052"
VAL = ROOT / "validation/learner052"
FORMAL_PROGRAM = BASE / "promotion_authority.formal.json"
LEARNER_PROGRAM = BASE / "authority_inputs/learner05_affine_authority.formal.json"
DATASET_DIR = BASE / "authority_inputs/datasets"
CONTEXT = BASE / "promotion_context.json"
CORRECTIVE = BASE / "authority_inputs/TOM_CORRECTIVE_HANDOFF_0_5_1.json"
REGISTRY = BASE / "authority_inputs/tom_seed_token_registry_1_0.json"
SOURCE = BASE / "promotion_authority.literal.json"
PROGRAM = BASE / "promotion_authority.tmg"
MATERIALIZED = VAL / "promotion_authority.materialized.json"
PROOF = VAL / "promotion_authority.proof.json"
ORACLE = VAL / "promotion_authority.oracle.json"
STORE = BASE / "promotion_store"
STORE_AUDIT = VAL / "promotion_store_audit.json"
STORE_RECONSTRUCTION = VAL / "promotion_store_reconstruction.json"
C_EXE = ROOT / "build/tomagi-c-learner052"

EXPECTED = {
    "promotion_program_content_hash": "sha256:f1030e332b5f7358c43603096a64ebca7f9268aaaf2fbbe16dbebc972daa8bdd",
    "promotion_program_file_sha256": "sha256:e8ddb14f88b24d54a2d3da4e80d1d8e7c6e7853b4c8d32b734a15b5b1de9a3a9",
    "learner_program_content_hash": "sha256:dd710388744a71861c90c15ef63bd85411f0652a2077f6f9ef9421997d626b28",
    "learner_execution_content_hash": "sha256:74d56499b6fb50d1a7a10ed7228f0c416ae5807c7a1564fb4308cc1fc5fda265",
    "learner_value_content_hash": "sha256:14c5e5e0dd4bc49d40eb8b8f3d86fbdb7bad4d86c872dbeea9799a5aeb92dd12",
    "promotion_execution_content_hash": "sha256:f1a5ccbab6eb64033200c480c3e45852c3f1eccb212eca344a98005e79ecc00d",
    "promotion_value_content_hash": "sha256:13544b08f0a211cc0b6b6a53484491159303bd45b42797422913d2b24459e3f2",
    "publication_plan_content_hash": "sha256:07b1607745e37c1f3ac7d61a47db96a3d01c884682432c91f1d77568045337e8",
    "terminal_head": "sha256:a3bd8ecd8578b28158b96a3dce814910beb3d627068159dc668a682c85b85448",
    "artifact_sha256": "sha256:2d6bc5b206545042e13faa5e9b4d9a0ec6b0ccf4929755c01025746b8ab4523c",
    "artifact_bytes": 970_993,
    "formal_steps": 32_900,
    "cell_count": 242_749,
    "literal_source_sha256": "sha256:64e28185c506821d8935bf79c12505ac74fb9f2f464cdefea1a18b81c87ced71",
    "program_sha256": "sha256:f6eacc1e90f63d90b2487d0230fc1a10ecdfe571124dbd317efc12f7dcb93821",
    "compile_report_sha256": "sha256:621cc77c50864b21c689e00df264f8edca779b148bd50564c59c529a6f62df09",
    "publication_count": 20,
    "accepted_count": 12,
    "rejected_count": 7,
    "dataset_count": 19,
}

from tom_learner052.oracle import build_promotion_result, canonical_bytes as oracle_bytes
from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tomagi.compiler import compile_file_result
from tomagi.core import run
from tomagi.formal import Limits, run_program, verify_program_hash
from tomagi.format import load
from tomagi.immutable_store import ImmutablePublicationStore, validate_plan
from tomagi.materialize import materialize_file, materialize_trace

FORMAL_LIMITS = Limits(
    max_steps=2_000_000,
    max_depth=256,
    max_collection_items=50_000,
    max_value_nodes=3_000_000,
    max_canonical_bytes=16_000_000,
)


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def tree_hash(root: Path) -> Mapping[str, Any]:
    digest = hashlib.sha256()
    count = 0
    byte_count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(rel).to_bytes(8, "big"))
        digest.update(rel)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        count += 1
        byte_count += len(data)
    return {"file_count": count, "bytes": byte_count, "sha256": "sha256:" + digest.hexdigest()}


def load_record(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    if not verify_hash(value):
        raise RuntimeError(f"{label} content hash mismatch")
    return value


def _compile_c() -> None:
    if C_EXE.is_file():
        return
    C_EXE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            os.environ.get("CC", "cc"), "-std=c99", "-O2", "-Wall", "-Wextra",
            "-Wpedantic", "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c",
            "-o", str(C_EXE),
        ],
        cwd=ROOT,
        check=True,
    )


def reconstruct_store(store: ImmutablePublicationStore, plan: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_plan(plan)
    descriptor = store.descriptor()
    commits: dict[str, dict[str, Any]] = {}
    for path in sorted((store.root / descriptor["head_namespace"]).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        commits[record["content_hash"]] = record
    chain: list[str] = []
    cursor: str | None = checked["terminal_head"]
    while cursor is not None:
        if cursor not in commits:
            raise RuntimeError(f"commit ancestry is missing {cursor}")
        commit = commits[cursor]
        chain.append(cursor)
        cursor = commit["parent_commit_hash"]
    chain.reverse()
    if len(chain) != EXPECTED["publication_count"]:
        raise RuntimeError("unexpected reconstructed commit count")
    for index, content_hash in enumerate(chain):
        if commits[content_hash]["sequence"] != index:
            raise RuntimeError("commit sequence differs from reconstructed ancestry")
    terminal = commits[chain[-1]]
    snapshot_path = store._path("snapshots", terminal["snapshot_hash"])
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    result = attach_hash({
        "schema": "TOM-LEARNER-PROMOTION-STORE-RECONSTRUCTION-0.5.2",
        "status": "pass",
        "terminal_head": chain[-1],
        "commit_count": len(chain),
        "session_count": len(snapshot["sessions"]),
        "accepted_definition_count": len(snapshot["accepted_definitions"]),
        "accepted_session_count": len(snapshot["accepted_sessions"]),
        "rejected_session_count": len(snapshot["rejected_sessions"]),
        "commit_chain": chain,
        "terminal_snapshot_hash": snapshot["content_hash"],
    })
    return result


def main() -> int:
    VAL.mkdir(parents=True, exist_ok=True)
    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    if len(seed) != 244 or seed.endswith((b"\r", b"\n")) or sha_bytes(seed) != "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5":
        raise RuntimeError("canonical seed identity mismatch")

    # Re-run the CODEX corrective handoff verifier before extending authority.
    handoff_output = VAL / "corrective_handoff_verification.json"
    subprocess.run(
        [
            os.environ.get("PYTHON", "python3"), "-m", "tom_learner05",
            "verify-corrective-handoff", ".", "--output", str(handoff_output),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src/python"), "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        stdout=subprocess.DEVNULL,
    )
    handoff = load_record(handoff_output, "corrective handoff verification")
    if not handoff.get("valid"):
        raise RuntimeError("CODEX corrective handoff verification failed")

    promotion_program = load_record(FORMAL_PROGRAM, "promotion formal program")
    learner_program = load_record(LEARNER_PROGRAM, "affine learner formal program")
    if not verify_program_hash(promotion_program, limits=FORMAL_LIMITS):
        raise RuntimeError("promotion formal program validation failed")
    if not verify_program_hash(learner_program, limits=FORMAL_LIMITS):
        raise RuntimeError("affine learner formal program validation failed")
    if promotion_program["content_hash"] != EXPECTED["promotion_program_content_hash"]:
        raise RuntimeError("unexpected promotion formal-program identity")
    if sha_path(FORMAL_PROGRAM) != EXPECTED["promotion_program_file_sha256"]:
        raise RuntimeError("unexpected promotion formal-program file bytes")
    if learner_program["content_hash"] != EXPECTED["learner_program_content_hash"]:
        raise RuntimeError("unexpected affine learner formal-program identity")

    dataset_paths = sorted(DATASET_DIR.glob("*.json"))
    datasets = [load_record(path, f"dataset {path.name}") for path in dataset_paths]
    context = load_record(CONTEXT, "promotion context")
    corrective = load_record(CORRECTIVE, "corrective handoff")
    registry = load_record(REGISTRY, "token registry")
    if len(datasets) != EXPECTED["dataset_count"]:
        raise RuntimeError("unexpected dataset count")

    learner_execution = run_program(learner_program, {"datasets": datasets}, limits=FORMAL_LIMITS)
    if learner_execution["content_hash"] != EXPECTED["learner_execution_content_hash"]:
        raise RuntimeError("recomputed learner execution identity mismatch")
    if learner_execution["value"]["content_hash"] != EXPECTED["learner_value_content_hash"]:
        raise RuntimeError("recomputed learner value identity mismatch")

    flattened = [promotion_program, learner_program, learner_execution, *datasets, context, corrective, registry]
    direct = run_program(promotion_program, {"promotion_inputs": flattened}, limits=FORMAL_LIMITS)
    if direct["steps"] != EXPECTED["formal_steps"]:
        raise RuntimeError("unexpected promotion formal step count")
    if direct["content_hash"] != EXPECTED["promotion_execution_content_hash"]:
        raise RuntimeError("unexpected promotion formal execution identity")
    if direct["value"]["content_hash"] != EXPECTED["promotion_value_content_hash"]:
        raise RuntimeError("unexpected promotion value identity")
    plan = direct["value"]["publication_plan"]
    if plan["content_hash"] != EXPECTED["publication_plan_content_hash"]:
        raise RuntimeError("unexpected publication plan identity")
    if direct["value"]["terminal_head"] != EXPECTED["terminal_head"]:
        raise RuntimeError("unexpected publication terminal head")
    validate_plan(plan)
    (VAL / "promotion_authority.direct_formal.json").write_bytes(canonical_bytes(direct) + b"\n")

    oracle = build_promotion_result(
        promotion_program, learner_program, learner_execution, datasets,
        context, corrective, registry,
    )
    if oracle != direct["value"]:
        raise RuntimeError("independent promotion oracle differs from formal authority")
    ORACLE.write_bytes(oracle_bytes(oracle) + b"\n")

    compilation = compile_file_result(SOURCE, PROGRAM)
    if compilation is None:
        raise RuntimeError("promotion authority did not compile under seeded mode")
    cell_count = len(compilation.program.cells)
    if cell_count != EXPECTED["cell_count"]:
        raise RuntimeError("unexpected promotion authority Cell48 count")
    program_hash = sha_path(PROGRAM)
    compile_report = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    report_hash = sha_path(compile_report)
    if sha_path(SOURCE) != EXPECTED["literal_source_sha256"]:
        raise RuntimeError("unexpected seeded literal-source bytes")
    if program_hash != EXPECTED["program_sha256"]:
        raise RuntimeError("unexpected seeded program bytes")
    if report_hash != EXPECTED["compile_report_sha256"]:
        raise RuntimeError("unexpected compile-report bytes")
    # The compilation result retains the complete 242,749-row crosswalk.  Drop
    # it before trace comparison so validation remains bounded in memory.
    del compilation
    gc.collect()

    data, python_state, python_trace, emit_records = materialize_file(PROGRAM, MATERIALIZED)
    if len(data) != EXPECTED["artifact_bytes"] or sha_bytes(data) != EXPECTED["artifact_sha256"]:
        raise RuntimeError("promotion materialized byte boundary mismatch")
    if data != canonical_bytes(direct) + b"\n":
        raise RuntimeError("seeded materialization differs from direct formal evaluation")

    _compile_c()
    with tempfile.TemporaryDirectory(prefix="tom-learner052-c-") as temp:
        c_trace_path = Path(temp) / "trace.json"
        with c_trace_path.open("wb") as stream:
            subprocess.run([str(C_EXE), str(PROGRAM), "--trace-json"], check=True, stdout=stream)
        c_record = json.loads(c_trace_path.read_text(encoding="utf-8"))
    state_dict = {name: getattr(python_state, name) for name in python_state.__dataclass_fields__}
    if c_record["state"] != state_dict or c_record["trace"] != python_trace:
        raise RuntimeError("Python/C promotion authority trace mismatch")
    c_data, c_emit = materialize_trace(load(PROGRAM), c_record["trace"])
    if c_data != data or len(c_emit) != len(emit_records):
        raise RuntimeError("Python/C promotion materialization mismatch")

    shutil.rmtree(STORE, ignore_errors=True)
    store = ImmutablePublicationStore.apply_plan(STORE, seed, plan)
    audit = store.audit_plan(plan, require_no_extra_records=True)
    if not audit.get("valid"):
        raise RuntimeError("promotion store audit failed")
    STORE_AUDIT.write_bytes(canonical_bytes(audit) + b"\n")
    reconstruction = reconstruct_store(store, plan)
    STORE_RECONSTRUCTION.write_bytes(canonical_bytes(reconstruction) + b"\n")
    if reconstruction["session_count"] != 19 or reconstruction["accepted_definition_count"] != 12 or reconstruction["rejected_session_count"] != 7:
        raise RuntimeError("promotion store reconstruction aggregate mismatch")

    trace_hash = sha_bytes(canonical_bytes(python_trace))
    emit_hash = sha_bytes(canonical_bytes([record.as_record() for record in emit_records]))
    proof = attach_hash({
        "schema": "TOM-LEARNER-PROMOTION-AUTHORITY-PROOF-0.5.2",
        "release": "0.5.2",
        "status": "pass",
        "canonical_seed_sha256": sha_bytes(seed),
        "corrective_handoff_verification_hash": handoff["content_hash"],
        "promotion_formal_program_hash": promotion_program["content_hash"],
        "affine_learner_formal_program_hash": learner_program["content_hash"],
        "affine_learner_execution_hash": learner_execution["content_hash"],
        "direct_promotion_execution_hash": direct["content_hash"],
        "promotion_value_hash": direct["value"]["content_hash"],
        "publication_plan_hash": plan["content_hash"],
        "terminal_head": direct["value"]["terminal_head"],
        "literal_source_sha256": sha_path(SOURCE),
        "program_sha256": program_hash,
        "compile_report_sha256": report_hash,
        "program_bytes": PROGRAM.stat().st_size,
        "cell_count": cell_count,
        "execution_steps": len(python_trace),
        "emit_records": len(emit_records),
        "trace_sha256": trace_hash,
        "emit_records_sha256": emit_hash,
        "artifact_bytes": len(data),
        "artifact_sha256": sha_bytes(data),
        "seeded_materialization_equals_direct_formal_result": True,
        "independent_oracle_equals_formal_value": True,
        "python_c_state_equal": True,
        "python_c_complete_trace_equal": True,
        "python_c_materialized_bytes_equal": True,
        "publication_count": len(plan["publications"]),
        "accepted_count": direct["value"]["accepted_count"],
        "rejected_count": direct["value"]["rejected_count"],
        "planned_unique_records": audit["planned_records"],
        "store_audit_hash": audit["content_hash"],
        "store_reconstruction_hash": reconstruction["content_hash"],
        "store_tree": tree_hash(STORE),
        "authority_boundary": "formal definitions decide promotion/evidence semantics; host code only verifies, persists immutable addressed records, and performs CAS HEAD publication",
    })
    PROOF.write_bytes(canonical_bytes(proof) + b"\n")
    print(json.dumps({
        "status": "pass",
        "cells": proof["cell_count"],
        "steps": proof["execution_steps"],
        "artifact_sha256": proof["artifact_sha256"],
        "plan_hash": proof["publication_plan_hash"],
        "terminal_head": proof["terminal_head"],
        "store_tree_sha256": proof["store_tree"]["sha256"],
        "proof_hash": proof["content_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
