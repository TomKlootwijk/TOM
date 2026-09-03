from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tomagi.canonical import attach_hash, canonical_bytes
from tomagi.compiler import compile_file_result
from tomagi.format import load
from tomagi.materialize import materialize_file, materialize_trace

DOC = ROOT / "TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.md"
SOURCE = ROOT / "examples/world03/world03_release_artifact.literal.json"
PROGRAM = ROOT / "examples/world03/world03_release_artifact.tmg"
MATERIALIZED = ROOT / "validation/world03/TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.materialized.md"
PY_TRACE = ROOT / "validation/world03/world03_release_artifact.python.trace.json"
C_TRACE = ROOT / "validation/world03/world03_release_artifact.c.trace.json"
EMIT_RECORDS = ROOT / "validation/world03/world03_release_artifact.emit_records.json"
PROOF = ROOT / "validation/world03/world03_release_artifact.proof.json"
C_EXE = ROOT / "build/tomagi-c"

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
            "source": "TOM World & Query Kernel 0.3 release documentation literal artifact",
            "date": "2026-09-01",
        },
    }
    if tokens:
        value["seed_tokens"] = tokens
    return attach_hash(value)


def source_record(data: bytes) -> dict[str, Any]:
    count = math.ceil(len(data) / 4)
    width = max(1, len(str(count - 1)))
    entry = f"cell:world03-release:{0:0{width}d}"
    digest = sha(data)
    definitions = [
        definition("tom:seed", "canonical-seed", "none", "bytes", [], "parse", 0,
                   "seed.bytes", {}, tokens=["TOM1"]),
        definition("tom:tokens", "seed-parse", "bytes", "record", ["tom:seed"], "resolve", 0,
                   "seed.tokens", {}, tokens=["TopologicalOpenModular"]),
        definition("doc:bytes", "literal-document", "seed-record", "bytes", ["tom:tokens"],
                   "construct", 0, "literal", {
                       "result_type": "bytes",
                       "value": {"encoding": "base64", "data": base64.b64encode(data).decode("ascii")},
                   }, tokens=["Pi"]),
        definition("doc:expected-hash", "literal-hash", "seed-record", "string", ["tom:tokens"],
                   "construct", 1, "literal", {"result_type": "string", "value": digest}),
        definition("doc:state", "initial-state", "seed-record", "state64", ["tom:tokens"],
                   "construct", 2, "state64.construct", {"fields": {"lineage": "0x57303344"}},
                   tokens=["lineage"]),
        definition("doc:actual-hash", "computed-hash", "bytes", "string", ["doc:bytes"],
                   "transform", 0, "hash.sha256", {"prefix": True}),
        definition("doc:emit", "byte-emission", "bytes", "cell_graph", ["doc:bytes"],
                   "transform", 1, "emit.graph", {
                       "id_prefix": "cell:world03-release",
                       "key_base": {"rho": 300000, "theta": 0, "tick": 0, "phi": 0},
                       "key_field": "rho",
                       "chunk_bytes": 4,
                       "byte_order": "little",
                       "halt_last": True,
                       "aux_base": "0x57303300",
                   }, tokens=["transition"]),
        definition("doc:guard", "hash-guard", "hash-pair", "bool",
                   ["doc:actual-hash", "doc:expected-hash"], "guard", 0,
                   "assert.equal", {}, tokens=["guard"]),
        definition("program:world03-release", "artifact-program", "state-graph-guard", "program",
                   ["doc:state", "doc:emit", "doc:guard"], "lineage", 0,
                   "program.construct", {
                       "entry": entry,
                       "seed": "0x57303330",
                       "default_ticks": count,
                       "flags": 0,
                       "emit_bytes": True,
                   }, tokens=["event", "transition", "lineage"]),
    ]
    return {
        "$schema": "../../spec/tom_seeded_program.schema.json",
        "tomagi_version": "1.0.0",
        "compilation_profile": "TOM-SEEDED-COMPILATION-1.0",
        "title": "TOM World & Query Kernel 0.3 release document literal artifact",
        "seed_genome": {
            "path": "../../TOM_seed_genome_2026-09-01.txt",
            "bytes": 244,
            "sha256": SEED_HASH,
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
            "token_registry": "../../spec/tom_seed_token_registry_1_0.json",
        },
        "root_definition": "program:world03-release",
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


def main() -> None:
    source_bytes = DOC.read_bytes()
    if os.environ.get("TOM_WORLD03_REFRESH_ARTIFACT_SOURCE") == "1":
        SOURCE.write_text(json.dumps(source_record(source_bytes), indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    if not SOURCE.is_file():
        raise FileNotFoundError(f"missing literal artifact definition: {SOURCE}")

    result = compile_file_result(SOURCE, PROGRAM)
    if result is None:
        raise RuntimeError("release artifact did not compile under seeded profile")
    data, state, trace, records = materialize_file(PROGRAM, MATERIALIZED)
    if data != source_bytes:
        raise RuntimeError("materialized release document is not byte-identical to the authored release document")

    state_record = {name: getattr(state, name) for name in state.__dataclass_fields__}
    py_record = {"state": state_record, "trace": trace}
    PY_TRACE.write_bytes(canonical_bytes(py_record) + b"\n")
    EMIT_RECORDS.write_bytes(canonical_bytes([record.as_record() for record in records]) + b"\n")

    if not C_EXE.exists():
        C_EXE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c", "-o", str(C_EXE),
        ], cwd=ROOT, check=True)
    c_record = json.loads(subprocess.check_output(
        [str(C_EXE), str(PROGRAM), "--trace-json"], cwd=ROOT
    ).decode("utf-8"))
    C_TRACE.write_bytes(canonical_bytes(c_record) + b"\n")
    if c_record != py_record:
        raise RuntimeError("release-document Python and C traces differ")
    c_data, c_emit = materialize_trace(load(PROGRAM), c_record["trace"])
    if c_data != data:
        raise RuntimeError("release-document C and Python materialized bytes differ")

    sidecar = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    proof = {
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-RELEASE-ARTIFACT-PROOF",
        "status": "pass",
        "literal_source": {
            "path": str(SOURCE.relative_to(ROOT)), "bytes": SOURCE.stat().st_size,
            "sha256": sha(SOURCE.read_bytes()),
        },
        "compile_sidecar": {
            "path": str(sidecar.relative_to(ROOT)), "bytes": sidecar.stat().st_size,
            "sha256": sha(sidecar.read_bytes()),
        },
        "program": {
            "path": str(PROGRAM.relative_to(ROOT)), "bytes": PROGRAM.stat().st_size,
            "sha256": sha(PROGRAM.read_bytes()), "cells": len(result.program.cells),
        },
        "execution": {
            "steps": len(trace), "emit_records": len(records),
            "python_c_full_trace_equal": True,
            "python_c_emit_sequence_equal": len(records) == len(c_emit),
        },
        "artifact": {
            "path": str(MATERIALIZED.relative_to(ROOT)), "bytes": len(data),
            "sha256": sha(data), "matches_authored_document": True,
        },
    }
    PROOF.write_bytes(canonical_bytes(proof) + b"\n")
    print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
