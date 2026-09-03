from __future__ import annotations

"""Materialize the authored WQK 0.6 validation handoff through TOMAGI.

The handoff bytes live only in the authored Markdown/literal definition.  This
host tool supplies generic hashing, compilation, execution, trace capture, and
authenticated byte materialization.
"""

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import attach_hash, canonical_bytes
from tomagi.compiler import compile_file_result
from tomagi.format import load
from tomagi.materialize import materialize_file, materialize_trace

DOC = ROOT / "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.md"
BASE = ROOT / "examples/learner06"
VAL = ROOT / "validation/learner06"
SOURCE = BASE / "kernel06_validation_handoff.literal.json"
PROGRAM = BASE / "kernel06_validation_handoff.tmg"
MATERIALIZED = VAL / "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.materialized.md"
PY_TRACE = VAL / "kernel06_validation_handoff.python.trace.json"
C_TRACE = VAL / "kernel06_validation_handoff.c.trace.json"
EMIT_RECORDS = VAL / "kernel06_validation_handoff.emit_records.json"
PROOF = VAL / "kernel06_validation_handoff.proof.json"
C_EXE = ROOT / "build/tomagi-c-learner06"

SEED_HASH = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


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
            "source": "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.md",
            "causal_role": "authored literal handoff bytes",
            "date": "2026-09-03",
        },
    }
    if tokens:
        value["seed_tokens"] = tokens
    return attach_hash(value)


def source_record(data: bytes) -> dict[str, Any]:
    count = math.ceil(len(data) / 4)
    width = max(1, len(str(count - 1)))
    entry = f"cell:kernel06-handoff:{0:0{width}d}"
    digest = sha(data)
    definitions = [
        definition(
            "tom:seed", "canonical-seed", "none", "bytes", [], "parse", 0,
            "seed.bytes", {}, tokens=["TOM1"],
        ),
        definition(
            "tom:tokens", "seed-parse", "bytes", "record", ["tom:seed"],
            "resolve", 0, "seed.tokens", {}, tokens=["TopologicalOpenModular"],
        ),
        definition(
            "handoff:bytes", "literal-validation-handoff", "seed-record", "bytes",
            ["tom:tokens"], "construct", 0, "literal",
            {
                "result_type": "bytes",
                "value": {
                    "encoding": "base64",
                    "data": base64.b64encode(data).decode("ascii"),
                },
            },
            tokens=["Pi"],
        ),
        definition(
            "handoff:expected-hash", "literal-hash", "seed-record", "string",
            ["tom:tokens"], "construct", 1, "literal",
            {"result_type": "string", "value": digest},
        ),
        definition(
            "handoff:state", "initial-state", "seed-record", "state64",
            ["tom:tokens"], "construct", 2, "state64.construct",
            {"fields": {"lineage": "0x48303630"}}, tokens=["lineage"],
        ),
        definition(
            "handoff:actual-hash", "computed-hash", "bytes", "string",
            ["handoff:bytes"], "transform", 0, "hash.sha256", {"prefix": True},
        ),
        definition(
            "handoff:emit", "byte-emission", "bytes", "cell_graph",
            ["handoff:bytes"], "transform", 1, "emit.graph",
            {
                "id_prefix": "cell:kernel06-handoff",
                "key_base": {"rho": 800000, "theta": 0, "tick": 0, "phi": 0},
                "key_field": "rho",
                "chunk_bytes": 4,
                "byte_order": "little",
                "halt_last": True,
                "aux_base": "0x48360000",
            },
            tokens=["transition"],
        ),
        definition(
            "handoff:guard", "hash-guard", "hash-pair", "bool",
            ["handoff:actual-hash", "handoff:expected-hash"], "guard", 0,
            "assert.equal", {}, tokens=["guard"],
        ),
        definition(
            "program:kernel06-handoff", "artifact-program", "state-graph-guard",
            "program", ["handoff:state", "handoff:emit", "handoff:guard"],
            "lineage", 0, "program.construct",
            {
                "entry": entry,
                "seed": "0x48303630",
                "default_ticks": count,
                "flags": 0,
                "emit_bytes": True,
            },
            tokens=["event", "transition", "lineage"],
        ),
    ]
    return {
        "$schema": "../../spec/tom_seeded_program.schema.json",
        "tomagi_version": "1.0.0",
        "compilation_profile": "TOM-SEEDED-COMPILATION-1.0",
        "title": "CODEX WQK 0.6 validation handoff artifact",
        "seed_genome": {
            "path": "../../TOM_seed_genome_2026-09-01.txt",
            "bytes": 244,
            "sha256": SEED_HASH,
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
            "token_registry": "../../spec/tom_seed_token_registry_1_0.json",
        },
        "root_definition": "program:kernel06-handoff",
        "budgets": {
            "max_definitions": 16,
            "max_cells": count,
            "max_output_bytes": len(data),
            "max_sequence_items": 64,
            "max_repeat": 1,
            "max_expression_depth": 16,
            "max_expression_nodes": 2048,
            "max_string_bytes": 2048,
        },
        "definitions": definitions,
    }


