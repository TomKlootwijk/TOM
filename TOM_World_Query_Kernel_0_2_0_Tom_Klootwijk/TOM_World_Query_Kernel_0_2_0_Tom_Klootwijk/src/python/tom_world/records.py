"""Typed content-addressed records used by the TOM world kernel."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from heapq import heapify, heappop, heappush
from typing import Any

from .canonical import attach_hash, verify_hash
from .expression import analyze_expression

RECORD_SCHEMA = "TOM-WORLD-RECORD-0.1"
RECORD_TYPES = frozenset({
    "definition",
    "instance",
    "relation",
    "support",
    "compatibility",
    "transition",
    "event_spec",
    "grammar",
    "observation",
    "hypothesis",
    "goal",
    "policy",
    "event",
    "lineage",
    "checkpoint",
})
DEFINITION_PHASES = (
    "parse",
    "normalize",
    "resolve",
    "construct",
    "transform",
    "support",
    "compatibility",
    "guard",
    "transition",
    "lineage",
)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]*$")
_STATE64_FIELDS = frozenset({
    "rho", "theta", "tick", "phi", "vrho", "vtheta", "vtick", "vphi",
    "orientation", "sheet", "branch", "cell", "lineage", "output", "residual", "status",
})


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f"{name} must be an array of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    return value




def _require_sha256(value: Any, name: str) -> str:
    text = _require_string(value, name)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", text):
        raise ValueError(f"{name} must be a lowercase sha256 identifier")
    return text


def _validate_interval(value: Any, name: str) -> None:
    interval = _require_mapping(value, name)
    start = interval.get("start")
    end = interval.get("end")
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise ValueError(f"{name}.start must be a nonnegative integer")
    if isinstance(end, bool) or not isinstance(end, int) or end < start:
        raise ValueError(f"{name}.end must be an integer >= start")


def _validate_topology_sheet(payload: Mapping[str, Any], name: str) -> None:
    if "topology_sheet" in payload:
        sheet = payload["topology_sheet"]
        if isinstance(sheet, bool) or not isinstance(sheet, int) or not 0 <= sheet <= 0xFFFFFFFF:
            raise ValueError(f"{name}.topology_sheet must be a u32 integer")


def make_record(
    record_type: str,
    ident: str,
    payload: Mapping[str, Any],
    *,
    dependencies: Sequence[str] = (),
    version: int = 1,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create and hash one source record."""

    record = {
        "schema": RECORD_SCHEMA,
        "record_type": record_type,
        "id": ident,
        "version": version,
        "dependencies": list(dependencies),
        "payload": dict(payload),
        "provenance": dict(provenance or {}),
    }
    result = attach_hash(record)
    validate_record(result)
    return result


def validate_record(record: Mapping[str, Any], *, require_hash: bool = True) -> None:
    if record.get("schema") != RECORD_SCHEMA:
        raise ValueError(f"record schema must be {RECORD_SCHEMA}")
    record_type = _require_string(record.get("record_type"), "record_type")
    if record_type not in RECORD_TYPES:
        raise ValueError(f"unsupported record_type {record_type}")
    ident = _require_string(record.get("id"), "id")
    if not _ID_RE.fullmatch(ident):
        raise ValueError(f"record id contains unsupported characters: {ident}")
    version = record.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("version must be a positive integer")
    _require_string_list(record.get("dependencies"), "dependencies")
    payload = _require_mapping(record.get("payload"), "payload")
    _require_mapping(record.get("provenance"), "provenance")
    if require_hash and not verify_hash(record):
        raise ValueError(f"record content hash mismatch: {ident}")

    validator = _TYPE_VALIDATORS[record_type]
    validator(ident, payload)


