from __future__ import annotations

"""Compile and replay the literal 0.5 release document through TOMAGI."""

import base64
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import attach_hash, canonical_bytes
from tomagi.compiler import compile_file_result
from tomagi.format import load
from tomagi.materialize import materialize_file, materialize_trace

DOC = ROOT / "TOM_WORLD_QUERY_KERNEL_0_5_RELEASE.md"
SOURCE = ROOT / "examples/learner05/learner05_release_artifact.literal.json"
PROGRAM = ROOT / "examples/learner05/learner05_release_artifact.tmg"
MATERIALIZED = ROOT / "validation/learner05/TOM_WORLD_QUERY_KERNEL_0_5_RELEASE.materialized.md"
PY_TRACE = ROOT / "validation/learner05/learner05_release_artifact.python.trace.json"
C_TRACE = ROOT / "validation/learner05/learner05_release_artifact.c.trace.json"
EMIT_RECORDS = ROOT / "validation/learner05/learner05_release_artifact.emit_records.json"
PROOF = ROOT / "validation/learner05/learner05_release_artifact.proof.json"
C_EXE = ROOT / (
    "build/tomagi-c-learner05-wsl"
    if os.name == "nt"
    else "build/tomagi-c-learner05"
)
SEED_HASH = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
HANDOFF_HASH = "sha256:3d2b46cfd33ba6e5cf0a13697fb59e374a64ad30450fdd3c256c98a04ebc474b"


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


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


def definition(
    ident: str, kind: str, domain: str, codomain: str, dependencies: list[str],
    phase: str, order: int, operation: str, parameters: dict[str, Any],
    *, tokens: list[str] | None = None,
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
            "source": "TOM Learner 0.1 / World & Query Kernel 0.5 release documentation",
            "literal_handoff_hash": HANDOFF_HASH,
            "date": "2026-09-01",
        },
    }
    if tokens:
        value["seed_tokens"] = tokens
    return attach_hash(value)


