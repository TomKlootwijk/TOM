"""Content-addressed definition evaluation and deterministic byte lowering.

The evaluator is deliberately representation-agnostic.  It knows literal byte
algebra, authenticated TOMAGI traces, record selection, rational affine field
projection, and safe record templates.  It contains no artifact-format,
geometry, or output-token vocabulary; those choices belong to hashed definitions.
"""
from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, TypeAlias

from .canonical import verify_hash
from .core import Cell, FLAG_EMIT_HALT, Opcode, Program, State, run
from .format import dumps, loads
from .project import MATERIALIZATION_PROFILE, encode_emit_byte_count


LITERAL_UTF8 = "literal_utf8"
LITERAL_HEX = "literal_hex"
CONCAT = "concat"
REPEAT = "repeat"
AUTHENTICATED_TRACE = "authenticated_trace"
SELECT_RECORDS = "select_records"
PROJECT_FIELDS = "project_fields"
FORMAT_RECORDS = "format_records"
GENOME_KINDS = frozenset({
    LITERAL_UTF8,
    LITERAL_HEX,
    CONCAT,
    REPEAT,
    AUTHENTICATED_TRACE,
    SELECT_RECORDS,
    PROJECT_FIELDS,
    FORMAT_RECORDS,
})
GENOME_PROGRAM_FLAG = 0x314E4547  # ASCII "GEN1" in little-endian storage.

Record: TypeAlias = dict[str, int]
RecordTable: TypeAlias = tuple[Record, ...]
GenomeValue: TypeAlias = bytes | RecordTable
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class EvaluatedGenome:
    entry: str
    content_hash: str
    data: bytes


@dataclass(frozen=True, slots=True)
class EvaluatedRecords:
    entry: str
    content_hash: str
    records: RecordTable


def _definition_map(definitions: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for definition in definitions:
        ident = str(definition["id"])
        if ident in by_id:
            raise ValueError(f"duplicate definition id {ident}")
        if "content_hash" not in definition:
            raise ValueError(f"definition missing content_hash: {ident}")
        if not verify_hash(definition):
            raise ValueError(f"definition hash mismatch: {ident}")
        by_id[ident] = definition
    return by_id


def _checked_dependency_hashes(
    definition: dict[str, Any],
    dependencies: list[str],
    by_id: dict[str, dict[str, Any]],
) -> None:
    parameters = definition.get("parameters", {})
    declared = parameters.get("dependency_hashes") if isinstance(parameters, dict) else None
    if not isinstance(declared, list) or not all(isinstance(value, str) for value in declared):
        raise ValueError(f"definition {definition['id']} requires dependency_hashes")
    actual = [str(by_id[ident]["content_hash"]) for ident in dependencies]
    if declared != actual:
        raise ValueError(f"definition {definition['id']} dependency hash mismatch")


def _as_bytes(value: GenomeValue, ident: str) -> bytes:
    if not isinstance(value, bytes):
        raise ValueError(f"definition {ident} requires byte-string dependencies")
    return value


def _as_records(value: GenomeValue, ident: str) -> RecordTable:
    if not isinstance(value, tuple):
        raise ValueError(f"definition {ident} requires a record-table dependency")
    return value


def _authenticated_file(
    base_dir: Path | None, path_text: Any, expected_hash: Any, label: str
) -> tuple[bytes, Path]:
    if base_dir is None:
        raise ValueError(f"{label} requires a definition document base directory")
    if not isinstance(path_text, str) or not path_text:
        raise ValueError(f"{label} path must be a non-empty string")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError(f"{label} sha256 must be 64 lower-case hexadecimal digits")
    relative = Path(path_text)
    if relative.is_absolute():
        raise ValueError(f"{label} path must be relative to the definition document")
    root = base_dir.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} path escapes the definition document directory") from exc
    try:
        data = candidate.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read authenticated {label} path {path_text}") from exc
    actual = sha256(data).hexdigest()
    if actual != expected_hash:
        raise ValueError(f"authenticated {label} hash mismatch")
    return data, candidate


