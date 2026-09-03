"""Independent Fraction-based affine trajectory baseline for 0.3 comparison."""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from .canonical import attach_hash


def _f(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, Mapping):
        return Fraction(int(value["num"]), int(value["den"]))
    raise TypeError(value)


def _linear(expr: Mapping[str, Any], fields: Mapping[str, Mapping[str, Any]]) -> tuple[Fraction, Fraction] | None:
    op = expr["op"]
    if op == "const":
        return Fraction(0), _f(expr["value"])
    if op == "time":
        return Fraction(1), Fraction(0)
    if op == "field":
        field = fields[expr["name"]]
        return _f(field.get("rate", 0)), _f(field.get("initial", 0))
    if op == "neg":
        value = _linear(expr["value"], fields)
        return None if value is None else (-value[0], -value[1])
    left = _linear(expr["args"][0], fields)
    right = _linear(expr["args"][1], fields)
    if left is None or right is None:
        return None
    if op == "add":
        return left[0] + right[0], left[1] + right[1]
    if op == "sub":
        return left[0] - right[0], left[1] - right[1]
    if op == "mul":
        if left[0] == 0:
            return right[0] * left[1], right[1] * left[1]
        if right[0] == 0:
            return left[0] * right[1], left[1] * right[1]
        return None
    raise ValueError(op)


def _state(fields: Mapping[str, Mapping[str, Any]], time: Fraction) -> dict[str, Fraction]:
    return {
        name: _f(field.get("initial", 0)) + _f(field.get("rate", 0)) * time
        for name, field in fields.items()
    }


def trusted_affine_baseline(world_record: Mapping[str, Any], start: Any, end: Any) -> dict[str, Any]:
    """Compute roots without importing the 0.3 Q/interval/solver implementation."""
    start_f = _f(start)
    end_f = _f(end)
    trajectory = world_record["trajectory"]
    fields = trajectory["fields"]
    supports = {record["id"]: record for record in world_record["supports"]}
    compatibilities = {record["id"]: record for record in world_record["compatibilities"]}
    events: list[dict[str, Any]] = []
    for relation in world_record["relations"]:
        coeff = _linear(relation["expression"], fields)
        if coeff is None or coeff[0] == 0:
            continue
        root = -coeff[1] / coeff[0]
        active = relation["active_time"]
        if not (start_f <= root <= end_f and _f(active["lower"]) <= root <= _f(active["upper"])):
            continue
        state = _state(fields, root)
        support = supports[relation["support_id"]]
        support_ok = all(
            _f(bound["lower"]) <= state[name] <= _f(bound["upper"])
            for name, bound in support["bounds"].items()
        )
        compatibility = compatibilities[relation["compatibility_id"]]
        compatibility_ok = all(state[name] == _f(value) for name, value in compatibility["equals"].items())
        if not (support_ok and compatibility_ok):
            continue
        events.append({
            "relation_id": relation["id"],
            "event_id": relation["event_id"],
            "priority": int(relation.get("priority", 0)),
            "root": {"num": root.numerator, "den": root.denominator},
        })
    events.sort(key=lambda item: (
        Fraction(item["root"]["num"], item["root"]["den"]),
        item["priority"], item["relation_id"], item["event_id"],
    ))
    return attach_hash({
        "schema": "TOM-TRUSTED-AFFINE-BASELINE-0.3",
        "world_hash": world_record["content_hash"],
        "implementation": "independent fractions.Fraction affine linearizer",
        "start": {"num": start_f.numerator, "den": start_f.denominator},
        "end": {"num": end_f.numerator, "den": end_f.denominator},
        "event_count": len(events),
        "events": events,
    })