def source_record(data: bytes) -> dict[str, Any]:
    count = math.ceil(len(data) / 4)
    width = max(1, len(str(count - 1)))
    entry = f"cell:learner05-release:{0:0{width}d}"
    digest = sha(data)
    definitions = [
        definition("tom:seed", "canonical-seed", "none", "bytes", [], "parse", 0,
                   "seed.bytes", {}, tokens=["TOM1"]),
        definition("tom:tokens", "seed-parse", "bytes", "record", ["tom:seed"], "resolve", 0,
                   "seed.tokens", {}, tokens=["TopologicalOpenModular"]),
        definition("doc:bytes", "literal-learner-release-document", "seed-record", "bytes", ["tom:tokens"],
                   "construct", 0, "literal", {
                       "result_type": "bytes",
                       "value": {"encoding": "base64", "data": base64.b64encode(data).decode("ascii")},
                   }, tokens=["Pi"]),
        definition("doc:expected-hash", "literal-hash", "seed-record", "string", ["tom:tokens"],
                   "construct", 1, "literal", {"result_type": "string", "value": digest}),
        definition("doc:state", "initial-state", "seed-record", "state64", ["tom:tokens"],
                   "construct", 2, "state64.construct", {"fields": {"lineage": "0x4c303531"}},
                   tokens=["lineage"]),
        definition("doc:actual-hash", "computed-hash", "bytes", "string", ["doc:bytes"],
                   "transform", 0, "hash.sha256", {"prefix": True}),
        definition("doc:emit", "byte-emission", "bytes", "cell_graph", ["doc:bytes"],
                   "transform", 1, "emit.graph", {
                       "id_prefix": "cell:learner05-release",
                       "key_base": {"rho": 420000, "theta": 0, "tick": 0, "phi": 0},
                       "key_field": "rho",
                       "chunk_bytes": 4,
                       "byte_order": "little",
                       "halt_last": True,
                       "aux_base": "0x4c303500",
                   }, tokens=["transition"]),
        definition("doc:guard", "hash-guard", "hash-pair", "bool",
                   ["doc:actual-hash", "doc:expected-hash"], "guard", 0,
                   "assert.equal", {}, tokens=["guard"]),
        definition("program:learner05-release", "artifact-program", "state-graph-guard", "program",
                   ["doc:state", "doc:emit", "doc:guard"], "lineage", 0,
                   "program.construct", {
                       "entry": entry,
                       "seed": "0x4c303531",
                       "default_ticks": count,
                       "flags": 0,
                       "emit_bytes": True,
                   }, tokens=["event", "transition", "lineage"]),
    ]
    return {
        "$schema": "../../spec/tom_seeded_program.schema.json",
        "tomagi_version": "1.0.0",
        "compilation_profile": "TOM-SEEDED-COMPILATION-1.0",
        "title": "TOM Learner 0.1 / WQK 0.5 release document literal artifact",
        "seed_genome": {
            "path": "../../TOM_seed_genome_2026-09-01.txt",
            "bytes": 244,
            "sha256": SEED_HASH,
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
            "token_registry": "../../spec/tom_seed_token_registry_1_0.json",
        },
        "root_definition": "program:learner05-release",
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
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    if os.environ.get("TOM_LEARNER05_REFRESH_ARTIFACT_SOURCE") == "1":
        SOURCE.write_text(json.dumps(source_record(source_bytes), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not SOURCE.is_file():
        raise FileNotFoundError(f"missing literal artifact definition: {SOURCE}")

    result = compile_file_result(SOURCE, PROGRAM)
    if result is None:
        raise RuntimeError("learner release artifact did not compile under seeded profile")
    data, state, trace, records = materialize_file(PROGRAM, MATERIALIZED)
    if data != source_bytes:
        raise RuntimeError("materialized learner release document differs from authored bytes")

    state_record = {name: getattr(state, name) for name in state.__dataclass_fields__}
    py_record = {"state": state_record, "trace": trace}
    PY_TRACE.write_bytes(canonical_bytes(py_record) + b"\n")
    EMIT_RECORDS.write_bytes(canonical_bytes([record.as_record() for record in records]) + b"\n")

    _compile_c()
    c_record = json.loads(
        subprocess.check_output(_c_trace_command(), cwd=ROOT).decode("utf-8")
    )
    C_TRACE.write_bytes(canonical_bytes(c_record) + b"\n")
    if c_record != py_record:
        raise RuntimeError("learner release-document Python and C traces differ")
    c_data, c_emit = materialize_trace(load(PROGRAM), c_record["trace"])
    if c_data != data:
        raise RuntimeError("learner release-document C and Python materialized bytes differ")

    sidecar = PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")
    proof = attach_hash({
        "schema": "TOM-LEARNER-0.1-RELEASE-ARTIFACT-PROOF",
        "status": "pass",
        "literal_handoff_hash": HANDOFF_HASH,
        "literal_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(), "bytes": SOURCE.stat().st_size,
            "sha256": sha(SOURCE.read_bytes()),
        },
        "compile_sidecar": {
            "path": sidecar.relative_to(ROOT).as_posix(), "bytes": sidecar.stat().st_size,
            "sha256": sha(sidecar.read_bytes()),
        },
        "program": {
            "path": PROGRAM.relative_to(ROOT).as_posix(), "bytes": PROGRAM.stat().st_size,
            "sha256": sha(PROGRAM.read_bytes()), "cells": len(result.program.cells),
        },
        "execution": {
            "steps": len(trace), "emit_records": len(records),
            "python_c_full_trace_equal": True,
            "python_c_emit_sequence_equal": len(records) == len(c_emit),
        },
        "artifact": {
            "path": MATERIALIZED.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": sha(data), "matches_authored_document": True,
        },
    })
    PROOF.write_bytes(canonical_bytes(proof) + b"\n")
    print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
