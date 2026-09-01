"""Compile literal TOMAGI JSON into the portable .tmg binary."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import verify_hash
from .core import Cell, Opcode, Program, State, OPCODE_BY_NAME, pack_key_contiguous, key_as_u64
from .format import dump


def _int(value: Any) -> int:
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _key_from_json(value: Any) -> tuple[int, int]:
    if isinstance(value, str):
        word = int(value, 0)
        return (word >> 32) & 0xFFFFFFFF, word & 0xFFFFFFFF
    if isinstance(value, dict):
        return pack_key_contiguous(
            _int(value.get("rho", 0)), _int(value.get("theta", 0)),
            _int(value.get("tick", 0)), _int(value.get("phi", 0)),
        )
    raise TypeError("cell key must be a hex string or a rho/theta/tick/phi object")


def _state_from_json(value: dict[str, Any]) -> State:
    fields = {name: _int(value.get(name, 0)) for name in State.__dataclass_fields__}
    return State(**fields)


def definition_order(definitions: list[dict[str, Any]]) -> list[str]:
    """Return a stable topological order for literal definition records.

    Definition cycles are not a runtime safety layer; they would make evaluation
    order ambiguous.  TOMAGI 1.0 therefore accepts only explicitly ordered finite
    definition graphs.
    """
    by_id: dict[str, dict[str, Any]] = {}
    input_rank: dict[str, int] = {}
    for rank, definition in enumerate(definitions):
        ident = str(definition["id"])
        if ident in by_id:
            raise ValueError(f"duplicate definition id {ident}")
        by_id[ident] = definition
        input_rank[ident] = rank
        if "content_hash" in definition and not verify_hash(definition):
            raise ValueError(f"definition hash mismatch: {ident}")

    indegree = {ident: 0 for ident in by_id}
    children: dict[str, list[str]] = {ident: [] for ident in by_id}
    for ident, definition in by_id.items():
        seen: set[str] = set()
        for dep_value in definition.get("dependencies", []):
            dep = str(dep_value)
            if dep not in by_id:
                raise ValueError(f"unknown dependency {dep} from {ident}")
            if dep in seen:
                raise ValueError(f"duplicate dependency {dep} from {ident}")
            seen.add(dep)
            indegree[ident] += 1
            children[dep].append(ident)

    ready = sorted((input_rank[i], i) for i, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        _, ident = ready.pop(0)
        order.append(ident)
        for child in sorted(children[ident], key=input_rank.__getitem__):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append((input_rank[child], child))
                ready.sort()
    if len(order) != len(by_id):
        cyclic = sorted(ident for ident, degree in indegree.items() if degree > 0)
        raise ValueError("definition dependency cycle: " + ", ".join(cyclic))
    return order


def compile_document(document: dict[str, Any]) -> Program:
    if document.get("tomagi_version") != "1.0.0":
        raise ValueError("tomagi_version must be 1.0.0")

    definitions = document.get("definitions", [])
    definition_order(definitions)
    ids = {str(d["id"]) for d in definitions}

    raw_cells = document.get("cells", [])
    if not raw_cells:
        raise ValueError("program requires cells")
    prepared: list[dict[str, Any]] = []
    for index, c in enumerate(raw_cells):
        ident = str(c.get("id", f"cell:{index}"))
        if c.get("definition_ref") and c["definition_ref"] not in ids:
            raise ValueError(f"cell {ident} references unknown definition {c['definition_ref']}")
        hi, lo = _key_from_json(c["key"])
        op_value = c["op"]
        if isinstance(op_value, str):
            try:
                opcode = int(OPCODE_BY_NAME[op_value.upper()])
            except KeyError as exc:
                raise ValueError(f"unknown opcode {op_value}") from exc
        else:
            opcode = int(Opcode(_int(op_value)))
        args = list(c.get("args", [0, 0, 0, 0]))
        if len(args) != 4:
            raise ValueError(f"cell {ident} requires four args")
        nxt = list(c.get("next", [ident, ident]))
        if len(nxt) != 2:
            raise ValueError(f"cell {ident} requires two successor IDs")
        prepared.append({
            "id": ident, "key_hi": hi, "key_lo": lo, "opcode": opcode,
            "flags": _int(c.get("flags", 0)), "args": [_int(x) for x in args],
            "next_ids": [str(nxt[0]), str(nxt[1])],
            "payload": _int(c.get("payload", 0)), "aux": _int(c.get("aux", 0)),
        })

    prepared.sort(key=lambda c: key_as_u64(c["key_hi"], c["key_lo"]))
    index_by_id = {c["id"]: i for i, c in enumerate(prepared)}
    if len(index_by_id) != len(prepared):
        raise ValueError("cell IDs must be unique")
    for c in prepared:
        for target in c["next_ids"]:
            if target not in index_by_id:
                raise ValueError(f"cell {c['id']} references unknown successor {target}")

    cells = [
        Cell(
            c["key_hi"], c["key_lo"], c["opcode"], c["flags"],
            c["args"][0], c["args"][1], c["args"][2], c["args"][3],
            index_by_id[c["next_ids"][0]], index_by_id[c["next_ids"][1]],
            c["payload"], c["aux"],
        )
        for c in prepared
    ]
    entry_id = str(document.get("entry", prepared[0]["id"]))
    if entry_id not in index_by_id:
        raise ValueError(f"entry cell {entry_id} does not exist")
    state = _state_from_json(document.get("initial_state", {}))
    state.cell = index_by_id[entry_id]
    return Program(
        cells=cells,
        entry=index_by_id[entry_id],
        seed=_int(document.get("seed", 0)),
        default_ticks=_int(document.get("default_ticks", len(cells))),
        initial_state=state,
        flags=_int(document.get("flags", 0)),
    )


def compile_file(source: str | Path, destination: str | Path) -> Program:
    document = json.loads(Path(source).read_text(encoding="utf-8"))
    program = compile_document(document)
    dump(program, destination)
    return program
