"""Format-agnostic materialization of literal bytes emitted by TOMAGI.

This module deliberately knows nothing about images, geometry, text, media types,
or output-token meanings. A TOMAGI ``EMIT`` cell owns one to four literal bytes.
Execution selects the cells; this host layer concatenates those bytes and writes no
interpretation into the artifact.

Packing profile ``tomagi-emit-bytes-be-v1``
------------------------------------------------

* ``Cell48.payload`` is interpreted as an unsigned 32-bit big-endian byte word.
* EMIT flag bits 24..25 encode ``byte_count - 1`` (values 0..3 => 1..4 bytes).
* The first ``byte_count`` bytes of the big-endian word are appended.
* EMIT flag bit 0 retains its existing halt meaning and is independent of length.

Big-endian payload order makes a literal word such as ``0x544f4d41`` materialize
as ``b"TOMA"`` regardless of the little-endian storage used by the ``.tmg`` file.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .core import Opcode, Program, State, run, u32
from .format import dumps


MATERIALIZATION_PROFILE = "tomagi-emit-bytes-be-v1"
EMIT_BYTE_COUNT_SHIFT = 24
EMIT_BYTE_COUNT_MASK = 0x3 << EMIT_BYTE_COUNT_SHIFT


@dataclass(frozen=True, slots=True)
class MaterializationResult:
    """Literal artifact bytes and the execution evidence that produced them."""

    data: bytes
    manifest: dict[str, Any]
    state: State
    trace: list[dict[str, int]]
    emissions: list[dict[str, int]]


def _state_dict(state: State) -> dict[str, int]:
    return {name: int(getattr(state, name)) for name in state.__dataclass_fields__}


def encode_emit_byte_count(byte_count: int, *, flags: int = 0) -> int:
    """Encode a 1..4 byte length without changing any other EMIT flag."""

    if not 1 <= byte_count <= 4:
        raise ValueError("EMIT literal byte count must be in 1..4")
    return (
        (u32(flags) & ~EMIT_BYTE_COUNT_MASK)
        | ((byte_count - 1) << EMIT_BYTE_COUNT_SHIFT)
    )


def emit_byte_count(flags: int) -> int:
    """Decode the literal byte count from an EMIT cell flag word."""

    return ((u32(flags) & EMIT_BYTE_COUNT_MASK) >> EMIT_BYTE_COUNT_SHIFT) + 1


def literal_payload_bytes(payload: int, byte_count: int) -> bytes:
    """Decode one payload under the profile's explicit big-endian rule."""

    if not 1 <= byte_count <= 4:
        raise ValueError("EMIT literal byte count must be in 1..4")
    return u32(payload).to_bytes(4, "big")[:byte_count]


def materialize_program(program: Program, *, ticks: int | None = None) -> MaterializationResult:
    """Execute *program* and concatenate bytes from the EMIT cells it reaches."""

    final_state, trace = run(program, ticks=ticks, trace=True)
    emissions = [record for record in trace if record["opcode"] == int(Opcode.EMIT)]
    if not emissions:
        raise ValueError("TOMAGI materialization requires at least one EMIT trace record")

    chunks: list[bytes] = []
    chunk_lengths: list[int] = []
    for record in emissions:
        cell_index = int(record["cell_before"])
        cell = program.cells[cell_index]
        # The trace opcode is the primary selection rule; this assertion protects
        # against a malformed or externally synthesized trace/program pairing.
        if cell.opcode != int(Opcode.EMIT):
            raise ValueError(f"trace cell {cell_index} is not an EMIT cell")
        length = emit_byte_count(cell.flags)
        chunks.append(literal_payload_bytes(cell.payload, length))
        chunk_lengths.append(length)

    data = b"".join(chunks)
    requested_ticks = program.default_ticks if ticks is None else ticks
    program_sha256 = sha256(dumps(program)).hexdigest()
    artifact_sha256 = sha256(data).hexdigest()
    manifest: dict[str, Any] = {
        "tomagi_version": "1.0.0",
        "materialization_profile": MATERIALIZATION_PROFILE,
        "program_sha256": program_sha256,
        "artifact_sha256": artifact_sha256,
        "seed": u32(program.seed),
        "requested_ticks": requested_ticks,
        "executed_ticks": len(trace),
        "emit_count": len(emissions),
        "byte_count": len(data),
        "chunk_byte_counts": chunk_lengths,
        "emit_steps": [int(record["step"]) for record in emissions],
        "final_lineage": u32(final_state.lineage),
        "final_output": u32(final_state.output),
        "final_state": _state_dict(final_state),
    }
    return MaterializationResult(data, manifest, final_state, trace, emissions)
