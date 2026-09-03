from __future__ import annotations

"""Build the TOM World & Query Kernel 0.2 release note through TOMAGI.

The Markdown source bytes are placed in content-addressed literal definitions
bound to the canonical TOM seed, lowered to a TOMAGI EMIT graph, executed by
both Python and C99, and recovered only by the generic byte materializer.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tomagi.format import load
from tom_world.artifact import (
    compile_literal_artifact_file,
    make_literal_artifact_source,
    materialize_literal_artifact_file,
    materialize_trace,
)
from tom_world.canonical import attach_hash, canonical_bytes, digest_file

DOCUMENT = ROOT / "docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md"
SOURCE = ROOT / "examples/artifacts/world_query_kernel_0_2_release.source.json"
PROGRAM = ROOT / "examples/artifacts/world_query_kernel_0_2_release.tmg"
ARTIFACT = ROOT / "artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md"
PY_TRACE = ROOT / "validation/release_0_2_artifact.python.trace.json"
C_TRACE = ROOT / "validation/release_0_2_artifact.c.trace.json"
EMIT_RECORDS = ROOT / "validation/release_0_2_artifact.emit_records.json"
PROOF = ROOT / "validation/release_0_2_artifact_proof.json"
SEED = ROOT / "TOM_seed_genome_2026-09-01.txt"
C_EXE = ROOT / "build/tomagi-c"


def write_json(path: Path, value: object, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_bytes(canonical_bytes(value) + b"\n")


def main() -> int:
    if not C_EXE.is_file():
        raise FileNotFoundError("build/tomagi-c is required")
    data = DOCUMENT.read_bytes()
    source = make_literal_artifact_source(
        "tom-world-query-kernel-0-2-release",
        data,
        media_type="text/markdown; charset=utf-8",
        seed_bytes=SEED.read_bytes(),
        provenance={
            "source": "docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md",
            "role": "0.2 release documentation",
            "milestone": "World & Query Kernel 1B",
        },
    )
    write_json(SOURCE, source, pretty=True)
    compile_report = compile_literal_artifact_file(SOURCE, SEED, PROGRAM)
    materialized = materialize_literal_artifact_file(
        PROGRAM,
        ARTIFACT,
        trace_path=PY_TRACE,
        records_path=EMIT_RECORDS,
    )
    if ARTIFACT.read_bytes() != data:
        raise RuntimeError("0.2 release artifact does not equal source documentation bytes")

    c_record = json.loads(subprocess.check_output(
        [str(C_EXE), str(PROGRAM), "--trace-json"],
        cwd=ROOT,
        text=True,
    ))
    write_json(C_TRACE, c_record)
    py_record = json.loads(PY_TRACE.read_text(encoding="utf-8"))
    trace_equal = canonical_bytes(c_record) == canonical_bytes(py_record)
    if not trace_equal:
        raise RuntimeError("0.2 release artifact Python/C traces differ")
    program = load(PROGRAM)
    c_data, c_records = materialize_trace(program, c_record["trace"])
    if c_data != data:
        raise RuntimeError("C trace does not materialize the 0.2 release documentation bytes")

    proof = attach_hash({
        "schema": "TOM-WORLD-QUERY-RELEASE-ARTIFACT-PROOF-0.2",
        "version": "0.2.0",
        "status": "pass",
        "chain": [
            "TOM_seed_genome_2026-09-01.txt",
            "examples/artifacts/world_query_kernel_0_2_release.source.json",
            "examples/artifacts/world_query_kernel_0_2_release.tmg",
            "ordered TOMAGI EMIT trace",
            "artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md",
        ],
        "source_document": {
            "path": DOCUMENT.relative_to(ROOT).as_posix(),
            "bytes": DOCUMENT.stat().st_size,
            "sha256": digest_file(DOCUMENT),
        },
        "definition_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "bytes": SOURCE.stat().st_size,
            "sha256": digest_file(SOURCE),
            "content_hash": source["content_hash"],
        },
        "program": {
            "path": PROGRAM.relative_to(ROOT).as_posix(),
            "bytes": PROGRAM.stat().st_size,
            "sha256": digest_file(PROGRAM),
            "cells": compile_report["cell_count"],
            "compile_report_sha256": digest_file(PROGRAM.with_suffix(PROGRAM.suffix + ".compile.json")),
        },
        "execution": {
            "steps": len(py_record["trace"]),
            "emit_records": len(c_records),
            "python_c_full_trace_equal": trace_equal,
            "python_trace_sha256": digest_file(PY_TRACE),
            "c_trace_sha256": digest_file(C_TRACE),
            "emit_records_sha256": digest_file(EMIT_RECORDS),
        },
        "artifact": {
            "path": ARTIFACT.relative_to(ROOT).as_posix(),
            "bytes": ARTIFACT.stat().st_size,
            "sha256": digest_file(ARTIFACT),
            "source_byte_equal": ARTIFACT.read_bytes() == DOCUMENT.read_bytes(),
        },
        "materializer": {
            "domain_specific_format_logic": False,
            "profile": "TOM-EMIT-BYTES-0.1",
            "python_result": materialized,
        },
    })
    write_json(PROOF, proof, pretty=True)
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