def _state_dict(state: State) -> dict[str, int]:
    return {name: int(getattr(state, name)) for name in state.__dataclass_fields__}


def _authenticated_trace(parameters: dict[str, Any], base_dir: Path | None) -> RecordTable:
    trace_bytes, _ = _authenticated_file(
        base_dir, parameters.get("trace_path"), parameters.get("trace_sha256"), "trace"
    )
    program_bytes, _ = _authenticated_file(
        base_dir, parameters.get("program_path"), parameters.get("program_sha256"), "program"
    )
    source_bytes, source_path = _authenticated_file(
        base_dir, parameters.get("source_path"), parameters.get("source_sha256"), "source"
    )
    ticks = parameters.get("ticks")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 0:
        raise ValueError("authenticated_trace ticks must be a non-negative integer")
    try:
        document = json.loads(trace_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("authenticated trace is not UTF-8 JSON") from exc
    trace_key = parameters.get("trace_key", "trace")
    state_key = parameters.get("state_key", "state")
    if not isinstance(trace_key, str) or not isinstance(state_key, str):
        raise ValueError("authenticated_trace keys must be strings")
    if not isinstance(document, dict) or not isinstance(document.get(trace_key), list):
        raise ValueError("authenticated trace document has no record array")

    try:
        source_document = json.loads(source_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("authenticated source is not UTF-8 JSON") from exc
    if not isinstance(source_document, dict):
        raise ValueError("authenticated source is not a TOMAGI document object")
    required_source_hashes = parameters.get("source_definition_hashes")
    if not isinstance(required_source_hashes, list) or not all(
        isinstance(value, str) for value in required_source_hashes
    ):
        raise ValueError("authenticated_trace requires source_definition_hashes")
    source_definitions = source_document.get("definitions", [])
    if not isinstance(source_definitions, list):
        raise ValueError("authenticated source definitions must be an array")
    available_source_hashes = {
        definition.get("content_hash")
        for definition in source_definitions
        if isinstance(definition, dict)
    }
    missing_source_hashes = [
        value for value in required_source_hashes if value not in available_source_hashes
    ]
    if missing_source_hashes:
        raise ValueError("authenticated source does not contain the declared definition anchors")
    # Local import avoids the compiler -> genome module import cycle while proving
    # that the authenticated binary is exactly Compile(authenticated source).
    from .compiler import compile_document

    compiled_source = compile_document(source_document, base_dir=source_path.parent)
    if dumps(compiled_source) != program_bytes:
        raise ValueError("authenticated program is not the compiled source document")

    program = loads(program_bytes)
    final_state, replay = run(program, ticks=ticks, trace=True)
    records = document[trace_key]
    if replay != records:
        raise ValueError("authenticated trace records do not match program replay")
    if document.get(state_key) != _state_dict(final_state):
        raise ValueError("authenticated trace final state does not match program replay")

    normalized: list[Record] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"trace record {index} is not an object")
        converted: Record = {}
        for name, value in record.items():
            if not isinstance(name, str) or isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"trace record {index} is not an integer field map")
            converted[name] = value
        normalized.append(converted)
    return tuple(normalized)


