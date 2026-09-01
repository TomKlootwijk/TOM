from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from tomagi import project
from tomagi.cli import main
from tomagi.core import Cell, FLAG_EMIT_HALT, Opcode, Program, State
from tomagi.format import dump, dumps
from tomagi.project import (
    EMIT_BYTE_COUNT_MASK,
    MATERIALIZATION_PROFILE,
    emit_byte_count,
    encode_emit_byte_count,
    literal_payload_bytes,
    materialize_program,
)


ARBITRARY_BYTES = b"\x00\xffTOM\n\x80\x00\xfe\x7f"


def _payload(chunk: bytes) -> int:
    return int.from_bytes(chunk.ljust(4, b"\0"), "big")


def literal_artifact_program() -> Program:
    """Emit arbitrary binary chunks of every supported length after one NOP."""

    chunks = (b"\x00", b"\xffT", b"OM\n", b"\x80\x00\xfe\x7f")
    cells = [
        Cell(0, 0, int(Opcode.NOP), 0, 0, 0, 0, 0,
             1, 1, 0x4E4F5020, 0x10),
    ]
    for index, chunk in enumerate(chunks, start=1):
        is_last = index == len(chunks)
        base_flags = FLAG_EMIT_HALT if is_last else 0
        flags = encode_emit_byte_count(len(chunk), flags=base_flags)
        successor = index if is_last else index + 1
        cells.append(
            Cell(0, index, int(Opcode.EMIT), flags, 0, 0, 0, 0,
                 successor, successor, _payload(chunk), 0x20 + index)
        )
    return Program(
        cells,
        entry=0,
        seed=0xA5A5A5A5,
        default_ticks=len(cells),
        initial_state=State(lineage=0x12345678),
    )


class LiteralMaterializationTests(unittest.TestCase):
    def test_arbitrary_binary_bytes_round_trip_through_emit_cells(self):
        result = materialize_program(literal_artifact_program())

        self.assertEqual(result.data, ARBITRARY_BYTES)
        self.assertEqual(len(result.trace), 5)
        self.assertEqual(len(result.emissions), 4)
        self.assertEqual([record["opcode"] for record in result.emissions],
                         [int(Opcode.EMIT)] * 4)
        self.assertEqual(result.manifest["chunk_byte_counts"], [1, 2, 3, 4])
        self.assertEqual(result.manifest["emit_steps"], [1, 2, 3, 4])
        self.assertEqual(result.manifest["byte_count"], len(ARBITRARY_BYTES))
        self.assertEqual(result.manifest["artifact_sha256"],
                         sha256(ARBITRARY_BYTES).hexdigest())

    def test_packing_profile_is_explicit_and_preserves_halt(self):
        unrelated_flag = 1 << 12
        for byte_count in range(1, 5):
            flags = encode_emit_byte_count(
                byte_count, flags=FLAG_EMIT_HALT | unrelated_flag
            )
            self.assertEqual(emit_byte_count(flags), byte_count)
            self.assertTrue(flags & FLAG_EMIT_HALT)
            self.assertTrue(flags & unrelated_flag)
            self.assertEqual(flags & EMIT_BYTE_COUNT_MASK,
                             (byte_count - 1) << 24)

        with self.assertRaises(ValueError):
            encode_emit_byte_count(0)
        with self.assertRaises(ValueError):
            encode_emit_byte_count(5)

    def test_payload_order_is_big_endian_and_length_delimited(self):
        payload = 0x544F4D41
        self.assertEqual(literal_payload_bytes(payload, 1), b"T")
        self.assertEqual(literal_payload_bytes(payload, 2), b"TO")
        self.assertEqual(literal_payload_bytes(payload, 3), b"TOM")
        self.assertEqual(literal_payload_bytes(payload, 4), b"TOMA")

    def test_manifest_is_deterministic_and_format_agnostic(self):
        program = literal_artifact_program()
        first = materialize_program(program)
        second = materialize_program(program)

        self.assertEqual(first.data, second.data)
        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual(first.manifest["materialization_profile"],
                         MATERIALIZATION_PROFILE)
        self.assertEqual(first.manifest["program_sha256"],
                         sha256(dumps(program)).hexdigest())
        self.assertNotIn("artifact_format", first.manifest)

    def test_materialize_cli_writes_exact_bytes_trace_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program_path = root / "literal.tmg"
            artifact_path = root / "artifact.bin"
            trace_path = root / "artifact.trace.json"
            manifest_path = root / "artifact.manifest.json"
            dump(literal_artifact_program(), program_path)

            status = main([
                "materialize", str(program_path), str(artifact_path),
                "--ticks", "5",
                "--trace-output", str(trace_path),
                "--manifest", str(manifest_path),
            ])

            self.assertEqual(status, 0)
            self.assertEqual(artifact_path.read_bytes(), ARBITRARY_BYTES)
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(trace["trace"]), 5)
            self.assertEqual(manifest["byte_count"], len(ARBITRARY_BYTES))
            self.assertEqual(manifest["artifact_sha256"],
                             sha256(ARBITRARY_BYTES).hexdigest())

    def test_program_without_emit_is_rejected(self):
        cell = Cell(0, 0, int(Opcode.HALT), 0, 0, 0, 0, 0, 0, 0, 0, 0)
        program = Program([cell], 0, 0, 1, State())
        with self.assertRaisesRegex(ValueError, "at least one EMIT"):
            materialize_program(program)

    def test_host_contains_no_artifact_or_shape_semantics(self):
        source = Path(project.__file__).read_text(encoding="utf-8")
        for forbidden in ("PYRA", "CIRC", "image/svg+xml", "<svg", "_PALETTE"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