def _validate_definition(ident: str, payload: Mapping[str, Any]) -> None:
    for field in ("kind", "domain", "codomain", "operation", "phase"):
        _require_string(payload.get(field), f"{ident}.payload.{field}")
    if payload["phase"] not in DEFINITION_PHASES:
        raise ValueError(f"{ident}.payload.phase is not a TOM phase")
    order = payload.get("order", 0)
    if isinstance(order, bool) or not isinstance(order, int) or order < 0:
        raise ValueError(f"{ident}.payload.order must be a nonnegative integer")
    if "parameters" in payload:
        _require_mapping(payload["parameters"], f"{ident}.payload.parameters")
    if "capabilities" in payload:
        _require_string_list(payload["capabilities"], f"{ident}.payload.capabilities")
    if "invariants" in payload and not isinstance(payload["invariants"], list):
        raise ValueError(f"{ident}.payload.invariants must be an array")


def _validate_instance(ident: str, payload: Mapping[str, Any]) -> None:
    _require_string(payload.get("program_blob_id"), f"{ident}.payload.program_blob_id")
    if "initial_state" in payload:
        state = _require_mapping(payload["initial_state"], f"{ident}.payload.initial_state")
        unknown = sorted(set(state) - _STATE64_FIELDS)
        if unknown:
            raise ValueError(f"{ident}.payload.initial_state has unknown fields: {', '.join(unknown)}")
        for field, value in state.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{ident}.payload.initial_state.{field} must be an integer")
    if "context" in payload:
        _require_mapping(payload["context"], f"{ident}.payload.context")
    if "time_interval" in payload:
        _validate_interval(payload["time_interval"], f"{ident}.payload.time_interval")
    _validate_topology_sheet(payload, f"{ident}.payload")


def _validate_expression_record(ident: str, payload: Mapping[str, Any]) -> tuple[str, bool, Any]:
    if "expression" not in payload:
        raise ValueError(f"{ident}.payload.expression is required")
    try:
        return analyze_expression(payload["expression"])
    except ValueError as exc:
        raise ValueError(f"{ident}.payload.expression is invalid: {exc}") from exc