def _select_records(records: RecordTable, parameters: dict[str, Any]) -> RecordTable:
    predicates = parameters.get("predicates", [])
    if not isinstance(predicates, list):
        raise ValueError("select_records predicates must be an array")

    def matches(record: Record) -> bool:
        for predicate in predicates:
            if not isinstance(predicate, dict):
                raise ValueError("select_records predicate must be an object")
            field = predicate.get("field")
            operator = predicate.get("operator")
            expected = predicate.get("value")
            if not isinstance(field, str) or field not in record:
                raise ValueError(f"select_records field {field!r} is absent")
            if isinstance(expected, bool) or not isinstance(expected, int):
                raise ValueError("select_records predicate value must be an integer")
            actual = record[field]
            operations = {
                "eq": actual == expected,
                "ne": actual != expected,
                "lt": actual < expected,
                "le": actual <= expected,
                "gt": actual > expected,
                "ge": actual >= expected,
            }
            if operator not in operations:
                raise ValueError(f"unsupported select_records operator {operator!r}")
            if not operations[operator]:
                return False
        return True

    selected = tuple(record for record in records if matches(record))
    start = parameters.get("start", 0)
    stop = parameters.get("stop")
    stride = parameters.get("stride", 1)
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise ValueError("select_records start must be a non-negative integer")
    if stop is not None and (isinstance(stop, bool) or not isinstance(stop, int) or stop < 0):
        raise ValueError("select_records stop must be null or a non-negative integer")
    if isinstance(stride, bool) or not isinstance(stride, int) or stride <= 0:
        raise ValueError("select_records stride must be a positive integer")
    return selected[start:stop:stride]


def _project_fields(records: RecordTable, parameters: dict[str, Any]) -> RecordTable:
    fields = parameters.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("project_fields requires a non-empty fields array")
    projected: list[Record] = []
    for record_index, record in enumerate(records):
        output: Record = {}
        for field in fields:
            if not isinstance(field, dict):
                raise ValueError("project_fields field must be an object")
            name = field.get("name")
            source = field.get("source")
            if not isinstance(name, str) or not _FIELD_NAME.fullmatch(name):
                raise ValueError(f"project_fields output name {name!r} is invalid")
            if name in output:
                raise ValueError(f"project_fields output name {name!r} is duplicated")
            if not isinstance(source, str) or source not in record:
                raise ValueError(
                    f"project_fields source {source!r} is absent at record {record_index}"
                )
            numerator = field.get("numerator", 1)
            denominator = field.get("denominator", 1)
            offset = field.get("offset", 0)
            rounding = field.get("rounding", "floor")
            integers = (numerator, denominator, offset)
            if any(isinstance(value, bool) or not isinstance(value, int) for value in integers):
                raise ValueError("project_fields affine coefficients must be integers")
            if denominator <= 0:
                raise ValueError("project_fields denominator must be positive")
            product = record[source] * numerator
            if rounding == "floor":
                quotient = product // denominator
            elif rounding == "trunc":
                quotient = abs(product) // denominator
                if product < 0:
                    quotient = -quotient
            else:
                raise ValueError(f"unsupported project_fields rounding {rounding!r}")
            output[name] = quotient + offset
        projected.append(output)
    return tuple(projected)


def _format_record(template: str, values: Record) -> str:
    formatter = string.Formatter()
    for _, field_name, format_spec, conversion in formatter.parse(template):
        if field_name is None:
            continue
        if not _FIELD_NAME.fullmatch(field_name):
            raise ValueError(f"format_records field {field_name!r} is invalid")
        if field_name not in values:
            raise ValueError(f"format_records field {field_name!r} is absent")
        if format_spec or conversion:
            raise ValueError("format_records conversions and format specs are not supported")
    return template.format_map(values)


def _format_records(records: RecordTable, parameters: dict[str, Any]) -> bytes:
    encoding = parameters.get("encoding", "utf-8")
    if encoding != "utf-8":
        raise ValueError("format_records supports only canonical UTF-8")
    prefix = parameters.get("prefix", "")
    template = parameters.get("record_template")
    separator = parameters.get("separator", "")
    suffix = parameters.get("suffix", "")
    index_start = parameters.get("index_start", 0)
    if not all(isinstance(value, str) for value in (prefix, template, separator, suffix)):
        raise ValueError("format_records text parameters must be strings")
    if isinstance(index_start, bool) or not isinstance(index_start, int):
        raise ValueError("format_records index_start must be an integer")
    rows: list[str] = []
    for index, record in enumerate(records, start=index_start):
        values = dict(record)
        if "index" in values:
            raise ValueError("format_records reserves the index field")
        values["index"] = index
        rows.append(_format_record(template, values))
    return (prefix + separator.join(rows) + suffix).encode("utf-8")


