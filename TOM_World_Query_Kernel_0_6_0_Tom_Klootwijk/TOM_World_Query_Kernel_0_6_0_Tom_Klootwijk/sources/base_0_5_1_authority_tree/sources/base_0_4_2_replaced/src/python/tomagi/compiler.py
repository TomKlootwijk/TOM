"""Compile literal TOMAGI JSON into the portable .tmg binary.

The module preserves the original TOMAGI 1.0 handwritten-cell format and adds
just the finite seeded-definition operations required by the World & Query
Kernel documentation artifact chain.  The binary ABI remains unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import base64
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import canonical_bytes, verify_hash
from .core import (
    Cell,
    FLAG_EMIT_BIG_ENDIAN,
    FLAG_EMIT_COUNT_SHIFT,
    FLAG_EMIT_HALT,
    OPCODE_BY_NAME,
    Opcode,
    Program,
    PROGRAM_FLAG_EMIT_BYTES,
    PROGRAM_FLAG_SEEDED_PROFILE,
    State,
    i32,
    key_as_u64,
    pack_key_contiguous,
    u32,
)
from .format import dump, dumps, load

CANONICAL_SEED_LENGTH = 244
CANONICAL_SEED_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
SEEDED_PROFILE_ID = "TOM-SEEDED-COMPILATION-1.0"
PHASE_ORDER = (
    "parse", "normalize", "resolve", "construct", "transform", "support",
    "compatibility", "guard", "event", "transition", "lineage",
)


def _int(value: Any) -> int:
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _key_from_json(value: Any) -> tuple[int, int]:
    if isinstance(value, str):
        word = int(value, 0)
        return (word >> 32) & 0xFFFFFFFF, word & 0xFFFFFFFF
    if isinstance(value, int):
        return (value >> 32) & 0xFFFFFFFF, value & 0xFFFFFFFF
    if isinstance(value, dict):
        return pack_key_contiguous(
            _int(value.get("rho", 0)), _int(value.get("theta", 0)),
            _int(value.get("tick", 0)), _int(value.get("phi", 0)),
        )
    raise TypeError("cell key must be an integer, hex string, or rho/theta/tick/phi object")


def _state_from_json(value: Mapping[str, Any]) -> State:
    unknown = sorted(set(value) - set(State.__dataclass_fields__))
    if unknown:
        raise ValueError("unknown State64 fields: " + ", ".join(unknown))
    fields = {name: _int(value.get(name, 0)) for name in State.__dataclass_fields__}
    return State(**fields)


def definition_order(definitions: list[dict[str, Any]]) -> list[str]:
    """Return a stable topological order for literal definition records."""
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


def _compile_legacy_document(document: Mapping[str, Any]) -> Program:
    if document.get("tomagi_version") != "1.0.0":
        raise ValueError("tomagi_version must be 1.0.0")

    definitions = document.get("definitions", [])
    if not isinstance(definitions, list):
        raise ValueError("definitions must be an array")
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


@dataclass(frozen=True, slots=True)
class _Typed:
    type_name: str
    value: Any


@dataclass(frozen=True, slots=True)
class _CellSpec:
    ident: str
    key_hi: int
    key_lo: int
    opcode: int
    flags: int
    args: tuple[int, int, int, int]
    next_ids: tuple[str, str]
    payload: int
    aux: int
    source_definition: str
    origin: Mapping[str, Any]

    @property
    def key(self) -> int:
        return key_as_u64(self.key_hi, self.key_lo)


@dataclass(frozen=True, slots=True)
class _Graph:
    cells: tuple[_CellSpec, ...]
    entry_id: str


@dataclass(frozen=True, slots=True)
class _ProgramSpec:
    graph: _Graph
    state: State
    entry_id: str
    seed: int
    default_ticks: int
    flags: int


@dataclass(frozen=True, slots=True)
class SeededCompilationResult:
    program: Program
    definition_order: tuple[str, ...]
    crosswalk: tuple[Mapping[str, Any], ...]
    report: Mapping[str, Any]


def _decode_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    if not isinstance(value, Mapping):
        raise TypeError("bytes literal must be a string or encoding object")
    encoding = str(value.get("encoding", "utf8")).lower()
    data = value.get("data", "")
    if not isinstance(data, str):
        raise TypeError("encoded bytes data must be a string")
    if encoding in {"utf8", "utf-8"}:
        return data.encode("utf-8")
    if encoding == "ascii":
        return data.encode("ascii")
    if encoding == "hex":
        return bytes.fromhex(data)
    if encoding == "base64":
        return base64.b64decode(data, validate=True)
    raise ValueError(f"unsupported bytes encoding {encoding}")


def _validate_seed(seed: bytes) -> str:
    if seed.endswith((b"\n", b"\r")):
        raise ValueError("canonical seed must not have a terminal line ending")
    try:
        text = seed.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("canonical seed must be ASCII") from exc
    digest = hashlib.sha256(seed).hexdigest()
    if len(seed) != CANONICAL_SEED_LENGTH:
        raise ValueError("canonical seed length mismatch")
    if digest != CANONICAL_SEED_SHA256:
        raise ValueError("canonical seed hash mismatch")
    return text


def _seeded_order(definitions: Sequence[Mapping[str, Any]]) -> tuple[list[str], dict[str, Mapping[str, Any]]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    slots: dict[tuple[int, int], str] = {}
    ranks: dict[str, tuple[int, int, str]] = {}
    for definition in definitions:
        if not isinstance(definition, Mapping):
            raise ValueError("definitions must contain objects")
        ident = str(definition.get("id", ""))
        if not ident or ident in by_id:
            raise ValueError(f"duplicate or empty definition id {ident!r}")
        if not verify_hash(dict(definition)):
            raise ValueError(f"definition hash mismatch: {ident}")
        phase = str(definition.get("phase", ""))
        if phase not in PHASE_ORDER:
            raise ValueError(f"definition {ident} has unknown phase {phase}")
        order = definition.get("order")
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            raise ValueError(f"definition {ident} has invalid order")
        slot = (PHASE_ORDER.index(phase), order)
        if slot in slots:
            raise ValueError(f"ambiguous phase/order slot for {ident} and {slots[slot]}")
        slots[slot] = ident
        ranks[ident] = (slot[0], slot[1], ident)
        by_id[ident] = definition

    indegree = {ident: 0 for ident in by_id}
    children = {ident: [] for ident in by_id}
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
    ready = sorted((ranks[i], i) for i, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        _, ident = ready.pop(0)
        ordered.append(ident)
        for child in sorted(children[ident], key=ranks.__getitem__):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append((ranks[child], child))
                ready.sort()
    if len(ordered) != len(by_id):
        raise ValueError("definition dependency cycle")
    for ident, definition in by_id.items():
        for dep_value in definition.get("dependencies", []):
            dep = str(dep_value)
            if ranks[dep] >= ranks[ident]:
                raise ValueError(f"definition order violation: {ident} depends on {dep}")
    return ordered, by_id


def _closure(root: str, by_id: Mapping[str, Mapping[str, Any]]) -> set[str]:
    if root not in by_id:
        raise ValueError(f"root definition {root} does not exist")
    selected: set[str] = set()
    stack = [root]
    while stack:
        ident = stack.pop()
        if ident in selected:
            continue
        selected.add(ident)
        stack.extend(str(dep) for dep in by_id[ident].get("dependencies", []))
    return selected


def _lower(spec: _ProgramSpec) -> tuple[Program, tuple[Mapping[str, Any], ...]]:
    cells = sorted(spec.graph.cells, key=lambda c: c.key)
    if not cells:
        raise ValueError("seeded program graph is empty")
    ids = [cell.ident for cell in cells]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate cell ID")
    keys = [cell.key for cell in cells]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate canonical cell key")
    by_id = {cell.ident: i for i, cell in enumerate(cells)}
    if spec.entry_id not in by_id:
        raise ValueError(f"entry cell {spec.entry_id} does not exist")
    lowered: list[Cell] = []
    crosswalk: list[Mapping[str, Any]] = []
    for index, cell in enumerate(cells):
        for target in cell.next_ids:
            if target not in by_id:
                raise ValueError(f"cell {cell.ident} references unknown successor {target}")
        lowered.append(Cell(
            cell.key_hi, cell.key_lo, cell.opcode, cell.flags,
            *cell.args,
            by_id[cell.next_ids[0]], by_id[cell.next_ids[1]],
            cell.payload, cell.aux,
        ))
        crosswalk.append({
            "cell_index": index,
            "cell_id": cell.ident,
            "key": f"0x{cell.key:016x}",
            "opcode": Opcode(cell.opcode).name,
            "definition_id": cell.source_definition,
            "next0": by_id[cell.next_ids[0]],
            "next1": by_id[cell.next_ids[1]],
            "flags": cell.flags,
            "payload": cell.payload,
            "aux": cell.aux,
            "origin": dict(cell.origin),
        })
    state = replace(spec.state)
    state.cell = by_id[spec.entry_id]
    return Program(
        cells=lowered,
        entry=by_id[spec.entry_id],
        seed=spec.seed,
        default_ticks=spec.default_ticks,
        initial_state=state,
        flags=spec.flags,
    ), tuple(crosswalk)


def _compile_seeded_document(document: Mapping[str, Any], *, seed_bytes: bytes) -> SeededCompilationResult:
    if document.get("tomagi_version") != "1.0.0":
        raise ValueError("tomagi_version must be 1.0.0")
    if document.get("compilation_profile") != SEEDED_PROFILE_ID:
        raise ValueError(f"compilation_profile must be {SEEDED_PROFILE_ID}")
    if "cells" in document:
        raise ValueError("seeded mode rejects top-level handwritten cells")
    seed_text = _validate_seed(seed_bytes)
    definitions = document.get("definitions")
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("seeded program requires definitions")
    order, by_id = _seeded_order(definitions)
    root = str(document.get("root_definition", ""))
    selected = _closure(root, by_id)
    selected_order = [ident for ident in order if ident in selected]
    values: dict[str, _Typed] = {}

    for ident in selected_order:
        definition = by_id[ident]
        op_record = definition.get("operation")
        if not isinstance(op_record, Mapping):
            raise ValueError(f"definition {ident} requires an operation")
        op = str(op_record.get("op", ""))
        params = definition.get("parameters", {})
        if not isinstance(params, Mapping):
            raise ValueError(f"definition {ident} parameters must be an object")
        deps = [str(dep) for dep in definition.get("dependencies", [])]
        dep_values = [values[dep] for dep in deps]
        for token in definition.get("seed_tokens", []):
            if str(token) not in seed_text:
                raise ValueError(f"definition {ident} references seed token {token!r} not present in seed")

        if op == "seed.bytes":
            if deps:
                raise ValueError("seed.bytes must not have dependencies")
            result = _Typed("bytes", seed_bytes)
        elif op == "seed.tokens":
            if len(dep_values) != 1 or dep_values[0].type_name != "bytes" or dep_values[0].value != seed_bytes:
                raise ValueError("seed.tokens requires canonical seed.bytes")
            result = _Typed("record", {
                "grammar_id": "TOM-SEED-GRAMMAR-1.0",
                "bytes": len(seed_bytes),
                "sha256": hashlib.sha256(seed_bytes).hexdigest(),
                "text": seed_text,
            })
        elif op == "literal":
            result_type = str(params.get("result_type", definition.get("codomain", "record")))
            raw = params.get("value")
            if result_type == "bytes":
                value = _decode_bytes(raw)
            elif result_type == "string":
                value = str(raw)
            elif result_type == "bool":
                if not isinstance(raw, bool):
                    raise TypeError("bool literal must be true or false")
                value = raw
            elif result_type == "i32":
                value = i32(_int(raw))
            elif result_type == "u32":
                value = u32(_int(raw))
            elif result_type == "record":
                if not isinstance(raw, Mapping):
                    raise TypeError("record literal must be an object")
                value = dict(raw)
            else:
                raise ValueError(f"literal result type {result_type} is unsupported")
            result = _Typed(result_type, value)
        elif op == "state64.construct":
            fields = params.get("fields", {})
            if not isinstance(fields, Mapping):
                raise ValueError("state64.construct fields must be an object")
            result = _Typed("state64", _state_from_json(fields))
        elif op == "hash.sha256":
            if len(dep_values) != 1 or dep_values[0].type_name != "bytes":
                raise TypeError("hash.sha256 requires one bytes dependency")
            digest = hashlib.sha256(dep_values[0].value).hexdigest()
            result = _Typed("string", ("sha256:" if params.get("prefix", True) else "") + digest)
        elif op == "assert.equal":
            if len(dep_values) != 2:
                raise ValueError("assert.equal requires two dependencies")
            if dep_values[0].value != dep_values[1].value:
                raise ValueError(f"assert.equal failed in definition {ident}")
            result = _Typed("bool", True)
        elif op == "emit.graph":
            if len(dep_values) != 1 or dep_values[0].type_name != "bytes":
                raise TypeError("emit.graph requires one bytes dependency")
            data = dep_values[0].value
            if not data:
                raise ValueError("emit.graph cannot lower empty bytes")
            chunk_size = _int(params.get("chunk_bytes", 4))
            if not 1 <= chunk_size <= 4:
                raise ValueError("emit.graph chunk_bytes must be in 1..4")
            byte_order = str(params.get("byte_order", "little"))
            if byte_order not in {"little", "big"}:
                raise ValueError("emit.graph byte_order must be little or big")
            count = math.ceil(len(data) / chunk_size)
            prefix = str(params.get("id_prefix", "cell:emit"))
            width = max(1, len(str(count - 1)))
            ids = [f"{prefix}:{i:0{width}d}" for i in range(count)]
            base = params.get("key_base", {})
            if not isinstance(base, Mapping):
                raise ValueError("emit.graph key_base must be an object")
            field = str(params.get("key_field", "rho"))
            if field not in {"rho", "theta", "tick", "phi"}:
                raise ValueError("emit.graph key_field is invalid")
            aux_base = _int(params.get("aux_base", 0))
            halt_last = bool(params.get("halt_last", True))
            specs: list[_CellSpec] = []
            for index in range(count):
                offset = index * chunk_size
                chunk = data[offset:offset + chunk_size]
                coords = {name: _int(base.get(name, 0)) for name in ("rho", "theta", "tick", "phi")}
                coords[field] += index
                hi, lo = pack_key_contiguous(**coords)
                if byte_order == "little":
                    payload = int.from_bytes(chunk.ljust(4, b"\0"), "little")
                else:
                    payload = int.from_bytes(chunk.rjust(4, b"\0"), "big")
                flags = len(chunk) << FLAG_EMIT_COUNT_SHIFT
                if byte_order == "big":
                    flags |= FLAG_EMIT_BIG_ENDIAN
                if halt_last and index == count - 1:
                    flags |= FLAG_EMIT_HALT
                successor = ids[index + 1] if index + 1 < count else ids[index]
                specs.append(_CellSpec(
                    ident=ids[index],
                    key_hi=hi,
                    key_lo=lo,
                    opcode=int(Opcode.EMIT),
                    flags=u32(flags),
                    args=(0, 0, 0, 0),
                    next_ids=(successor, successor),
                    payload=u32(payload),
                    aux=u32(aux_base + index),
                    source_definition=ident,
                    origin={
                        "definition": ident,
                        "byte_offset": offset,
                        "byte_count": len(chunk),
                        "byte_order": byte_order,
                    },
                ))
            result = _Typed("cell_graph", _Graph(tuple(specs), ids[0]))
        elif op == "program.construct":
            graphs = [value.value for value in dep_values if value.type_name == "cell_graph"]
            states = [value.value for value in dep_values if value.type_name == "state64"]
            guards = [value.value for value in dep_values if value.type_name == "bool"]
            if len(graphs) != 1 or len(states) > 1:
                raise ValueError("program.construct requires one graph and at most one state")
            if guards and not all(guards):
                raise ValueError("program.construct guard dependency is false")
            graph = graphs[0]
            state = states[0] if states else State()
            entry = str(params.get("entry", graph.entry_id))
            flags = u32(_int(params.get("flags", 0))) | PROGRAM_FLAG_SEEDED_PROFILE
            if bool(params.get("emit_bytes", False)):
                flags |= PROGRAM_FLAG_EMIT_BYTES
            result = _Typed("program", _ProgramSpec(
                graph=graph,
                state=state,
                entry_id=entry,
                seed=u32(_int(params.get("seed", 0))),
                default_ticks=_int(params.get("default_ticks", len(graph.cells))),
                flags=flags,
            ))
        else:
            raise ValueError(f"unknown seeded definition operation {op}")

        declared = str(definition.get("codomain", result.type_name))
        if result.type_name != declared:
            raise TypeError(f"definition {ident} produced {result.type_name}, declared {declared}")
        values[ident] = result

    root_value = values[root]
    if root_value.type_name != "program":
        raise TypeError("root definition must produce program")
    program, crosswalk = _lower(root_value.value)
    report = {
        "schema": "TOM-SEEDED-COMPILE-REPORT-1.0",
        "profile": SEEDED_PROFILE_ID,
        "tomagi_abi": "1.0",
        "seed": {
            "bytes": len(seed_bytes),
            "sha256": hashlib.sha256(seed_bytes).hexdigest(),
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
        },
        "root_definition": root,
        "definition_order": order,
        "evaluated_definition_order": selected_order,
        "definition_hashes": {ident: str(by_id[ident]["content_hash"]) for ident in order},
        "cell_count": len(program.cells),
        "entry": program.entry,
        "program_flags": program.flags,
        "crosswalk": list(crosswalk),
    }
    return SeededCompilationResult(program, tuple(order), crosswalk, report)


def compile_document(
    document: Mapping[str, Any],
    *,
    seed_bytes: bytes | None = None,
    token_registry: Mapping[str, Any] | None = None,
) -> Program:
    if document.get("compilation_profile") == SEEDED_PROFILE_ID:
        if seed_bytes is None:
            raise ValueError("seeded compile_document requires seed_bytes")
        return _compile_seeded_document(document, seed_bytes=seed_bytes).program
    return _compile_legacy_document(document)


def compile_file_result(source: str | Path, destination: str | Path) -> SeededCompilationResult | None:
    source_path = Path(source).resolve()
    destination_path = Path(destination)
    document = json.loads(source_path.read_text(encoding="utf-8"))
    if document.get("compilation_profile") != SEEDED_PROFILE_ID:
        program = _compile_legacy_document(document)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        dump(program, destination_path)
        return None

    seed_info = document.get("seed_genome")
    if not isinstance(seed_info, Mapping):
        raise ValueError("seeded source requires seed_genome")
    seed_path = (source_path.parent / str(seed_info.get("path", ""))).resolve()
    seed_bytes = seed_path.read_bytes()
    _validate_seed(seed_bytes)
    if _int(seed_info.get("bytes", -1)) != CANONICAL_SEED_LENGTH:
        raise ValueError("seed_genome declared byte length mismatch")
    if str(seed_info.get("sha256", "")) != CANONICAL_SEED_SHA256:
        raise ValueError("seed_genome declared hash mismatch")

    result = _compile_seeded_document(document, seed_bytes=seed_bytes)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    blob = dumps(result.program)
    destination_path.write_bytes(blob)
    sidecar = dict(result.report)
    sidecar.update({
        "source_file": source_path.name,
        "source_sha256": _sha256_bytes(source_path.read_bytes()),
        "program_file": destination_path.name,
        "program_bytes": len(blob),
        "program_sha256": _sha256_bytes(blob),
    })
    destination_path.with_suffix(destination_path.suffix + ".compile.json").write_bytes(
        canonical_bytes(sidecar) + b"\n"
    )
    return result


def compile_file(source: str | Path, destination: str | Path) -> Program:
    result = compile_file_result(source, destination)
    if result is not None:
        return result.program
    return load(destination)
