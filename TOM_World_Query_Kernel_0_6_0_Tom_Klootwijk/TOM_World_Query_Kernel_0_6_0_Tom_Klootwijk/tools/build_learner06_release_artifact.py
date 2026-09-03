from __future__ import annotations

"""Compile and replay the literal WQK 0.6 release document through TOMAGI.

The Markdown bytes are definition data.  This tool supplies only generic
hashing, strict seeded compilation, execution, trace capture, replay-authenticated
materialization, and cross-backend comparison.
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

DOC = ROOT / "TOM_WORLD_QUERY_KERNEL_0_6_RELEASE.md"
BASE = ROOT / "examples/learner06"
VAL = ROOT / "validation/learner06"
SOURCE = BASE / "learner06_release_artifact.literal.json"
PROGRAM = BASE / "learner06_release_artifact.tmg"
MATERIALIZED = VAL / "TOM_WORLD_QUERY_KERNEL_0_6_RELEASE.materialized.md"
PY_TRACE = VAL / "learner06_release_artifact.python.trace.json"
C_TRACE = VAL / "learner06_release_artifact.c.trace.json"
EMIT_RECORDS = VAL / "learner06_release_artifact.emit_records.json"
PROOF = VAL / "learner06_release_artifact.proof.json"
C_EXE = ROOT / "build/tomagi-c-learner06"

SEED_HASH = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
REPAIR_PROOF_HASH = "sha256:88f1b383fbedfdc15e22001940d65cbc0b518ce3a9f8d9aa27447a9f44f44f3d"
REGISTRY_HASH = "sha256:06952f2ff0d961ca6a92d20c00d3996916009e35e47d903659893a48630d65a4"
LEARNER_PROOF_HASH = "sha256:06ec4c9e511f15d01bfc1cd7e1d44a50a04816b74af3ad8eb9c8bdf2e3135b42"
PROMOTION_PROOF_HASH = "sha256:23c0b88d791102341b331099a2bb2264774554f2ad99e80eeb9ef138ed44c36f"


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
            "source": "TOM Learner 0.2 / WQK 0.6 release documentation",
            "repair_handoff_proof_hash": REPAIR_PROOF_HASH,
            "family_registry_hash": REGISTRY_HASH,
            "learner_proof_hash": LEARNER_PROOF_HASH,
            "promotion_proof_hash": PROMOTION_PROOF_HASH,
            "date": "2026-09-03",
        },
    }
    if tokens:
        value["seed_tokens"] = tokens
    return attach_hash(value)


def source_record(data: bytes) -> dict[str, Any]:
    count = math.ceil(len(data) / 4)
    width = max(1, len(str(count - 1)))
    entry = f"cell:learner06-release:{0:0{width}d}"
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
            "doc:bytes", "literal-learner06-release-document", "seed-record",
            "bytes", ["tom:tokens"], "construct", 0, "literal",
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
            "doc:expected-hash", "literal-hash", "seed-record", "string",
            ["tom:tokens"], "construct", 1, "literal",
            {"result_type": "string", "value": digest},
        ),
        definition(
            "doc:state", "initial-state", "seed-record", "state64",
            ["tom:tokens"], "construct", 2, "state64.construct",
            {"fields": {"lineage": "0x4c303630"}}, tokens=["lineage"],
        ),
        definition(
            "doc:actual-hash", "computed-hash", "bytes", "string",
            ["doc:bytes"], "transform", 0, "hash.sha256", {"prefix": True},
        ),
        definition(
            "doc:emit", "byte-emission", "bytes", "cell_graph", ["doc:bytes"],
            "transform", 1, "emit.graph",
            {
                "id_prefix": "cell:learner06-release",
                "key_base": {"rho": 700000, "theta": 0, "tick": 0, "phi": 0},
                "key_field": "rho",
                "chunk_bytes": 4,
                "byte_order": "little",
                "halt_last": True,
                "aux_base": "0x4c363000",
            },
            tokens=["transition"],
        ),
        definition(
            "doc:guard", "hash-guard", "hash-pair", "bool",
            ["doc:actual-hash", "doc:expected-hash"], "guard", 0,
            "assert.equal", {}, tokens=["guard"],
        ),
        definition(
            "program:learner06-release", "artifact-program", "state-graph-guard",
            "program", ["doc:state", "doc:emit", "doc:guard"], "lineage", 0,
            "program.construct",
            {
                "entry": entry,
                "seed": "0x4c303630",
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
        "title": "TOM Learner 0.2 / WQK 0.6 release-document artifact",
        "seed_genome": {
            "path": "../../TOM_seed_genome_2026-09-01.txt",
            "bytes": 244,
            "sha256": SEED_HASH,
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
            "token_registry": "../../spec/tom_seed_token_registry_1_0.json",
        },
        "root_definition": "program:learner06-release",
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
    current_bindings = {
        "repair handoff proof": (
            BASE / "repair_handoff_proof.json", REPAIR_PROOF_HASH,
        ),
        "family registry": (BASE / "family_registry.json", REGISTRY_HASH),
        "learner proof": (VAL / "learner_authority_proof.json", LEARNER_PROOF_HASH),
        "promotion proof": (
            VAL / "promotion_authority_proof.json", PROMOTION_PROOF_HASH,
        ),
    }
    for label, (path, expected) in current_bindings.items():
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("content_hash") != expected:
            raise RuntimeError(f"release artifact has a stale {label} binding")

    source_bytes = DOC.read_bytes()
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    VAL.mkdir(parents=True, exist_ok=True)
    if os.environ.get("TOM_LEARNER06_REFRESH_ARTIFACT_SOURCE") == "1":
        SOURCE.write_text(
            json.dumps(source_record(source_bytes), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not SOURCE.is_file():
        raise FileNotFoundError(f"missing literal artifact definition: {SOURCE}")

    result = compile_file_result(SOURCE, PROGRAM)
    if result is None:
        raise RuntimeError("0.6 release artifact did not compile under seeded profile")
    data, state, trace, records = materialize_file(PROGRAM, MATERIALIZED)
    if data != source_bytes:
        raise RuntimeError("materialized 0.6 release document differs from authored bytes")

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
        raise RuntimeError("0.6 release-document Python and C traces differ")
    c_data, c_emit = materialize_trace(load(PROGRAM), c_record["trace"])
    if c_data != data:
        raise RuntimeError("0.6 release-document C and Python bytes differ")

    sidecar = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    proof = attach_hash({
        "schema": "TOM-WQK-0.6-RELEASE-ARTIFACT-PROOF-1.0",
        "status": "pass",
        "repair_handoff_proof_hash": REPAIR_PROOF_HASH,
        "family_registry_hash": REGISTRY_HASH,
        "learner_proof_hash": LEARNER_PROOF_HASH,
        "promotion_proof_hash": PROMOTION_PROOF_HASH,
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
            "python_c_emit_sequence_equal": [r.as_record() for r in records]
            == [r.as_record() for r in c_emit],
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
