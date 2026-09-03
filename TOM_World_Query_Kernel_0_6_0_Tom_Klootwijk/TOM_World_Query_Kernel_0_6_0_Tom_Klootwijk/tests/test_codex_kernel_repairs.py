from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
import runpy
import struct
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import attach_hash
from tomagi.core import (
    Cell, Opcode, Program, State, run,
    FLAG_KLEIN_FLIP_SHEET, FLAG_PHI_BRANCH_HALF,
)
from tomagi.format import dumps, loads
from tomagi.formal import FormalBudgetExceeded, Limits, evaluate
from tomagi.immutable_store import (
    ImmutablePublicationStore,
    _same_host_publication_lock,
)

canonicalize_test_output = runpy.run_path(
    ROOT / "tools/run_learner06_tests.py"
)["canonicalize_test_output"]


def _state_record(state: State) -> dict[str, int]:
    return {name: getattr(state, name) for name in state.__dataclass_fields__}


class TestLogNormalizationTests(unittest.TestCase):
    def test_paths_timing_and_line_endings_are_canonical(self):
        raw = (
            f"test_example ... ok\r\n"
            f"Ran 258 tests in 12.345s\r\n"
            f"root={ROOT}/tests\r\n"
            "/tmp/tom-wqk-audit.123/output.json\r\n"
            "OK\r\n"
        )
        self.assertEqual(
            canonicalize_test_output(raw),
            "test_example ... ok\n"
            "Ran 258 tests\n"
            "root=<PACKAGE_ROOT>/tests\n"
            "<TEMP_PATH>\n"
            "OK\n",
        )


def _publication(profile: str, sequence: int, expected: str | None, tag: str) -> dict:
    commit = attach_hash({
        "schema": "TOM-LOCK-TEST-COMMIT-1.0",
        "tag": tag,
        "sequence": sequence,
        "parent": expected,
    })
    publication = attach_hash({
        "schema": "TOMAGI-IMMUTABLE-PUBLICATION-1.0",
        "profile": profile,
        "sequence": sequence,
        "expected_head": expected,
        "replacement_head": commit["content_hash"],
        "required_hashes": [commit["content_hash"]],
        "writes": [{"namespace": "commits", "record": commit}],
    })
    return publication


def _process_publish(root: str, publication: dict, start, queue) -> None:
    start.wait()
    try:
        result = ImmutablePublicationStore(root).apply_publication(publication)
        queue.put(("success", result))
    except Exception as exc:  # deterministic evidence returned to parent
        queue.put(("error", type(exc).__name__, str(exc)))


def _process_die_holding_lock(root: str) -> None:
    with _same_host_publication_lock(Path(root)):
        os._exit(0)


class ReservedHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exe = ROOT / "build/tomagi-c"
        if not cls.exe.exists():
            subprocess.run(
                ["cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                 "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c", "-o", str(cls.exe)],
                cwd=ROOT, check=True,
            )

    def test_all_six_reserved_words_reject_in_python_and_c(self):
        program = Program(
            [Cell(0, 0, int(Opcode.NOP), 0, 0, 0, 0, 0, 0, 0, 0, 0)],
            0, 0, 1, State(), 0,
        )
        pristine = dumps(program)
        for index in range(6):
            data = bytearray(pristine)
            struct.pack_into("<I", data, 40 + 4 * index, index + 1)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "reserved"):
                loads(bytes(data))
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "bad.tmg"
                path.write_bytes(data)
                result = subprocess.run(
                    [str(self.exe), str(path), "1", "--trace-json"],
                    text=True, capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("reserved TOMAGI header words must be zero", result.stderr)


class ExtremeI32ConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exe = ROOT / "build/tomagi-c"

    def _compare(self, op: Opcode, state: State, args=(0, 0, 0, 0), flags=0, aux=0):
        cell = Cell(0, 0, int(op), flags, *args, 0, 0, 0, aux)
        program = Program([cell], 0, 0xFFFFFFFF, 1, state, 0)
        py_state, py_trace = run(program, ticks=1, trace=True)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "extreme.tmg"
            path.write_bytes(dumps(program))
            actual = json.loads(subprocess.check_output(
                [str(self.exe), str(path), "1", "--trace-json"], text=True,
            ))
        self.assertEqual(actual["state"], _state_record(py_state))
        self.assertEqual(actual["trace"], py_trace)

    def test_extreme_signed_operands_match_python_without_undefined_overflow(self):
        cases = [
            (Opcode.JIT1, State(phi=0, tick=-2**31), (-2**31, 0, 0, 0), 3, 0xFFFFFFFF),
            (Opcode.KIN2, State(rho=2**31-1, theta=-2**31, tick=2**31-1, phi=-2**31,
                                vrho=2**31-1, vtheta=-2**31, vtick=2**31-1, vphi=-2**31),
             (2**31-1, -2**31, 2**31-1, -2**31), 0, 0),
            (Opcode.PHI, State(phi=2**31-1), (2**31-1, 0, 0, 0), FLAG_PHI_BRANCH_HALF, 0),
            (Opcode.TIME, State(tick=-2**31), (-2**31, 0, 0, 0), 0, 0),
            (Opcode.CONE, State(rho=2**31-1, theta=-2**31),
             (-2**31, 2**31-1, -2**31, -2**31), 0, 0),
            (Opcode.SPHERE, State(rho=-2**31, phi=2**31-1),
             (2**31-1, -2**31, -2**31, -2**31), 0, 0),
            (Opcode.KLEIN, State(rho=-2**31, theta=2**31-1, phi=-2**31),
             (0, 0, 0, 0), FLAG_KLEIN_FLIP_SHEET, 0),
            (Opcode.HINGE, State(rho=2**31-1, theta=-2**31, tick=2**31-1, phi=-2**31,
                                 branch=1),
             (2**31-1, -2**31, 2**31-1, -2**31), 0, 0),
            (Opcode.LSYS, State(phi=2**31-1, orientation=1, branch=1,
                                vrho=-2**31, vtheta=2**31-1, vtick=-2**31, vphi=2**31-1),
             (-2**31, 31, 0, 0), 0, 0),
        ]
        for case in cases:
            with self.subTest(op=case[0].name):
                self._compare(*case)


class RecursiveFormalBudgetTests(unittest.TestCase):
    def test_discarded_oversized_let_binding_rejects_before_parent_consumes_it(self):
        # The root value is the tiny integer 0.  Only recursive-result checking
        # catches the oversized fold binding before the let body discards it.
        source = {"op": "list", "items": [
            {"op": "lit", "value": "abcdefghij"} for _ in range(12)
        ]}
        expression = {
            "op": "let",
            "bindings": [{
                "name": "oversized",
                "value": {
                    "op": "fold",
                    "source": source,
                    "item": "item",
                    "accumulator": "acc",
                    "initial": {"op": "list", "items": []},
                    "body": {
                        "op": "append",
                        "source": {"op": "ref", "name": "acc"},
                        "value": {"op": "ref", "name": "item"},
                    },
                },
            }],
            "body": {"op": "lit", "value": 0},
        }
        with self.assertRaisesRegex(FormalBudgetExceeded, "max_canonical_bytes"):
            evaluate(expression, limits=Limits(
                max_steps=10_000,
                max_depth=64,
                max_collection_items=100,
                max_value_nodes=1_000,
                max_canonical_bytes=64,
            ))


class SameHostPublicationLockTests(unittest.TestCase):
    PROFILE = "TOM-LOCK-TEST-PROFILE"

    def _descriptor(self) -> dict:
        import hashlib
        seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
        return attach_hash({
            "schema": "TOMAGI-IMMUTABLE-STORE-DESCRIPTOR-1.0",
            "profile": self.PROFILE,
            "seed_sha256": "sha256:" + hashlib.sha256(seed).hexdigest(),
            "namespaces": ["commits"],
            "head_namespace": "commits",
            "record_encoding": "canonical-json-plus-lf",
            "publication_rule": "write-immutable-records-then-cas-head",
        })

    def test_thread_contenders_cannot_both_publish_from_same_expected_head(self):
        seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            store = ImmutablePublicationStore.initialize(Path(td) / "store", self._descriptor(), seed)
            publications = [_publication(self.PROFILE, 0, None, "a"),
                            _publication(self.PROFILE, 0, None, "b")]
            barrier = threading.Barrier(2)
            results: list[str] = []
            lock = threading.Lock()

            def worker(publication):
                barrier.wait()
                try:
                    store.apply_publication(publication)
                    outcome = "success"
                except ValueError as exc:
                    outcome = "stale" if "stale publication head" in str(exc) else "other"
                with lock:
                    results.append(outcome)

            threads = [threading.Thread(target=worker, args=(p,)) for p in publications]
            for thread in threads: thread.start()
            for thread in threads: thread.join(10)
            self.assertEqual(sorted(results), ["stale", "success"])

    @unittest.skipIf(os.name == "nt", "fork-style multiprocess regression runs on POSIX")
    def test_process_contenders_and_abnormal_exit_release_lock(self):
        seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
        context = mp.get_context("fork")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "store"
            ImmutablePublicationStore.initialize(root, self._descriptor(), seed)
            start = context.Event()
            queue = context.Queue()
            processes = [
                context.Process(target=_process_publish,
                                args=(str(root), _publication(self.PROFILE, 0, None, tag), start, queue))
                for tag in ("a", "b")
            ]
            for process in processes: process.start()
            start.set()
            results = [queue.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(10)
                self.assertFalse(process.is_alive())
            kinds = sorted(item[0] for item in results)
            self.assertEqual(kinds, ["error", "success"])
            self.assertTrue(any("stale publication head" in item[-1] for item in results if item[0] == "error"))

            # A dead publisher cannot strand the OS lock.
            dying = context.Process(target=_process_die_holding_lock, args=(str(root),))
            dying.start(); dying.join(10)
            self.assertFalse(dying.is_alive())
            current = ImmutablePublicationStore(root)._current_head()
            next_publication = _publication(self.PROFILE, 1, current, "after-abnormal-exit")
            self.assertEqual(
                ImmutablePublicationStore(root).apply_publication(next_publication),
                next_publication["replacement_head"],
            )


if __name__ == "__main__":
    unittest.main()
