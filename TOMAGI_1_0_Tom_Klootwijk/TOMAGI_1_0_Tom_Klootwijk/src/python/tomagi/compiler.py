"""Compile literal TOMAGI JSON into the portable .tmg binary."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import verify_hash
from .core import Cell, Opcode, Program, State, OPCODE_BY_NAME, pack_key_contiguous, key_as_u64
from .format import dump
from .genome import lower_definition_genome


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


def _opcode(value: Any) -> int:
    if isinstance(value, str):
        try:
            return int(OPCODE_BY_NAME[value.upper()])
        except KeyError as exc:
            raise ValueError(f"unknown opcode {value}") from exc
    return int(Opcode(_int(value)))


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
        if "content_hash" not in definition:
            raise ValueError(f"definition missing content_hash: {ident}")
        if not verify_hash(definition):
            raise ValueError(f"definition hash mismatch: {ident}")

    indegree = {ident: 0 for ident in by_id}
    children: dict[str, list[str]] = {ident: [] for ident in by_id}
    for ident, definition in by_id.items():
        seen: set[str] = set()
        ordered_dependencies: list[str] = []
        for dep_value in definition.get("dependencies", []):
            dep = str(dep_value)
            if dep not in by_id:
                raise ValueError(f"unknown dependency {dep} from {ident}")
            if dep in seen:
                raise ValueError(f"duplicate dependency {dep} from {ident}")
            seen.add(dep)
            ordered_dependencies.append(dep)
            indegree[ident] += 1
            children[dep].append(ident)
        parameters = definition.get("parameters")
        if isinstance(parameters, dict) and "dependency_hashes" in parameters:
            declared = parameters["dependency_hashes"]
            actual = [str(by_id[dep]["content_hash"]) for dep in ordered_dependencies]
            if declared != actual:
                raise ValueError(f"definition dependency hash mismatch: {ident}")

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


def compile_document(
    document: dict[str, Any], *, base_dir: str | Path | None = None
) -> Program:
    if document.get("tomagi_version") != "1.0.0":
        raise ValueError("tomagi_version must be 1.0.0")

    definitions = document.get("definitions", [])
    definition_order(definitions)
    ids = {str(d["id"]) for d in definitions}
    definitions_by_id = {str(d["id"]): d for d in definitions}

    raw_cells = document.get("cells")
    if raw_cells is None:
        entry_definition = str(document.get("entry", ""))
        return lower_definition_genome(
            definitions, entry_definition, base_dir=base_dir
        )
    if not raw_cells:
        raise ValueError("program requires cells")
    prepared: list[dict[str, Any]] = []
    for index, c in enumerate(raw_cells):
        ident = str(c.get("id", f"cell:{index}"))
        definition_ref = c.get("definition_ref")
        if definition_ref and definition_ref not in ids:
            raise ValueError(f"cell {ident} references unknown definition {definition_ref}")
        hi, lo = _key_from_json(c["key"])
        definition = (
            definitions_by_id[str(definition_ref)] if definition_ref else None
        )
        if definition and definition.get("kind") == "tomagi_cell_operation":
            parameters = definition.get("parameters")
            required = ("opcode", "flags", "args", "next", "payload", "aux")
            if not isinstance(parameters, dict) or any(
                name not in parameters for name in required
            ):
                raise ValueError(
                    f"cell operation definition {definition_ref} requires "
                    "opcode, flags, args, next, payload and aux"
                )
            definition_args = list(parameters["args"])
            definition_next = list(parameters["next"])
            normalizers = {
                "op": (_opcode, parameters["opcode"], "opcode"),
                "flags": (_int, parameters["flags"], "flags"),
                "args": (
                    lambda values: [_int(value) for value in values],
                    definition_args,
                    "args",
                ),
                "next": (
                    lambda values: [str(value) for value in values],
                    definition_next,
                    "next",
                ),
                "payload": (_int, parameters["payload"], "payload"),
                "aux": (_int, parameters["aux"], "aux"),
            }
            for cell_field, (normalize, expected, definition_field) in normalizers.items():
                if cell_field not in c:
                    continue
                if normalize(c[cell_field]) != normalize(expected):
                    raise ValueError(
                        f"cell {ident} {definition_field} does not match "
                        f"definition {definition_ref}"
                    )
            op_value = parameters["opcode"]
            flags_value = parameters["flags"]
            args = definition_args
            next_values = definition_next
            payload_value = parameters["payload"]
            aux_value = parameters["aux"]
        else:
            missing = [name for name in ("op", "args", "next") if name not in c]
            if missing:
                raise ValueError(
                    f"raw cell {ident} requires " + ", ".join(missing)
                )
            op_value = c["op"]
            flags_value = c.get("flags", 0)
            args = list(c["args"])
            next_values = list(c["next"])
            payload_value = c.get("payload", 0)
            aux_value = c.get("aux", 0)

        opcode = _opcode(op_value)
        if len(args) != 4:
            raise ValueError(f"cell {ident} requires four args")
        if len(next_values) != 2:
            raise ValueError(f"cell {ident} requires two successor IDs")
        prepared.append({
            "id": ident, "key_hi": hi, "key_lo": lo, "opcode": opcode,
            "flags": _int(flags_value), "args": [_int(x) for x in args],
            "next_ids": [str(next_values[0]), str(next_values[1])],
            "payload": _int(payload_value), "aux": _int(aux_value),
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
    source_path = Path(source)
    document = json.loads(source_path.read_text(encoding="utf-8"))
    program = compile_document(document, base_dir=source_path.parent)
    dump(program, destination)
    return program
