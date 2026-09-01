from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .compiler import compile_file
from .format import load
from .knowledge import nineteen_demo
from .core import Opcode, run


def _state_dict(state):
    return {name: getattr(state, name) for name in state.__dataclass_fields__}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tomagi", description="TOMAGI 1.0 deterministic operator machine")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="compile JSON program to .tmg")
    p_compile.add_argument("source")
    p_compile.add_argument("destination")

    p_run = sub.add_parser("run", help="execute a .tmg program")
    p_run.add_argument("program")
    p_run.add_argument("--ticks", type=int)
    p_run.add_argument("--trace", action="store_true")
    p_run.add_argument("--output")

    p_inspect = sub.add_parser("inspect", help="inspect a .tmg program")
    p_inspect.add_argument("program")

    p_knowledge = sub.add_parser("nineteen", help="run the source-derived 19/three-pulse inference")
    p_knowledge.add_argument("--output")

    args = parser.parse_args(argv)
    if args.command == "compile":
        program = compile_file(args.source, args.destination)
        print(json.dumps({"cells": len(program.cells), "entry": program.entry,
                          "seed": program.seed, "default_ticks": program.default_ticks}, indent=2))
        return 0
    if args.command == "run":
        program = load(args.program)
        state, trace = run(program, ticks=args.ticks, trace=args.trace)
        result = {"state": _state_dict(state), "trace": trace}
        text = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    if args.command == "inspect":
        program = load(args.program)
        result = {
            "cells": len(program.cells), "entry": program.entry, "seed": program.seed,
            "default_ticks": program.default_ticks,
            "initial_state": _state_dict(program.initial_state),
            "opcodes": [Opcode(c.opcode).name for c in program.cells],
            "keys": [f"0x{c.key_u64:016x}" for c in program.cells],
        }
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "nineteen":
        result = nineteen_demo()
        data = {"output": result.output, "trace": result.trace}
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