class _Evaluator:
    def __init__(
        self, definitions: Iterable[dict[str, Any]], base_dir: str | Path | None
    ) -> None:
        self.by_id = _definition_map(definitions)
        self.base_dir = Path(base_dir) if base_dir is not None else None
        self.memo: dict[str, GenomeValue] = {}
        self.active: set[str] = set()

    def evaluate(self, ident: str) -> GenomeValue:
        if ident in self.memo:
            return self.memo[ident]
        if ident not in self.by_id:
            raise ValueError(f"entry definition {ident} does not exist")
        if ident in self.active:
            raise ValueError(f"definition dependency cycle at {ident}")
        definition = self.by_id[ident]
        kind = str(definition.get("kind", ""))
        if kind not in GENOME_KINDS:
            raise ValueError(f"definition {ident} has unsupported genome kind {kind!r}")
        parameters = definition.get("parameters")
        if not isinstance(parameters, dict):
            raise ValueError(f"definition {ident} parameters must be an object")
        dependencies = [str(value) for value in definition.get("dependencies", [])]
        for dependency in dependencies:
            if dependency not in self.by_id:
                raise ValueError(f"unknown dependency {dependency} from {ident}")

        self.active.add(ident)
        try:
            if kind == LITERAL_UTF8:
                if dependencies:
                    raise ValueError(f"literal definition {ident} cannot have dependencies")
                text = parameters.get("text")
                if not isinstance(text, str):
                    raise ValueError(f"literal_utf8 definition {ident} requires string text")
                value: GenomeValue = text.encode("utf-8")
            elif kind == LITERAL_HEX:
                if dependencies:
                    raise ValueError(f"literal definition {ident} cannot have dependencies")
                encoded = parameters.get("hex")
                if not isinstance(encoded, str):
                    raise ValueError(f"literal_hex definition {ident} requires string hex")
                if len(encoded) & 1:
                    raise ValueError(f"literal_hex definition {ident} requires even digits")
                if encoded and any(character.isspace() for character in encoded):
                    raise ValueError(f"literal_hex definition {ident} cannot contain whitespace")
                try:
                    value = bytes.fromhex(encoded)
                except ValueError as exc:
                    raise ValueError(f"literal_hex definition {ident} is not hexadecimal") from exc
            elif kind == CONCAT:
                _checked_dependency_hashes(definition, dependencies, self.by_id)
                value = b"".join(
                    _as_bytes(self.evaluate(dependency), ident) for dependency in dependencies
                )
            elif kind == REPEAT:
                if len(dependencies) != 1:
                    raise ValueError(f"repeat definition {ident} requires one dependency")
                _checked_dependency_hashes(definition, dependencies, self.by_id)
                count = parameters.get("count")
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError(f"repeat definition {ident} requires non-negative count")
                value = _as_bytes(self.evaluate(dependencies[0]), ident) * count
            elif kind == AUTHENTICATED_TRACE:
                _checked_dependency_hashes(definition, dependencies, self.by_id)
                if parameters.get("source_definition_hashes") != parameters.get(
                    "dependency_hashes"
                ):
                    raise ValueError(
                        "authenticated_trace source anchors must equal dependency_hashes"
                    )
                for dependency in dependencies:
                    self.evaluate(dependency)  # Explicit content-addressed anchors.
                value = _authenticated_trace(parameters, self.base_dir)
            elif kind == SELECT_RECORDS:
                if len(dependencies) != 1:
                    raise ValueError(f"select_records definition {ident} requires one dependency")
                _checked_dependency_hashes(definition, dependencies, self.by_id)
                value = _select_records(
                    _as_records(self.evaluate(dependencies[0]), ident), parameters
                )
            elif kind == PROJECT_FIELDS:
                if len(dependencies) != 1:
                    raise ValueError(f"project_fields definition {ident} requires one dependency")
                _checked_dependency_hashes(definition, dependencies, self.by_id)
                value = _project_fields(
                    _as_records(self.evaluate(dependencies[0]), ident), parameters
                )
            else:
                if len(dependencies) != 1:
                    raise ValueError(f"format_records definition {ident} requires one dependency")
                _checked_dependency_hashes(definition, dependencies, self.by_id)
                value = _format_records(
                    _as_records(self.evaluate(dependencies[0]), ident), parameters
                )
        finally:
            self.active.remove(ident)
        self.memo[ident] = value
        return value


