from __future__ import annotations

"""Build the 0.5.1 corrective handoff document through literal TOMAGI bytes.

The authored Markdown is packed into the seeded definition source only when the
explicit refresh environment variable is set.  Normal runs consume that static
source and use only the generic compiler, TOMAGI runtime, trace capture, and byte
materializer.
"""

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tomagi.compiler import compile_file_result
from tomagi.format import load
from tomagi.materialize import materialize_file, materialize_trace


DOC = ROOT / "docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md"
OVERLAY = ROOT / "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"
SOURCE = ROOT / "examples/learner05/corrective_handoff_0_5_1.literal.json"
PROGRAM = ROOT / "examples/learner05/corrective_handoff_0_5_1.tmg"
MATERIALIZED = ROOT / "TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.materialized.md"
PY_TRACE = ROOT / "validation/learner05/corrective_handoff_0_5_1.python.trace.json"
C_TRACE = ROOT / "validation/learner05/corrective_handoff_0_5_1.c.trace.json"
EMIT_RECORDS = ROOT / "validation/learner05/corrective_handoff_0_5_1.emit_records.json"
PROOF = ROOT / "validation/learner05/corrective_handoff_0_5_1.proof.json"
C_EXE = ROOT / (
    "build/tomagi-c-corrective-handoff-wsl"
    if os.name == "nt"
    else "build/tomagi-c-corrective-handoff"
)

SEED_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
OVERLAY_RELATIVE_PATH = "sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json"
REFRESH_VARIABLE = "TOM_CORRECTIVE_REFRESH_HANDOFF_SOURCE"


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


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
        subprocess.run([
            "wsl.exe", "cc",
            "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-I" + _wsl_path(ROOT / "src/c"),
            _wsl_path(ROOT / "src/c/tomagi.c"),
            _wsl_path(ROOT / "src/c/tomagi_cli.c"),
            "-o", _wsl_path(C_EXE),
        ], check=True)
    else:
        subprocess.run([
            os.environ.get("CC", "cc"),
            "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c",
            "-o", str(C_EXE),
        ], cwd=ROOT, check=True)


def _c_trace_command() -> list[str]:
    if os.name == "nt":
        return ["wsl.exe", _wsl_path(C_EXE), _wsl_path(PROGRAM), "--trace-json"]
    return [str(C_EXE), str(PROGRAM), "--trace-json"]


