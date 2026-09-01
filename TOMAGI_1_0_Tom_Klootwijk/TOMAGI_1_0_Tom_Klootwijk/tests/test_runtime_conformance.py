from __future__ import annotations

import json
import os
import struct
import subprocess
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tomagi.core import (
    Cell,
    Opcode,
    PHI_STATES,
    Program,
    RHO_STATES,
    State,
    STATUS_CONE,
    THETA_STATES,
    TIME_STATES,
    i32,
    mix32,
    rotl32,
    run,
    u32,
)
from tomagi.format import HEADER_SIZE, dumps, loads


ROOT = Path(__file__).resolve().parents[1]
I32_MIN = -(1 << 31)
I32_MAX = (1 << 31) - 1


def one_cell(
    op: Opcode,
    *,
    state: State | None = None,
    args: tuple[int, int, int, int] = (0, 0, 0, 0),
    flags: int = 0,
    payload: int = 0,
    aux: int = 0,
) -> Program:
    cell = Cell(0, 0, int(op), flags, *args, 0, 0, payload, aux)
    return Program([cell], 0, 0xA5A5A5A5, 1, state or State())


def edge_programs() -> dict[str, Program]:
    return {
        "time_wrap": one_cell(
            Opcode.TIME,
            state=State(tick=I32_MAX, lineage=0x12345678),
            args=(1, 0, 0, 0),
            aux=0x10203040,
        ),
        "jit1_int32_min": one_cell(
            Opcode.JIT1,
            state=State(vrho=7),
            args=(I32_MIN, 0, 0, 0),
            flags=4,
        ),
        "cone_extremes": one_cell(
            Opcode.CONE,
            state=State(rho=RHO_STATES - 1, theta=THETA_STATES - 1),
            args=(I32_MAX, I32_MIN, I32_MIN, I32_MIN),
        ),
        "sphere_extremes": one_cell(
            Opcode.SPHERE,
            state=State(rho=RHO_STATES - 1, phi=PHI_STATES - 1),
            args=(I32_MIN, I32_MIN, I32_MIN, I32_MAX),
        ),
        "lsys_extremes": one_cell(
            Opcode.LSYS,
            state=State(
                phi=I32_MAX,
                branch=0,
                orientation=0,
                vrho=I32_MIN,
                vtheta=I32_MAX,
                vtick=-3,
                vphi=3,
            ),
            args=(I32_MIN, 1, 0, 0),
        ),
        "klein_int32_min": one_cell(
            Opcode.KLEIN,
            state=State(rho=RHO_STATES, theta=I32_MIN, phi=I32_MIN),
        ),
    }


class PythonArithmeticConformanceTests(unittest.TestCase):
    def test_time_wraps_to_i32_before_floor_winding(self) -> None:
        program = edge_programs()["time_wrap"]
        initial = program.initial_state
        key_hi, key_lo = initial.normalized_key()
        raw = i32(initial.tick + program.cells[0].arg0)
        wraps = raw // TIME_STATES
        self.assertEqual(raw, I32_MIN)
        self.assertEqual(wraps, -131072)

        expected_lineage = mix32(initial.lineage ^ u32(wraps) ^ program.cells[0].aux)
        expected_lineage = mix32(
            expected_lineage
            ^ program.cells[0].payload
            ^ program.cells[0].aux
            ^ key_hi
            ^ rotl32(key_lo, 7)
            ^ (wraps & 1)
        )
        state, _ = run(program, ticks=1)
        self.assertEqual(state.tick, 0)
        self.assertEqual(state.branch, 0)
        self.assertEqual(state.lineage, expected_lineage)
        self.assertEqual(state.lineage, 3570288091)

    def test_extreme_operands_have_defined_wrapped_results(self) -> None:
        expected = {
            "jit1_int32_min": {"branch": 0, "vrho": -2147483641},
            "cone_extremes": {
                "branch": 1,
                "residual": -2146435073,
                "status": STATUS_CONE,
            },
            "sphere_extremes": {"branch": 0, "residual": 1048575},
            "lsys_extremes": {
                "phi": 4095,
                "vrho": -1073741824,
                "vtheta": 1073741823,
                "vtick": -1,
                "vphi": 1,
            },
            "klein_int32_min": {
                "rho": 0,
                "theta": THETA_STATES // 2,
                "phi": 0,
                "orientation": 1,
                "branch": 1,
            },
        }
        programs = edge_programs()
        for name, fields in expected.items():
            with self.subTest(name=name):
                state, _ = run(programs[name], ticks=1)
                for field, value in fields.items():
                    if field == "status":
                        self.assertEqual(state.status & value, value)
                    else:
                        self.assertEqual(getattr(state, field), value)


class LoaderConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.blob = dumps(one_cell(Opcode.NOP))

    def test_python_loader_rejects_each_nonzero_reserved_word(self) -> None:
        for offset in range(40, 64, 4):
            with self.subTest(offset=offset):
                malformed = bytearray(self.blob)
                struct.pack_into("<I", malformed, offset, 1)
                with self.assertRaisesRegex(ValueError, "reserved.*zero"):
                    loads(malformed)

    def test_python_loader_rejects_opcode_outside_0_through_15(self) -> None:
        for opcode in (16, 0xFFFFFFFF):
            with self.subTest(opcode=opcode):
                malformed = bytearray(self.blob)
                struct.pack_into("<I", malformed, HEADER_SIZE + 8, opcode)
                with self.assertRaisesRegex(ValueError, "invalid cell opcode"):
                    loads(malformed)


class CBackendConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configured = os.environ.get("TOMAGI_C_EXE")
        cls.exe = Path(configured) if configured else ROOT / "build" / "tomagi-c"
        if not cls.exe.exists():
            raise unittest.SkipTest("C backend has not been built")
        if os.name == "nt" and cls.exe.read_bytes()[:4] == b"\x7fELF":
            raise unittest.SkipTest("the available C backend is a Linux executable")

    def run_c(self, program: Program, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.tmg"
            path.write_bytes(dumps(program))
            return subprocess.run(
                [str(self.exe), str(path), *args],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_c_matches_python_for_i32_edge_matrix(self) -> None:
        for name, program in edge_programs().items():
            with self.subTest(name=name):
                expected, _ = run(program, ticks=1)
                result = self.run_c(program, "1")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), asdict(expected))

    def test_c_loader_rejects_reserved_words_and_bad_opcode(self) -> None:
        program = one_cell(Opcode.NOP)
        mutations = {
            **{
                f"reserved_{offset}": (offset, 1, "reserved.*zero")
                for offset in range(40, 64, 4)
            },
            "opcode_16": (HEADER_SIZE + 8, 16, "invalid cell opcode"),
            "opcode_u32_max": (
                HEADER_SIZE + 8,
                0xFFFFFFFF,
                "invalid cell opcode",
            ),
        }
        for name, (offset, value, message) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                malformed = bytearray(dumps(program))
                struct.pack_into("<I", malformed, offset, value)
                path = Path(directory) / "malformed.tmg"
                path.write_bytes(malformed)
                result = subprocess.run(
                    [str(self.exe), str(path)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertRegex(result.stderr, message)

    def test_c_trace_matches_normative_python_fields(self) -> None:
        program = edge_programs()["time_wrap"]
        _, trace = run(program, ticks=1, trace=True)
        result = self.run_c(program, "1", "--trace")
        self.assertEqual(result.returncode, 0, result.stderr)
        tokens = dict(part.split("=", 1) for part in result.stderr.strip().split())
        self.assertEqual(tokens.pop("op_name"), "TIME")
        actual = {name: int(value) for name, value in tokens.items()}
        self.assertEqual(actual, trace[0])


if __name__ == "__main__":
    unittest.main()