def evaluate_definition_genome(
    definitions: Iterable[dict[str, Any]], entry: str, *, base_dir: str | Path | None = None
) -> EvaluatedGenome:
    """Evaluate *entry* and require its result to be a literal byte string."""
    definitions = list(definitions)
    evaluator = _Evaluator(definitions, base_dir)
    data = _as_bytes(evaluator.evaluate(entry), entry)
    root = evaluator.by_id[entry]
    return EvaluatedGenome(entry, str(root["content_hash"]), data)


def evaluate_definition_records(
    definitions: Iterable[dict[str, Any]], entry: str, *, base_dir: str | Path | None = None
) -> EvaluatedRecords:
    """Evaluate *entry* and require its result to be an integer record table."""
    definitions = list(definitions)
    evaluator = _Evaluator(definitions, base_dir)
    records = _as_records(evaluator.evaluate(entry), entry)
    root = evaluator.by_id[entry]
    return EvaluatedRecords(entry, str(root["content_hash"]), records)


def lower_definition_genome(
    definitions: Iterable[dict[str, Any]],
    entry: str,
    *,
    base_dir: str | Path | None = None,
) -> Program:
    """Lower an evaluated byte genome into sequential raw EMIT cells."""
    definitions = list(definitions)
    by_id = _definition_map(definitions)
    if entry not in by_id:
        raise ValueError(f"entry definition {entry} does not exist")
    parameters = by_id[entry].get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError(f"entry definition {entry} parameters must be an object")
    if parameters.get("materialization_profile") != MATERIALIZATION_PROFILE:
        raise ValueError(
            f"entry definition {entry} must declare materialization_profile "
            f"{MATERIALIZATION_PROFILE!r}"
        )
    evaluated = evaluate_definition_genome(definitions, entry, base_dir=base_dir)
    digest_text = evaluated.content_hash
    if not digest_text.startswith("sha256:") or len(digest_text) != 71:
        raise ValueError(f"entry definition {entry} has invalid content_hash")
    digest = bytes.fromhex(digest_text[7:])

    chunks = [evaluated.data[offset:offset + 4] for offset in range(0, len(evaluated.data), 4)]
    if not chunks:
        raise ValueError("definition genome must evaluate to at least one artifact byte")
    if len(chunks) > 0xFFFFFFFF:
        raise ValueError("definition genome exceeds the .tmg cell-count limit")

    cells: list[Cell] = []
    for index, chunk in enumerate(chunks):
        final = index + 1 == len(chunks)
        successor = index if final else index + 1
        cells.append(
            Cell(
                index >> 32,
                index & 0xFFFFFFFF,
                int(Opcode.EMIT),
                encode_emit_byte_count(
                    len(chunk), flags=FLAG_EMIT_HALT if final else 0
                ),
                0,
                0,
                0,
                0,
                successor,
                successor,
                int.from_bytes(chunk.ljust(4, b"\0"), "big"),
                index & 0xFFFFFFFF,
            )
        )

    return Program(
        cells=cells,
        entry=0,
        seed=int.from_bytes(digest[:4], "little"),
        default_ticks=len(cells),
        initial_state=State(lineage=int.from_bytes(digest[4:8], "little")),
        flags=GENOME_PROGRAM_FLAG,
    )
