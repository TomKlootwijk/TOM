"""Typed continuous expression evaluation over affine TOM trajectories."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .interval import ClosedInterval
from .rational import Q


class TrajectoryLike(Protocol):
    def state_at(self, time: Q) -> Mapping[str, Q]: ...
    def field_interval(self, name: str, time: ClosedInterval) -> ClosedInterval: ...
    def field_rate(self, name: str) -> Q: ...
    def field_affine(self, name: str) -> tuple[Q, Q]: ...


@dataclass(frozen=True, slots=True)
class DualInterval:
    value: ClosedInterval
    derivative: ClosedInterval


def _op(expr: Mapping[str, Any]) -> str:
    value = expr.get("op")
    if not isinstance(value, str):
        raise ValueError("expression requires string op")
    return value


def validate_expression(expr: Any, *, depth: int = 0, max_depth: int = 64) -> None:
    if depth > max_depth:
        raise ValueError("expression depth exceeds profile limit")
    if not isinstance(expr, Mapping):
        raise TypeError("relation expression nodes must be objects")
    op = _op(expr)
    if op == "const":
        Q.from_value(expr.get("value"))
        return
    if op == "field":
        if not isinstance(expr.get("name"), str) or not expr["name"]:
            raise ValueError("field expression requires nonempty name")
        return
    if op == "time":
        return
    if op == "neg":
        validate_expression(expr.get("value"), depth=depth + 1, max_depth=max_depth)
        return
    if op in {"add", "sub", "mul"}:
        args = expr.get("args")
        if not isinstance(args, list) or len(args) != 2:
            raise ValueError(f"{op} expression requires exactly two args")
        validate_expression(args[0], depth=depth + 1, max_depth=max_depth)
        validate_expression(args[1], depth=depth + 1, max_depth=max_depth)
        return
    raise ValueError(f"unsupported continuous expression op {op}")


def evaluate_point(expr: Mapping[str, Any], trajectory: TrajectoryLike, time: Q) -> Q:
    op = _op(expr)
    if op == "const":
        return Q.from_value(expr["value"])
    if op == "time":
        return time
    if op == "field":
        state = trajectory.state_at(time)
        name = str(expr["name"])
        if name not in state:
            raise ValueError(f"trajectory has no field {name}")
        return Q.from_value(state[name])
    if op == "neg":
        return -evaluate_point(expr["value"], trajectory, time)
    a = evaluate_point(expr["args"][0], trajectory, time)
    b = evaluate_point(expr["args"][1], trajectory, time)
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    raise ValueError(f"unsupported op {op}")


def evaluate_dual_interval(
    expr: Mapping[str, Any],
    trajectory: TrajectoryLike,
    time: ClosedInterval,
) -> DualInterval:
    op = _op(expr)
    if op == "const":
        return DualInterval(ClosedInterval.point(expr["value"]), ClosedInterval.point(0))
    if op == "time":
        return DualInterval(time, ClosedInterval.point(1))
    if op == "field":
        name = str(expr["name"])
        return DualInterval(
            trajectory.field_interval(name, time),
            ClosedInterval.point(trajectory.field_rate(name)),
        )
    if op == "neg":
        a = evaluate_dual_interval(expr["value"], trajectory, time)
        return DualInterval(-a.value, -a.derivative)
    a = evaluate_dual_interval(expr["args"][0], trajectory, time)
    b = evaluate_dual_interval(expr["args"][1], trajectory, time)
    if op == "add":
        return DualInterval(a.value + b.value, a.derivative + b.derivative)
    if op == "sub":
        return DualInterval(a.value - b.value, a.derivative - b.derivative)
    if op == "mul":
        return DualInterval(
            a.value * b.value,
            a.derivative * b.value + a.value * b.derivative,
        )
    raise ValueError(f"unsupported op {op}")


def affine_coefficients(
    expr: Mapping[str, Any], trajectory: TrajectoryLike
) -> tuple[Q, Q] | None:
    """Return (slope, intercept) when expr is affine in global time."""
    op = _op(expr)
    if op == "const":
        return Q(0), Q.from_value(expr["value"])
    if op == "time":
        return Q(1), Q(0)
    if op == "field":
        return trajectory.field_affine(str(expr["name"]))
    if op == "neg":
        inner = affine_coefficients(expr["value"], trajectory)
        return None if inner is None else (-inner[0], -inner[1])
    left = affine_coefficients(expr["args"][0], trajectory)
    right = affine_coefficients(expr["args"][1], trajectory)
    if left is None or right is None:
        return None
    if op == "add":
        return left[0] + right[0], left[1] + right[1]
    if op == "sub":
        return left[0] - right[0], left[1] - right[1]
    if op == "mul":
        if left[0] == Q(0):
            return right[0] * left[1], right[1] * left[1]
        if right[0] == Q(0):
            return left[0] * right[1], left[1] * right[1]
        return None
    raise ValueError(f"unsupported op {op}")
