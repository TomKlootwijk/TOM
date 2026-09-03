from __future__ import annotations

"""Build and independently validate the corrective literal learner authority.

The domain algorithm is the content-addressed formal JSON program.  This tool
only performs generic compilation/execution/trace capture plus comparison with
the already shipped independent reference oracle.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/learner05/learner05_formal_authority.literal.json"
FORMAL_PROGRAM = ROOT / "examples/learner05/learner05_affine_authority.formal.json"
PROGRAM = ROOT / "examples/learner05/learner05_formal_authority.tmg"
MATERIALIZED = ROOT / "validation/learner05/learner05_formal_authority.materialized.json"
PROOF = ROOT / "validation/learner05/learner05_formal_authority.proof.json"
C_EXE = ROOT / "build/tomagi-c-formal"

from tom_learner05.baseline import trusted_affine_learning_baseline
from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tomagi.compiler import compile_file_result
from tomagi.formal import Limits, content_address, evaluate, verify_program_hash
from tomagi.format import load
from tomagi.materialize import materialize_file, materialize_trace

EXPECTED_SEED_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
EXPECTED_FORMAL_PROGRAM_HASH = "sha256:dd710388744a71861c90c15ef63bd85411f0652a2077f6f9ef9421997d626b28"
EXPECTED_VALUE_HASH = "sha256:14c5e5e0dd4bc49d40eb8b8f3d86fbdb7bad4d86c872dbeea9799a5aeb92dd12"
EXPECTED_ARTIFACT_SHA256 = "sha256:dd9a0c20c8f721c764580f6655bb509001a7ef59000d0cd1bd5826971b72cb82"
EXPECTED_STEPS = 131_478
EXPECTED_CELLS = 19_540

FORMAL_LIMITS = Limits(
    max_steps=2_000_000,
    max_depth=192,
    max_collection_items=20_000,
    max_value_nodes=2_000_000,
    max_canonical_bytes=8_000_000,
)


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def trace_hash(record: Mapping[str, Any]) -> str:
    return sha_bytes(canonical_bytes(record))


def _wsl_path(path: Path) -> str:
    resolved = str(path.resolve()).replace("\\", "/")
    if len(resolved) < 3 or resolved[1:3] != ":/":
        raise RuntimeError(f"cannot map Windows path into WSL: {resolved}")
    return f"/mnt/{resolved[0].lower()}/{resolved[3:]}"


def _compile_c() -> None:
    if C_EXE.is_file():
        return
    C_EXE.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        command = [
            "wsl.exe", "cc",
            "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-I" + _wsl_path(ROOT / "src/c"),
            _wsl_path(ROOT / "src/c/tomagi.c"),
            _wsl_path(ROOT / "src/c/tomagi_cli.c"),
            "-o", _wsl_path(C_EXE),
        ]
        subprocess.run(command, check=True)
    else:
        subprocess.run(
            [
                os.environ.get("CC", "cc"),
                "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c",
                "-o", str(C_EXE),
            ],
            cwd=ROOT,
            check=True,
        )


def _c_trace_command() -> list[str]:
    if os.name == "nt":
        return ["wsl.exe", _wsl_path(C_EXE), _wsl_path(PROGRAM), "--trace-json"]
    return [str(C_EXE), str(PROGRAM), "--trace-json"]


def _selected_coefficients(semantic: Mapping[str, Any]) -> Any:
    return semantic.get("selected_coefficients")


def _validate_semantics(result: Mapping[str, Any]) -> dict[str, Any]:
    value = result.get("value")
    if not isinstance(value, Mapping):
        raise RuntimeError("formal result has no value record")
    if not verify_hash(dict(value)):
        raise RuntimeError("formal authority value content hash mismatch")
    rows = value.get("results")
    if not isinstance(rows, list) or len(rows) != 19:
        raise RuntimeError("formal authority did not return 19 result rows")
    by_id = {str(row["dataset_id"]): row for row in rows}
    if len(by_id) != 19:
        raise RuntimeError("formal authority returned duplicate dataset IDs")

    coefficient_errors = 0
    semantic_mismatches: list[str] = []
    relation_checks = 0
    dataset_paths = sorted((ROOT / "examples/learner05/datasets").glob("*.json"))
    for path in dataset_paths:
        dataset = json.loads(path.read_text(encoding="utf-8"))
        baseline = trusted_affine_learning_baseline(dataset)["semantic"]
        row = by_id.get(str(dataset["id"]))
        if row is None:
            semantic_mismatches.append(f"{dataset['id']}: missing result")
            continue
        expected = {
            "accepted": baseline["accepted"],
            "candidate_count": baseline["candidate_count"],
            "exact_training_candidate_count": baseline["exact_training_candidate_count"],
            "selected_coefficients": _selected_coefficients(baseline),
            "split_ids": baseline["splits"],
            "contradiction_count": len(baseline["contradictions"]),
        }
        actual = {name: row.get(name) for name in expected}
        if actual != expected:
            semantic_mismatches.append(f"{dataset['id']}: independent baseline mismatch")
        coefficient_errors += int(actual["selected_coefficients"] != expected["selected_coefficients"])
        if not verify_hash(dict(row)):
            semantic_mismatches.append(f"{dataset['id']}: row content hash mismatch")

        relation = row.get("relation_definition")
        if row.get("accepted"):
            if not isinstance(relation, Mapping) or not verify_hash(dict(relation)):
                semantic_mismatches.append(f"{dataset['id']}: missing/invalid accepted relation")
                continue
            for observation in dataset["observations"]:
                residual = evaluate(
                    relation["expression"],
                    {
                        dataset["domain"]["input"]: observation["t"],
                        dataset["domain"]["output"]: observation["y"],
                    },
                    limits=FORMAL_LIMITS,
                )
                if residual != {"num": 0, "den": 1}:
                    semantic_mismatches.append(
                        f"{dataset['id']}: accepted SDF0 relation has nonzero residual"
                    )
                    break
            relation_checks += 1
        elif relation is not None:
            semantic_mismatches.append(f"{dataset['id']}: rejected row emitted a relation")

    if semantic_mismatches:
        raise RuntimeError("; ".join(semantic_mismatches))
    if value.get("accepted_count") != 12 or value.get("rejected_count") != 7:
        raise RuntimeError("formal authority benchmark aggregate mismatch")
    return {
        "dataset_count": len(dataset_paths),
        "independent_baseline_rows_equal": len(dataset_paths),
        "accepted": value["accepted_count"],
        "rejected": value["rejected_count"],
        "coefficient_errors": coefficient_errors,
        "addressed_sdf0_relations_executed": relation_checks,
    }


def main() -> int:
    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    if len(seed) != 244 or seed.endswith((b"\r", b"\n")) or hashlib.sha256(seed).hexdigest() != EXPECTED_SEED_SHA256:
        raise RuntimeError("canonical seed identity mismatch")

    formal_program = json.loads(FORMAL_PROGRAM.read_text(encoding="utf-8"))
    if not verify_program_hash(formal_program, limits=FORMAL_LIMITS):
        raise RuntimeError("formal learner program content hash mismatch")
    if formal_program["content_hash"] != EXPECTED_FORMAL_PROGRAM_HASH:
        raise RuntimeError("unexpected formal learner program identity")

    result = compile_file_result(SOURCE, PROGRAM)
    if result is None:
        raise RuntimeError("formal authority was not compiled under the seeded profile")
    if len(result.program.cells) != EXPECTED_CELLS:
        raise RuntimeError("unexpected formal authority Cell48 count")
    first_program_hash = sha_path(PROGRAM)
    compile_report_path = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    first_report_hash = sha_path(compile_report_path)
    # A same-path rebuild proves that no prior generated state is required.
    compile_file_result(SOURCE, PROGRAM)
    if sha_path(PROGRAM) != first_program_hash or sha_path(compile_report_path) != first_report_hash:
        raise RuntimeError("seeded compilation is not byte-stable in place")

    data, python_state, python_trace, emit_records = materialize_file(PROGRAM, MATERIALIZED)
    if len(data) != 78_160 or sha_bytes(data) != EXPECTED_ARTIFACT_SHA256:
        raise RuntimeError("formal authority materialized byte boundary mismatch")
    formal_result = json.loads(data.decode("utf-8"))
    if not verify_hash(formal_result):
        raise RuntimeError("formal result wrapper content hash mismatch")
    if formal_result.get("program_hash") != EXPECTED_FORMAL_PROGRAM_HASH:
        raise RuntimeError("formal result does not bind the authority program")
    if formal_result.get("steps") != EXPECTED_STEPS:
        raise RuntimeError("formal result step count mismatch")
    if formal_result.get("value", {}).get("content_hash") != EXPECTED_VALUE_HASH:
        raise RuntimeError("formal result value hash mismatch")
    semantic = _validate_semantics(formal_result)

    _compile_c()
    c_record = json.loads(
        subprocess.check_output(_c_trace_command(), cwd=ROOT).decode("utf-8")
    )
    python_record = {
        "state": {
            name: getattr(python_state, name)
            for name in python_state.__dataclass_fields__
        },
        "trace": python_trace,
    }
    if c_record != python_record:
        raise RuntimeError("Python and C formal-authority traces differ")
    c_data, c_emit = materialize_trace(load(PROGRAM), c_record["trace"])
    if c_data != data or len(c_emit) != len(emit_records):
        raise RuntimeError("Python and C EMIT materialization differs")

    compile_report = json.loads(compile_report_path.read_text(encoding="utf-8"))
    resolved = compile_report.get("resolved_sources", [])
    if not isinstance(resolved, list) or len(resolved) != 20:
        raise RuntimeError("compile report does not bind all formal/dataset sources")
    emit_record_values = [record.as_record() for record in emit_records]
    proof = attach_hash({
        "schema": "TOM-WQK-0.5.1-FORMAL-AUTHORITY-PROOF-1.0",
        "status": "pass",
        "canonical_seed": {
            "bytes": len(seed),
            "sha256": "sha256:" + EXPECTED_SEED_SHA256,
        },
        "literal_definition_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha_path(SOURCE),
            "definitions": len(result.definition_order),
            "resolved_literal_sources": resolved,
        },
        "formal_program": {
            "path": FORMAL_PROGRAM.relative_to(ROOT).as_posix(),
            "bytes": FORMAL_PROGRAM.stat().st_size,
            "file_sha256": sha_path(FORMAL_PROGRAM),
            "content_hash": formal_program["content_hash"],
        },
        "compiled_program": {
            "path": PROGRAM.relative_to(ROOT).as_posix(),
            "bytes": PROGRAM.stat().st_size,
            "sha256": first_program_hash,
            "cells": len(result.program.cells),
            "cell_bytes": 48,
            "abi_opcodes": 16,
            "compile_report_path": compile_report_path.relative_to(ROOT).as_posix(),
            "compile_report_sha256": first_report_hash,
            "in_place_recompile_equal": True,
        },
        "formal_evaluation": {
            "steps": formal_result["steps"],
            "inputs_hash": formal_result["inputs_hash"],
            "result_content_hash": formal_result["content_hash"],
            "value_content_hash": formal_result["value"]["content_hash"],
        },
        "execution": {
            "steps": len(python_trace),
            "python_trace_sha256": trace_hash(python_record),
            "c_trace_sha256": trace_hash(c_record),
            "python_c_full_trace_equal": True,
            "emit_records": len(emit_records),
            "emit_records_sha256": sha_bytes(canonical_bytes(emit_record_values)),
            "python_c_emit_equal": True,
        },
        "materialized_artifact": {
            "path": MATERIALIZED.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha_bytes(data),
            "canonical_json_plus_lf": data == canonical_bytes(formal_result) + b"\n",
        },
        "semantic_oracle": semantic,
        "claim_boundary": (
            "exact finite affine induction over 19 literal rational datasets; "
            "no claim of general learning, perception, planning, GPU learner execution, or AGI"
        ),
    })
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_bytes(canonical_bytes(proof) + b"\n")
    print(json.dumps({
        "status": proof["status"],
        "proof_hash": proof["content_hash"],
        "program_sha256": first_program_hash,
        "materialized_sha256": sha_bytes(data),
        "cells": len(result.program.cells),
        "formal_steps": formal_result["steps"],
        **semantic,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