def _validate_relation(ident: str, payload: Mapping[str, Any]) -> None:
    result_kind, is_static, static_value = _validate_expression_record(ident, payload)
    _require_string(payload.get("instance_id"), f"{ident}.payload.instance_id")
    zero_test = payload.get("zero_test", "equal_zero")
    if zero_test not in {"equal_zero", "contains_zero", "less_equal_zero"}:
        raise ValueError(f"{ident}.payload.zero_test is unsupported")
    trigger = payload.get("trigger", "enter_zero")
    if trigger not in {"zero", "enter_zero", "crossing", "enter_nonpositive"}:
        raise ValueError(f"{ident}.payload.trigger is unsupported")
    expected_kind = "interval" if zero_test == "contains_zero" else "int"
    if result_kind != "unknown" and result_kind != expected_kind:
        raise ValueError(
            f"{ident}.payload.expression must produce {expected_kind} for {zero_test}"
        )
    if zero_test == "contains_zero" and trigger == "enter_nonpositive":
        raise ValueError(
            f"{ident}.payload.trigger enter_nonpositive requires an integer zero test"
        )
    if is_static and zero_test == "contains_zero":
        lower = static_value.get("lower") if isinstance(static_value, Mapping) else None
        upper = static_value.get("upper") if isinstance(static_value, Mapping) else None
        if (
            isinstance(lower, bool)
            or not isinstance(lower, int)
            or isinstance(upper, bool)
            or not isinstance(upper, int)
            or lower > upper
        ):
            raise ValueError(f"{ident}.payload.expression must produce a valid closed interval")
    for field in ("support_ids", "compatibility_ids"):
        if field in payload:
            _require_string_list(payload[field], f"{ident}.payload.{field}")
    if "event_spec_id" in payload:
        _require_string(payload["event_spec_id"], f"{ident}.payload.event_spec_id")
    priority = payload.get("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValueError(f"{ident}.payload.priority must be an integer")
    if "active_interval" in payload:
        _validate_interval(payload["active_interval"], f"{ident}.payload.active_interval")
    if "time_interval" in payload:
        _validate_interval(payload["time_interval"], f"{ident}.payload.time_interval")
    _validate_topology_sheet(payload, f"{ident}.payload")


def _validate_support(ident: str, payload: Mapping[str, Any]) -> None:
    result_kind, _, _ = _validate_expression_record(ident, payload)
    if result_kind != "unknown" and result_kind != "bool":
        raise ValueError(f"{ident}.payload.expression must produce a boolean")


def _validate_compatibility(ident: str, payload: Mapping[str, Any]) -> None:
    result_kind, _, _ = _validate_expression_record(ident, payload)
    if result_kind != "unknown" and result_kind != "bool":
        raise ValueError(f"{ident}.payload.expression must produce a boolean")


def _validate_transition(ident: str, payload: Mapping[str, Any]) -> None:
    for field in ("set", "add", "xor"):
        if field in payload:
            expressions = _require_mapping(payload[field], f"{ident}.payload.{field}")
            unknown = sorted(
                (repr(name) for name in expressions if not isinstance(name, str) or name not in _STATE64_FIELDS)
            )
            if unknown:
                raise ValueError(
                    f"{ident}.payload.{field} has unknown State64 fields: {', '.join(unknown)}"
                )
            for state_field, expression in expressions.items():
                try:
                    result_kind, _, _ = analyze_expression(expression)
                except ValueError as exc:
                    raise ValueError(
                        f"{ident}.payload.{field}.{state_field} is invalid: {exc}"
                    ) from exc
                if result_kind != "unknown" and result_kind != "int":
                    raise ValueError(
                        f"{ident}.payload.{field}.{state_field} must produce an integer"
                    )
    if not any(field in payload for field in ("set", "add", "xor")):
        raise ValueError(f"{ident}.payload requires set, add, or xor")
    if "normalize_periodic" in payload and not isinstance(payload["normalize_periodic"], bool):
        raise ValueError(f"{ident}.payload.normalize_periodic must be boolean")
    if "lineage_salt" in payload:
        salt = payload["lineage_salt"]
        if isinstance(salt, bool) or not isinstance(salt, int):
            raise ValueError(f"{ident}.payload.lineage_salt must be an integer")


def _validate_event_spec(ident: str, payload: Mapping[str, Any]) -> None:
    _require_string(payload.get("relation_id"), f"{ident}.payload.relation_id")
    if "transition_id" in payload:
        _require_string(payload["transition_id"], f"{ident}.payload.transition_id")
    if "route" in payload:
        _require_string(payload["route"], f"{ident}.payload.route")
    if "confidence" in payload:
        confidence = _require_mapping(payload["confidence"], f"{ident}.payload.confidence")
        if "numerator" in confidence or "denominator" in confidence:
            numerator = confidence.get("numerator")
            denominator = confidence.get("denominator")
            if (
                isinstance(numerator, bool)
                or not isinstance(numerator, int)
                or isinstance(denominator, bool)
                or not isinstance(denominator, int)
                or denominator <= 0
            ):
                raise ValueError(f"{ident}.payload.confidence rational is invalid")


def _validate_grammar(ident: str, payload: Mapping[str, Any]) -> None:
    axiom = payload.get("axiom")
    if not isinstance(axiom, list) or any(not isinstance(x, str) for x in axiom):
        raise ValueError(f"{ident}.payload.axiom must be a string array")
    productions = _require_mapping(payload.get("productions"), f"{ident}.payload.productions")
    for symbol, production in productions.items():
        _require_string(symbol, f"{ident}.payload.productions key")
        if isinstance(production, list):
            if any(not isinstance(x, str) for x in production):
                raise ValueError(f"{ident} production {symbol} must contain strings")
        elif isinstance(production, Mapping):
            for branch in ("zero", "one"):
                value = production.get(branch)
                if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
                    raise ValueError(f"{ident} branched production {symbol}.{branch} must be a string array")
        else:
            raise ValueError(f"{ident} production {symbol} must be an array or zero/one object")
    budgets = _require_mapping(payload.get("budgets"), f"{ident}.payload.budgets")
    for field in ("max_depth", "max_symbols", "max_stack"):
        value = budgets.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{ident}.payload.budgets.{field} must be a nonnegative integer")
    if len(axiom) > budgets["max_symbols"]:
        raise ValueError(f"{ident}.payload.axiom exceeds max_symbols")
    stack_depth = 0
    maximum_stack_depth = 0
    for symbol in axiom:
        if symbol == "[":
            stack_depth += 1
            maximum_stack_depth = max(maximum_stack_depth, stack_depth)
        elif symbol == "]":
            stack_depth -= 1
            if stack_depth < 0:
                raise ValueError(f"{ident}.payload.axiom has an unmatched closing bracket")
    if stack_depth != 0:
        raise ValueError(f"{ident}.payload.axiom has unbalanced brackets")
    if maximum_stack_depth > budgets["max_stack"]:
        raise ValueError(f"{ident}.payload.axiom exceeds max_stack")
    branched = any(isinstance(production, Mapping) for production in productions.values())
    if "branch_bits" not in payload:
        if branched:
            raise ValueError(f"{ident} requires nonempty branch_bits for branched productions")
    else:
        bits = payload["branch_bits"]
        if not isinstance(bits, list) or any(
            isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1)
            for bit in bits
        ):
            raise ValueError(f"{ident}.payload.branch_bits must contain only integer 0/1 values")
        if branched and not bits:
            raise ValueError(f"{ident} requires nonempty branch_bits for branched productions")
    policy = payload.get("branch_policy", "cycle")
    if policy not in {"cycle", "strict"}:
        raise ValueError(f"{ident}.payload.branch_policy is unsupported")


