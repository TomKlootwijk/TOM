"""Literal definition -> TOMAGI EMIT graph -> generic byte materialization."""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from tomagi.core import Cell, Opcode, Program, State, FLAG_EMIT_HALT, pack_key_contiguous, run
from tomagi.format import dump, load

from .canonical import attach_hash, canonical_bytes, digest_bytes, verify_hash
from .records import make_record, topological_record_order, validate_record
from .seed import verify_seed_bytes

ARTIFACT_SOURCE_SCHEMA = "TOM-LITERAL-ARTIFACT-SOURCE-0.1"
ARTIFACT_COMPILE_REPORT_SCHEMA = "TOM-LITERAL-ARTIFACT-COMPILE-REPORT-0.1"
PROGRAM_FLAG_LITERAL_ARTIFACT = 1 << 8
PROGRAM_FLAG_EMIT_BYTES = 1 << 9
FLAG_EMIT_COUNT_SHIFT = 8
FLAG_EMIT_COUNT_MASK = 0x7 << FLAG_EMIT_COUNT_SHIFT
FLAG_EMIT_BIG_ENDIAN = 1 << 11
MAX_ARTIFACT_BYTES = 1_048_576


def _decode_literal(parameters: Mapping[str, Any]) -> bytes:
    encoding = parameters.get("encoding")
    data = parameters.get("data")
    if not isinstance(encoding, str) or not isinstance(data, str):
        raise ValueError("literal.bytes requires string encoding and data")
    if encoding in {"utf8", "utf-8"}:
        return data.encode("utf-8")
    if encoding == "ascii":
        return data.encode("ascii")
    if encoding == "hex":
        return bytes.fromhex(data)
    if encoding == "base64":
        return base64.b64decode(data, validate=True)
    raise ValueError(f"unsupported literal bytes encoding: {encoding}")