def compile_c() -> None:
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


def main() -> None:
    source_bytes = DOC.read_bytes()
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    VAL.mkdir(parents=True, exist_ok=True)
    if os.environ.get("TOM_LEARNER06_REFRESH_HANDOFF_SOURCE") == "1":
        SOURCE.write_text(
            json.dumps(source_record(source_bytes), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not SOURCE.is_file():
        raise FileNotFoundError(f"missing literal handoff definition: {SOURCE}")

    result = compile_file_result(SOURCE, PROGRAM)
    if result is None:
        raise RuntimeError("WQK 0.6 validation handoff did not compile under seeded profile")
    data, state, trace, records = materialize_file(PROGRAM, MATERIALIZED)
    if data != source_bytes:
        raise RuntimeError("materialized validation handoff differs from authored bytes")

    state_record = {name: getattr(state, name) for name in state.__dataclass_fields__}
    py_record = {"state": state_record, "trace": trace}
    PY_TRACE.write_bytes(canonical_bytes(py_record) + b"\n")
    EMIT_RECORDS.write_bytes(canonical_bytes([record.as_record() for record in records]) + b"\n")

    compile_c()
    c_record = json.loads(
        subprocess.check_output([str(C_EXE), str(PROGRAM), "--trace-json"], cwd=ROOT)
    )
    C_TRACE.write_bytes(canonical_bytes(c_record) + b"\n")
    if c_record != py_record:
        raise RuntimeError("validation-handoff Python and C traces differ")
    c_data, c_emit = materialize_trace(load(PROGRAM), c_record["trace"])
    if c_data != data:
        raise RuntimeError("validation-handoff C and Python bytes differ")

    sidecar = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    proof = attach_hash({
        "schema": "TOM-WQK-0.6-CODEX-VALIDATION-HANDOFF-PROOF-1.0",
        "status": "pass",
        "canonical_seed_sha256": "sha256:" + SEED_HASH,
        "literal_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "bytes": SOURCE.stat().st_size,
            "sha256": sha(SOURCE.read_bytes()),
        },
        "compile_sidecar": {
            "path": sidecar.relative_to(ROOT).as_posix(),
            "bytes": sidecar.stat().st_size,
            "sha256": sha(sidecar.read_bytes()),
        },
        "program": {
            "path": PROGRAM.relative_to(ROOT).as_posix(),
            "bytes": PROGRAM.stat().st_size,
            "sha256": sha(PROGRAM.read_bytes()),
            "cells": len(result.program.cells),
        },
        "execution": {
            "steps": len(trace),
            "emit_records": len(records),
            "python_c_full_trace_equal": True,
            "python_c_emit_sequence_equal": [record.as_record() for record in records]
            == [record.as_record() for record in c_emit],
        },
        "artifact": {
            "path": MATERIALIZED.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha(data),
            "matches_authored_document": True,
        },
    })
    PROOF.write_bytes(canonical_bytes(proof) + b"\n")
    print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
