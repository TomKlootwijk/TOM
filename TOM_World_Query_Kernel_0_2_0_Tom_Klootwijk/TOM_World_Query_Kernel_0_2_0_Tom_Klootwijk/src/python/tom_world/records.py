"""Typed content-addressed records used by the TOM world kernel."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .canonical import attach_hash, verify_hash

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
        valid = {
            "rho", "theta", "tick", "phi", "vrho", "vtheta", "vtick", "vphi",
            "orientation", "sheet", "branch", "cell", "lineage", "output", "residual", "status",
        }
        unknown = sorted(set(state) - valid)
        if unknown:
            raise ValueError(f"{ident}.payload.initial_state has unknown fields: {', '.join(unknown)}")
    if "context" in payload:
        _require_mapping(payload["context"], f"{ident}.payload.context")
    if "time_interval" in payload:
        _validate_interval(payload["time_interval"], f"{ident}.payload.time_interval")
    _validate_topology_sheet(payload, f"{ident}.payload")


def _validate_expression_record(ident: str, payload: Mapping[str, Any]) -> None:
    if "expression" not in payload:
        raise ValueError(f"{ident}.payload.expression is required")


def _validate_relation(ident: str, payload: Mapping[str, Any]) -> None:
    _validate_expression_record(ident, payload)
    _require_string(payload.get("instance_id"), f"{ident}.payload.instance_id")
    zero_test = payload.get("zero_test", "equal_zero")
    if zero_test not in {"equal_zero", "contains_zero", "less_equal_zero"}:
        raise ValueError(f"{ident}.payload.zero_test is unsupported")
    trigger = payload.get("trigger", "enter_zero")
    if trigger not in {"zero", "enter_zero", "crossing", "enter_nonpositive"}:
        raise ValueError(f"{ident}.payload.trigger is unsupported")
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
    _validate_expression_record(ident, payload)


def _validate_compatibility(ident: str, payload: Mapping[str, Any]) -> None:
    _validate_expression_record(ident, payload)


def _validate_transition(ident: str, payload: Mapping[str, Any]) -> None:
    for field in ("set", "add", "xor"):
        if field in payload:
            _require_mapping(payload[field], f"{ident}.payload.{field}")
    if not any(field in payload for field in ("set", "add", "xor")):
        raise ValueError(f"{ident}.payload requires set, add, or xor")
    if "normalize_periodic" in payload and not isinstance(payload["normalize_periodic"], bool):
        raise ValueError(f"{ident}.payload.normalize_periodic must be boolean")


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
            if not isinstance(numerator, int) or not isinstance(denominator, int) or denominator <= 0:
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
    if "branch_bits" in payload:
        bits = payload["branch_bits"]
        if not isinstance(bits, list) or any(bit not in (0, 1) for bit in bits):
            raise ValueError(f"{ident}.payload.branch_bits must contain only 0/1")
        if not bits and any(isinstance(p, Mapping) for p in productions.values()):
            raise ValueError(f"{ident} requires branch_bits for branched productions")
    policy = payload.get("branch_policy", "cycle")
    if policy not in {"cycle", "strict"}:
        raise ValueError(f"{ident}.payload.branch_policy is unsupported")


def _validate_checkpoint(ident: str, payload: Mapping[str, Any]) -> None:
    _require_string(payload.get("instance_id"), f"{ident}.payload.instance_id")
    tick = payload.get("tick")
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise ValueError(f"{ident}.payload.tick must be a nonnegative integer")
    state = _require_mapping(payload.get("state"), f"{ident}.payload.state")
    valid = {
        "rho", "theta", "tick", "phi", "vrho", "vtheta", "vtick", "vphi",
        "orientation", "sheet", "branch", "cell", "lineage", "output", "residual", "status",
    }
    if set(state) != valid:
        missing = sorted(valid - set(state))
        extra = sorted(set(state) - valid)
        raise ValueError(f"{ident}.payload.state field mismatch: missing={missing}, extra={extra}")
    for field, value in state.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{ident}.payload.state.{field} must be an integer")
    _require_sha256(payload.get("instance_hash"), f"{ident}.payload.instance_hash")
    _require_sha256(payload.get("program_blob_hash"), f"{ident}.payload.program_blob_hash")
    _require_sha256(payload.get("source_commit"), f"{ident}.payload.source_commit")
    _require_sha256(payload.get("state_certificate_hash"), f"{ident}.payload.state_certificate_hash")
    _validate_topology_sheet(payload, f"{ident}.payload")


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

    ready = sorted((input_rank[ident], ident) for ident, degree in indegree.items() if degree == 0)
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
        raise ValueError("record dependency cycle: " + ", ".join(cyclic))
    return order