def _validate_checkpoint(ident: str, payload: Mapping[str, Any]) -> None:
    _require_string(payload.get("instance_id"), f"{ident}.payload.instance_id")
    tick = payload.get("tick")
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise ValueError(f"{ident}.payload.tick must be a nonnegative integer")
    executed_steps = payload.get("executed_steps")
    if isinstance(executed_steps, bool) or not isinstance(executed_steps, int) or executed_steps < 0:
        raise ValueError(f"{ident}.payload.executed_steps must be a nonnegative integer")
    state = _require_mapping(payload.get("state"), f"{ident}.payload.state")
    if set(state) != _STATE64_FIELDS:
        missing = sorted(_STATE64_FIELDS - set(state))
        extra = sorted(set(state) - _STATE64_FIELDS)
        raise ValueError(f"{ident}.payload.state field mismatch: missing={missing}, extra={extra}")
    for field, value in state.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{ident}.payload.state.{field} must be an integer")
    _require_sha256(payload.get("instance_hash"), f"{ident}.payload.instance_hash")
    _require_sha256(payload.get("program_blob_hash"), f"{ident}.payload.program_blob_hash")
    _require_sha256(payload.get("source_commit"), f"{ident}.payload.source_commit")
    _require_sha256(payload.get("state_certificate_hash"), f"{ident}.payload.state_certificate_hash")
    if "topology_sheet" not in payload:
        raise ValueError(f"{ident}.payload.topology_sheet is required")
    _validate_topology_sheet(payload, f"{ident}.payload")
    if payload["topology_sheet"] != state["sheet"]:
        raise ValueError(f"{ident}.payload.topology_sheet must equal payload.state.sheet")
    address = _require_mapping(payload.get("generative_address"), f"{ident}.payload.generative_address")
    if address.get("instance_id") != payload["instance_id"] or address.get("tick") != tick:
        raise ValueError(
            f"{ident}.payload.generative_address must identify payload.instance_id and payload.tick"
        )
    interval = payload.get("time_interval")
    _validate_interval(interval, f"{ident}.payload.time_interval")
    if interval["start"] != tick or interval["end"] != tick:
        raise ValueError(f"{ident}.payload.time_interval must be the singleton payload.tick")