def _load_overlay() -> dict[str, Any]:
    value = json.loads(OVERLAY.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("corrective overlay must be a JSON object")
    record = dict(value)
    if record.get("schema") != "TOM-CORRECTIVE-HANDOFF-0.5.1":
        raise RuntimeError("unexpected corrective overlay schema")
    if not verify_hash(record):
        raise RuntimeError("corrective overlay content hash mismatch")
    if record.get("canonical_seed_sha256") != "sha256:" + SEED_SHA256:
        raise RuntimeError("corrective overlay does not bind the canonical seed")
    return record


def definition(
    ident: str,
    kind: str,
    domain: str,
    codomain: str,
    dependencies: list[str],
    phase: str,
    order: int,
    operation: str,
    parameters: dict[str, Any],
    *,
    overlay: Mapping[str, Any],
    tokens: list[str] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": ident,
        "kind": kind,
        "domain": domain,
        "codomain": codomain,
        "dependencies": dependencies,
        "phase": phase,
        "order": order,
        "operation": {"op": operation},
        "parameters": parameters,
        "limits": {},
        "provenance": {
            "source": DOC.relative_to(ROOT).as_posix(),
            "role": "0.5.1 corrective handoff document byte artifact",
            "corrective_overlay": OVERLAY_RELATIVE_PATH,
            "corrective_overlay_hash": overlay["content_hash"],
            "base_handoff_hash": overlay["base_handoff_hash"],
        },
    }
    if tokens:
        value["seed_tokens"] = tokens
    return attach_hash(value)


def source_record(data: bytes, overlay: Mapping[str, Any]) -> dict[str, Any]:
    if not data:
        raise RuntimeError("corrective handoff document must not be empty")
    count = math.ceil(len(data) / 4)
    width = max(1, len(str(count - 1)))
    entry = f"cell:corrective-handoff-0-5-1:{0:0{width}d}"
    digest = sha_bytes(data)

    def make(
        ident: str,
        kind: str,
        domain: str,
        codomain: str,
        dependencies: list[str],
        phase: str,
        order: int,
        operation: str,
        parameters: dict[str, Any],
        *,
        tokens: list[str] | None = None,
    ) -> dict[str, Any]:
        return definition(
            ident,
            kind,
            domain,
            codomain,
            dependencies,
            phase,
            order,
            operation,
            parameters,
            overlay=overlay,
            tokens=tokens,
        )

    definitions = [
        make(
            "tom:seed", "canonical-seed", "none", "bytes", [], "parse", 0,
            "seed.bytes", {}, tokens=["TOM1"],
        ),
        make(
            "tom:tokens", "seed-parse", "bytes", "record", ["tom:seed"],
            "resolve", 0, "seed.tokens", {}, tokens=["TopologicalOpenModular"],
        ),
        make(
            "handoff:bytes", "literal-corrective-handoff-document", "seed-record",
            "bytes", ["tom:tokens"], "construct", 0, "literal", {
                "result_type": "bytes",
                "value": {
                    "encoding": "base64",
                    "data": base64.b64encode(data).decode("ascii"),
                },
            }, tokens=["Pi"],
        ),
        make(
            "handoff:expected-hash", "literal-hash", "seed-record", "string",
            ["tom:tokens"], "construct", 1, "literal", {
                "result_type": "string", "value": digest,
            },
        ),
        make(
            "handoff:state", "initial-state", "seed-record", "state64",
            ["tom:tokens"], "construct", 2, "state64.construct", {"fields": {}},
            tokens=["lineage"],
        ),
        make(
            "handoff:actual-hash", "computed-hash", "bytes", "string",
            ["handoff:bytes"], "transform", 0, "hash.sha256", {"prefix": True},
        ),
        make(
            "handoff:emit", "byte-emission", "bytes", "cell_graph",
            ["handoff:bytes"], "transform", 1, "emit.graph", {
                "id_prefix": "cell:corrective-handoff-0-5-1",
                "key_base": {"rho": 0, "theta": 0, "tick": 0, "phi": 0},
                "key_field": "rho",
                "chunk_bytes": 4,
                "byte_order": "little",
                "halt_last": True,
                "aux_base": 0,
            }, tokens=["transition"],
        ),
        make(
            "handoff:guard", "hash-guard", "hash-pair", "bool",
            ["handoff:actual-hash", "handoff:expected-hash"], "guard", 0,
            "assert.equal", {}, tokens=["guard"],
        ),
        make(
            "program:corrective-handoff-0-5-1", "artifact-program",
            "state-graph-guard", "program",
            ["handoff:state", "handoff:emit", "handoff:guard"],
            "lineage", 0, "program.construct", {
                "entry": entry,
                "seed": 0,
                "default_ticks": count,
                "flags": 0,
                "emit_bytes": True,
            }, tokens=["event", "transition", "lineage"],
        ),
    ]
    return {
        "$schema": "../../spec/tom_seeded_program.schema.json",
        "tomagi_version": "1.0.0",
        "compilation_profile": "TOM-SEEDED-COMPILATION-1.0",
        "title": "TOM WQK 0.5.1 corrective handoff literal document artifact",
        "seed_genome": {
            "path": "../../TOM_seed_genome_2026-09-01.txt",
            "bytes": 244,
            "sha256": SEED_SHA256,
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
            "token_registry": "../../spec/tom_seed_token_registry_1_0.json",
        },
        "root_definition": "program:corrective-handoff-0-5-1",
        "budgets": {
            "max_definitions": 16,
            "max_cells": count,
            "max_output_bytes": len(data),
            "max_sequence_items": 64,
            "max_repeat": 1,
            "max_expression_depth": 16,
            "max_expression_nodes": 4096,
            "max_string_bytes": 4096,
        },
        "definitions": definitions,
    }


def _validate_source_overlay_binding(
    source: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> None:
    definitions = source.get("definitions")
    if not isinstance(definitions, list) or not definitions:
        raise RuntimeError("corrective handoff source has no definitions")
    for item in definitions:
        if not isinstance(item, Mapping):
            raise RuntimeError("corrective handoff source contains a non-record definition")
        provenance = item.get("provenance")
        if not isinstance(provenance, Mapping):
            raise RuntimeError("corrective handoff definition has no provenance record")
        if provenance.get("corrective_overlay") != OVERLAY_RELATIVE_PATH:
            raise RuntimeError("corrective handoff definition names the wrong overlay")
        if provenance.get("corrective_overlay_hash") != overlay["content_hash"]:
            raise RuntimeError("corrective handoff definition has a stale overlay hash")
        if provenance.get("base_handoff_hash") != overlay["base_handoff_hash"]:
            raise RuntimeError("corrective handoff definition has a stale base handoff hash")


def main() -> int:
    document_bytes = DOC.read_bytes()
    overlay = _load_overlay()
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    PROOF.parent.mkdir(parents=True, exist_ok=True)

    if os.environ.get(REFRESH_VARIABLE) == "1":
        SOURCE.write_text(
            json.dumps(
                source_record(document_bytes, overlay),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
    if not SOURCE.is_file():
        raise FileNotFoundError(
            f"missing static corrective handoff source: {SOURCE}; set "
            f"{REFRESH_VARIABLE}=1 only to refresh it from the authored document"
        )

    source_value = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(source_value, Mapping):
        raise RuntimeError("corrective handoff seeded source must be an object")
    _validate_source_overlay_binding(source_value, overlay)

    result = compile_file_result(SOURCE, PROGRAM)
    if result is None:
        raise RuntimeError("corrective handoff did not compile under the seeded profile")
    sidecar = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    first_program = PROGRAM.read_bytes()
    first_report = sidecar.read_bytes()
    second = compile_file_result(SOURCE, PROGRAM)
    if second is None:
        raise RuntimeError("corrective handoff second compile left the seeded profile")
    if PROGRAM.read_bytes() != first_program or sidecar.read_bytes() != first_report:
        raise RuntimeError("corrective handoff compilation is not byte-stable in place")

    data, python_state, python_trace, emit_records = materialize_file(
        PROGRAM, MATERIALIZED
    )
    if data != document_bytes:
        raise RuntimeError("materialized corrective handoff differs from authored bytes")
    python_record = {
        "state": {
            name: getattr(python_state, name)
            for name in python_state.__dataclass_fields__
        },
        "trace": python_trace,
    }
    PY_TRACE.write_bytes(canonical_bytes(python_record) + b"\n")
    python_emit = [record.as_record() for record in emit_records]
    EMIT_RECORDS.write_bytes(canonical_bytes(python_emit) + b"\n")

    _compile_c()
    c_record = json.loads(
        subprocess.check_output(_c_trace_command(), cwd=ROOT).decode("utf-8")
    )
    C_TRACE.write_bytes(canonical_bytes(c_record) + b"\n")
    if c_record != python_record:
        raise RuntimeError("corrective handoff Python and C traces differ")
    c_data, c_emit_records = materialize_trace(load(PROGRAM), c_record["trace"])
    c_emit = [record.as_record() for record in c_emit_records]
    if c_data != data or c_emit != python_emit:
        raise RuntimeError("corrective handoff Python and C EMIT bytes differ")

    proof = attach_hash({
        "schema": "TOM-WQK-0.5.1-CORRECTIVE-HANDOFF-ARTIFACT-PROOF-1.0",
        "status": "pass",
        "release": "0.5.1-corrective-handoff",
        "corrective_overlay": {
            "path": OVERLAY.relative_to(ROOT).as_posix(),
            "bytes": OVERLAY.stat().st_size,
            "file_sha256": sha_path(OVERLAY),
            "content_hash": overlay["content_hash"],
            "base_handoff_hash": overlay["base_handoff_hash"],
            "base_world_hash": overlay["base_world_hash"],
        },
        "authored_document": {
            "path": DOC.relative_to(ROOT).as_posix(),
            "bytes": len(document_bytes),
            "sha256": sha_bytes(document_bytes),
        },
        "literal_definition_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha_path(SOURCE),
            "definitions": len(result.definition_order),
            "refresh_environment_variable": REFRESH_VARIABLE,
        },
        "compiled_program": {
            "path": PROGRAM.relative_to(ROOT).as_posix(),
            "bytes": len(first_program),
            "sha256": sha_bytes(first_program),
            "cells": len(result.program.cells),
            "cell_bytes": 48,
            "tomagi_abi": "1.0",
            "compile_report_path": sidecar.relative_to(ROOT).as_posix(),
            "compile_report_bytes": len(first_report),
            "compile_report_sha256": sha_bytes(first_report),
            "in_place_recompile_equal": True,
        },
        "execution": {
            "steps": len(python_trace),
            "emit_records": len(python_emit),
            "python_trace_path": PY_TRACE.relative_to(ROOT).as_posix(),
            "python_trace_sha256": sha_path(PY_TRACE),
            "c_trace_path": C_TRACE.relative_to(ROOT).as_posix(),
            "c_trace_sha256": sha_path(C_TRACE),
            "python_c_full_trace_equal": True,
            "emit_records_path": EMIT_RECORDS.relative_to(ROOT).as_posix(),
            "emit_records_sha256": sha_path(EMIT_RECORDS),
            "python_c_emit_equal": True,
        },
        "materialized_artifact": {
            "path": MATERIALIZED.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha_bytes(data),
            "matches_authored_document": True,
        },
        "causal_chain": [
            OVERLAY_RELATIVE_PATH,
            DOC.relative_to(ROOT).as_posix(),
            SOURCE.relative_to(ROOT).as_posix(),
            PROGRAM.relative_to(ROOT).as_posix(),
            PY_TRACE.relative_to(ROOT).as_posix(),
            EMIT_RECORDS.relative_to(ROOT).as_posix(),
            MATERIALIZED.relative_to(ROOT).as_posix(),
        ],
        "claim_boundary": (
            "byte-for-byte seeded compilation, TOMAGI replay, authenticated EMIT "
            "materialization, and Python/C equality for the authored corrective handoff"
        ),
    })
    PROOF.write_bytes(canonical_bytes(proof) + b"\n")
    print(json.dumps({
        "status": proof["status"],
        "proof_hash": proof["content_hash"],
        "overlay_hash": overlay["content_hash"],
        "program_sha256": sha_bytes(first_program),
        "materialized_sha256": sha_bytes(data),
        "cells": len(result.program.cells),
        "steps": len(python_trace),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