def make_literal_artifact_source(
    artifact_id: str,
    data: bytes,
    *,
    media_type: str,
    seed_bytes: bytes,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = verify_seed_bytes(seed_bytes)
    seed_def = make_record(
        "definition",
        "definition:canonical-seed",
        {
            "kind": "canonical_seed",
            "domain": "none",
            "codomain": "bytes",
            "operation": "seed.bytes",
            "phase": "parse",
            "order": 0,
            "parameters": {},
        },
        provenance={"source": "TOM_seed_genome_2026-09-01.txt"},
    )
    literal_def = make_record(
        "definition",
        f"definition:{artifact_id}:bytes",
        {
            "kind": "literal_artifact_bytes",
            "domain": "canonical_seed",
            "codomain": "bytes",
            "operation": "literal.bytes",
            "phase": "construct",
            "order": 0,
            "parameters": {
                "encoding": "base64",
                "data": base64.b64encode(data).decode("ascii"),
                "media_type": media_type,
            },
        },
        dependencies=[seed_def["id"]],
        provenance=dict(provenance or {}),
    )
    emit_def = make_record(
        "definition",
        f"definition:{artifact_id}:emit",
        {
            "kind": "generic_byte_emission",
            "domain": "bytes",
            "codomain": "cell_graph",
            "operation": "emit.bytes",
            "phase": "transition",
            "order": 0,
            "parameters": {
                "chunk_bytes": 4,
                "byte_order": "little",
                "halt_last": True,
                "rho_start": 1,
            },
        },
        dependencies=[literal_def["id"]],
        provenance={"profile": "TOM-EMIT-BYTES-0.1"},
    )
    return attach_hash({
        "schema": ARTIFACT_SOURCE_SCHEMA,
        "version": "0.1.0",
        "seed_sha256": "sha256:" + identity.sha256,
        "artifact_id": artifact_id,
        "media_type": media_type,
        "root_definition": emit_def["id"],
        "max_output_bytes": MAX_ARTIFACT_BYTES,
        "definitions": [seed_def, literal_def, emit_def],
    })


def _evaluate_source(source: Mapping[str, Any], seed_bytes: bytes) -> tuple[bytes, list[str]]:
    identity = verify_seed_bytes(seed_bytes)
    if source.get("schema") != ARTIFACT_SOURCE_SCHEMA or not verify_hash(source):
        raise ValueError("literal artifact source hash/schema is invalid")
    if source.get("seed_sha256") != "sha256:" + identity.sha256:
        raise ValueError("literal artifact source is not bound to the canonical seed")
    definitions = source.get("definitions")
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("literal artifact source requires definitions")
    order = topological_record_order(definitions)
    by_id = {record["id"]: record for record in definitions}
    values: dict[str, bytes] = {}
    for ident in order:
        record = by_id[ident]
        validate_record(record)
        if record["record_type"] != "definition":
            raise TypeError("artifact definitions must use record_type definition")
        payload = record["payload"]
        operation = payload["operation"]
        dependencies = record["dependencies"]
        if operation == "seed.bytes":
            if dependencies:
                raise ValueError("seed.bytes must not have dependencies")
            value = seed_bytes
        elif operation == "literal.bytes":
            value = _decode_literal(payload.get("parameters", {}))
        elif operation == "concat.bytes":
            if not dependencies:
                raise ValueError("concat.bytes requires dependencies")
            value = b"".join(values[dep] for dep in dependencies)
        elif operation == "emit.bytes":
            if len(dependencies) != 1:
                raise ValueError("emit.bytes requires exactly one bytes dependency")
            value = values[dependencies[0]]
        else:
            raise ValueError(f"unsupported artifact definition operation: {operation}")
        if len(value) > int(source.get("max_output_bytes", MAX_ARTIFACT_BYTES)):
            raise ValueError("artifact output byte budget exceeded")
        values[ident] = value
    root = source.get("root_definition")
    if not isinstance(root, str) or root not in values:
        raise ValueError("artifact root_definition does not resolve")
    if by_id[root]["payload"]["operation"] != "emit.bytes":
        raise ValueError("artifact root_definition must execute emit.bytes")
    return values[root], order


def compile_literal_artifact(
    source: Mapping[str, Any],
    seed_bytes: bytes,
) -> tuple[Program, dict[str, Any]]:
    data, order = _evaluate_source(source, seed_bytes)
    if not data:
        raise ValueError("empty literal artifacts are not supported in 0.1")
    root = next(record for record in source["definitions"] if record["id"] == source["root_definition"])
    parameters = root["payload"].get("parameters", {})
    chunk_bytes = int(parameters.get("chunk_bytes", 4))
    if not 1 <= chunk_bytes <= 4:
        raise ValueError("emit.bytes chunk_bytes must be in 1..4")
    byte_order = parameters.get("byte_order", "little")
    if byte_order not in {"little", "big"}:
        raise ValueError("emit.bytes byte_order must be little or big")
    rho_start = int(parameters.get("rho_start", 1))
    cell_count = math.ceil(len(data) / chunk_bytes)
    if rho_start < 0 or rho_start + cell_count > (1 << 20):
        raise ValueError("artifact EMIT keys exceed the 20-bit rho field")
    cells: list[Cell] = []
    crosswalk: list[dict[str, Any]] = []
    for index in range(cell_count):
        chunk = data[index * chunk_bytes:(index + 1) * chunk_bytes]
        count = len(chunk)
        flags = count << FLAG_EMIT_COUNT_SHIFT
        if byte_order == "big":
            flags |= FLAG_EMIT_BIG_ENDIAN
            payload = int.from_bytes(chunk.rjust(4, b"\0"), "big")
        else:
            payload = int.from_bytes(chunk.ljust(4, b"\0"), "little")
        if parameters.get("halt_last", True) and index == cell_count - 1:
            flags |= FLAG_EMIT_HALT
        hi, lo = pack_key_contiguous(rho_start + index, 0, 0, 0)
        next_index = index + 1 if index + 1 < cell_count else index
        cells.append(Cell(
            hi,
            lo,
            int(Opcode.EMIT),
            flags,
            0,
            0,
            0,
            0,
            next_index,
            next_index,
            payload,
            index,
        ))
        crosswalk.append({
            "cell_index": index,
            "definition_id": root["id"],
            "byte_offset": index * chunk_bytes,
            "byte_count": count,
            "payload": payload,
            "flags": flags,
            "key": f"0x{((hi << 32) | lo):016x}",
        })
    program = Program(
        cells=cells,
        entry=0,
        seed=int(source["seed_sha256"][7:15], 16),
        default_ticks=cell_count,
        initial_state=State(),
        flags=PROGRAM_FLAG_LITERAL_ARTIFACT | PROGRAM_FLAG_EMIT_BYTES,
    )
    report = attach_hash({
        "schema": ARTIFACT_COMPILE_REPORT_SCHEMA,
        "artifact_id": source["artifact_id"],
        "source_hash": source["content_hash"],
        "seed_sha256": source["seed_sha256"],
        "definition_order": order,
        "definition_hashes": {record["id"]: record["content_hash"] for record in source["definitions"]},
        "artifact_bytes": len(data),
        "artifact_sha256": digest_bytes(data),
        "cell_count": cell_count,
        "crosswalk": crosswalk,
    })
    return program, report


def compile_literal_artifact_file(
    source_path: str | Path,
    seed_path: str | Path,
    program_path: str | Path,
) -> dict[str, Any]:
    source_file = Path(source_path)
    source = json.loads(source_file.read_text(encoding="utf-8"))
    program, report = compile_literal_artifact(source, Path(seed_path).read_bytes())
    destination = Path(program_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dump(program, destination)
    report = dict(report)
    report["program_bytes"] = destination.stat().st_size
    report["program_sha256"] = digest_bytes(destination.read_bytes())
    report = attach_hash({key: value for key, value in report.items() if key != "content_hash"})
    destination.with_suffix(destination.suffix + ".compile.json").write_bytes(canonical_bytes(report) + b"\n")
    return report


def decode_emit_cell(cell: Cell) -> bytes:
    if cell.opcode != int(Opcode.EMIT):
        raise ValueError("cell is not EMIT")
    count = (cell.flags & FLAG_EMIT_COUNT_MASK) >> FLAG_EMIT_COUNT_SHIFT
    if not 1 <= count <= 4:
        raise ValueError(f"EMIT byte count must be in 1..4, got {count}")
    if cell.flags & FLAG_EMIT_BIG_ENDIAN:
        return cell.payload.to_bytes(4, "big")[-count:]
    return cell.payload.to_bytes(4, "little")[:count]


def materialize_trace(program: Program, trace: Sequence[Mapping[str, Any]]) -> tuple[bytes, list[dict[str, Any]]]:
    if not (program.flags & PROGRAM_FLAG_LITERAL_ARTIFACT) or not (program.flags & PROGRAM_FLAG_EMIT_BYTES):
        raise ValueError("program does not declare the literal emitted-byte profile")
    output = bytearray()
    records: list[dict[str, Any]] = []
    for trace_record in trace:
        cell_index = int(trace_record["cell_before"])
        if not 0 <= cell_index < len(program.cells):
            raise ValueError("trace cell index is outside program")
        cell = program.cells[cell_index]
        if cell.opcode != int(Opcode.EMIT):
            continue
        chunk = decode_emit_cell(cell)
        output.extend(chunk)
        records.append({
            "sequence": len(records),
            "step": int(trace_record["step"]),
            "cell_index": cell_index,
            "byte_count": len(chunk),
            "hex": chunk.hex(),
            "flags": cell.flags,
            "payload": cell.payload,
            "lineage": int(trace_record["lineage"]),
        })
    if not records:
        raise ValueError("trace contains no emitted-byte records")
    return bytes(output), records


def run_and_materialize(program: Program) -> tuple[bytes, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    state, trace = run(program, ticks=program.default_ticks, trace=True)
    data, records = materialize_trace(program, trace)
    return data, {name: getattr(state, name) for name in state.__dataclass_fields__}, trace, records


def materialize_literal_artifact_file(
    program_path: str | Path,
    destination_path: str | Path,
    *,
    trace_path: str | Path | None = None,
    records_path: str | Path | None = None,
) -> dict[str, Any]:
    program = load(program_path)
    data, state, trace, records = run_and_materialize(program)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    if trace_path is not None:
        Path(trace_path).write_bytes(canonical_bytes({"state": state, "trace": trace}) + b"\n")
    if records_path is not None:
        Path(records_path).write_bytes(canonical_bytes(records) + b"\n")
    return {
        "artifact_bytes": len(data),
        "artifact_sha256": digest_bytes(data),
        "emit_records": len(records),
        "final_state": state,
    }