def _validate_generic(ident: str, payload: Mapping[str, Any]) -> None:
    del ident, payload


_TYPE_VALIDATORS = {
    "definition": _validate_definition,
    "instance": _validate_instance,
    "relation": _validate_relation,
    "support": _validate_support,
    "compatibility": _validate_compatibility,
    "transition": _validate_transition,
    "event_spec": _validate_event_spec,
    "grammar": _validate_grammar,
    "observation": _validate_generic,
    "hypothesis": _validate_generic,
    "goal": _validate_generic,
    "policy": _validate_generic,
    "event": _validate_generic,
    "lineage": _validate_generic,
    "checkpoint": _validate_checkpoint,
}


def topological_record_order(records: Sequence[Mapping[str, Any]], existing_ids: set[str] | None = None) -> list[str]:
    """Return a deterministic dependency order for staged records."""

    existing = existing_ids or set()
    by_id: dict[str, Mapping[str, Any]] = {}
    input_rank: dict[str, int] = {}
    for rank, record in enumerate(records):
        validate_record(record)
        ident = str(record["id"])
        if ident in by_id:
            raise ValueError(f"duplicate staged record id: {ident}")
        by_id[ident] = record
        input_rank[ident] = rank

    indegree = {ident: 0 for ident in by_id}
    children: dict[str, list[str]] = {ident: [] for ident in by_id}
    for ident, record in by_id.items():
        for dep in record["dependencies"]:
            if dep in existing:
                continue
            if dep not in by_id:
                raise ValueError(f"unresolved dependency {dep} from {ident}")
            indegree[ident] += 1
            children[dep].append(ident)

    ready = [(input_rank[ident], ident) for ident, degree in indegree.items() if degree == 0]
    # A heap preserves input-order tie breaking without repeatedly sorting and
    # shifting a potentially large ready list.
    heapify(ready)
    order: list[str] = []
    while ready:
        _, ident = heappop(ready)
        order.append(ident)
        for child in sorted(children[ident], key=input_rank.__getitem__):
            indegree[child] -= 1
            if indegree[child] == 0:
                heappush(ready, (input_rank[child], child))
    if len(order) != len(by_id):
        cyclic = sorted(ident for ident, degree in indegree.items() if degree > 0)
        raise ValueError("record dependency cycle: " + ", ".join(cyclic))
    return order


def validate_record_dependency_graph(records: Mapping[str, Mapping[str, Any]]) -> None:
    """Validate the complete prospective logical record graph.

    Unlike ``topological_record_order``'s staged-record convenience mode, this
    function treats every supplied ID as its prospective value.  Replacing an
    existing record therefore cannot disguise a self-cycle or a cycle that
    passes through an otherwise unchanged record.
    """

    indegree: dict[str, int] = {ident: 0 for ident in records}
    children: dict[str, list[str]] = {ident: [] for ident in records}
    for ident, record in records.items():
        validate_record(record)
        if record["id"] != ident:
            raise ValueError(f"record graph key/id mismatch: {ident} != {record['id']}")
        for dependency in record["dependencies"]:
            if dependency not in records:
                raise ValueError(f"unresolved dependency {dependency} from {ident}")
            indegree[ident] += 1
            children[str(dependency)].append(ident)

    ready = [ident for ident, degree in indegree.items() if degree == 0]
    heapify(ready)
    visited = 0
    while ready:
        ident = heappop(ready)
        visited += 1
        for child in children[ident]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heappush(ready, child)
    if visited != len(records):
        cyclic = sorted(ident for ident, degree in indegree.items() if degree > 0)
        raise ValueError("record dependency cycle: " + ", ".join(cyclic))
