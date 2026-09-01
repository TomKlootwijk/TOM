"""Bounded, side-effect-free expression evaluator for world queries."""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping, Sequence

I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1


@dataclass(slots=True)
class ExpressionBudget:
    max_nodes: int = 10_000
    max_depth: int = 64
    nodes: int = 0

    def visit(self, depth: int) -> None:
        self.nodes += 1
        if self.nodes > self.max_nodes:
            raise ValueError(f"expression node budget exceeded: {self.nodes} > {self.max_nodes}")
        if depth > self.max_depth:
            raise ValueError(f"expression depth budget exceeded: {depth} > {self.max_depth}")


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return vars(value)
    raise TypeError(f"value is not field-addressable: {type(value).__name__}")


def _get_path(value: Any, path: Sequence[Any]) -> Any:
    current = value
    for key in path:
        if isinstance(current, Mapping):
            current = current[key]
        elif is_dataclass(current):
            current = getattr(current, str(key))
        elif isinstance(current, (list, tuple)) and isinstance(key, int):
            current = current[key]
        else:
            current = getattr(current, str(key))
    return current


def _int(value: Any, name: str = "value") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _i64(value: int) -> int:
    if not I64_MIN <= value <= I64_MAX:
        raise OverflowError(f"query integer exceeds signed 64-bit range: {value}")
    return value


def _args(expression: Mapping[str, Any], count: int | None = None) -> list[Any]:
    args = expression.get("args")
    if not isinstance(args, list):
        raise ValueError(f"expression {expression.get('op')} requires an args array")
    if count is not None and len(args) != count:
        raise ValueError(f"expression {expression.get('op')} requires {count} args")
    return args


def evaluate_expression(
    expression: Any,
    sources: Mapping[str, Any],
    *,
    budget: ExpressionBudget | None = None,
    depth: int = 0,
) -> Any:
    """Evaluate one deterministic expression.

    The evaluator has no I/O, clock, random source, dynamic import, or arbitrary
    code path.  Numeric arithmetic is checked signed 64-bit integer arithmetic.
    """

    tracker = budget or ExpressionBudget()
    tracker.visit(depth)

    if expression is None or isinstance(expression, (str, int, bool)):
        return expression
    if isinstance(expression, list):
        return [evaluate_expression(item, sources, budget=tracker, depth=depth + 1) for item in expression]
    if not isinstance(expression, Mapping):
        raise TypeError(f"unsupported expression value: {type(expression).__name__}")

    op = expression.get("op")
    if not isinstance(op, str) or not op:
        return {
            str(key): evaluate_expression(value, sources, budget=tracker, depth=depth + 1)
            for key, value in expression.items()
        }

    if op == "const":
        return expression.get("value")
    if op == "field":
        source_name = expression.get("source", "state")
        if not isinstance(source_name, str) or source_name not in sources:
            raise ValueError(f"unknown expression source: {source_name!r}")
        if "path" in expression:
            path = expression["path"]
            if not isinstance(path, list):
                raise ValueError("field.path must be an array")
        else:
            name = expression.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("field requires name or path")
            path = [name]
        return _get_path(sources[source_name], path)

    if op in {"add", "sub", "mul", "floor_div", "mod"}:
        left_expr, right_expr = _args(expression, 2)
        left = _int(evaluate_expression(left_expr, sources, budget=tracker, depth=depth + 1), "left")
        right = _int(evaluate_expression(right_expr, sources, budget=tracker, depth=depth + 1), "right")
        if op == "add":
            return _i64(left + right)
        if op == "sub":
            return _i64(left - right)
        if op == "mul":
            return _i64(left * right)
        if right == 0:
            raise ZeroDivisionError(f"{op} by zero")
        if op == "floor_div":
            return _i64(left // right)
        return _i64(left % right)

    if op in {"abs", "neg"}:
        (arg_expr,) = _args(expression, 1)
        value = _int(evaluate_expression(arg_expr, sources, budget=tracker, depth=depth + 1))
        return _i64(abs(value) if op == "abs" else -value)

    if op in {"max", "min"}:
        values = [
            _int(evaluate_expression(arg, sources, budget=tracker, depth=depth + 1))
            for arg in _args(expression)
        ]
        if not values:
            raise ValueError(f"{op} requires at least one arg")
        return max(values) if op == "max" else min(values)

    if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
        left_expr, right_expr = _args(expression, 2)
        left = evaluate_expression(left_expr, sources, budget=tracker, depth=depth + 1)
        right = evaluate_expression(right_expr, sources, budget=tracker, depth=depth + 1)
        if op == "eq":
            return left == right
        if op == "ne":
            return left != right
        if op == "lt":
            return left < right
        if op == "le":
            return left <= right
        if op == "gt":
            return left > right
        return left >= right

    if op in {"all", "any"}:
        values = [
            evaluate_expression(arg, sources, budget=tracker, depth=depth + 1)
            for arg in _args(expression)
        ]
        if any(not isinstance(value, bool) for value in values):
            raise TypeError(f"{op} arguments must be booleans")
        return all(values) if op == "all" else any(values)

    if op == "not":
        (arg_expr,) = _args(expression, 1)
        value = evaluate_expression(arg_expr, sources, budget=tracker, depth=depth + 1)
        if not isinstance(value, bool):
            raise TypeError("not argument must be boolean")
        return not value

    if op == "if":
        condition = evaluate_expression(expression.get("condition"), sources, budget=tracker, depth=depth + 1)
        if not isinstance(condition, bool):
            raise TypeError("if condition must be boolean")
        selected = expression.get("then") if condition else expression.get("else")
        return evaluate_expression(selected, sources, budget=tracker, depth=depth + 1)

    if op == "cyclic_delta":
        value_expr, center_expr, period_expr = _args(expression, 3)
        value = _int(evaluate_expression(value_expr, sources, budget=tracker, depth=depth + 1))
        center = _int(evaluate_expression(center_expr, sources, budget=tracker, depth=depth + 1))
        period = _int(evaluate_expression(period_expr, sources, budget=tracker, depth=depth + 1))
        if period <= 0:
            raise ValueError("cyclic_delta period must be positive")
        delta = (value - center) % period
        if delta >= (period + 1) // 2:
            delta -= period
        return _i64(delta)

    if op == "interval":
        lower_expr, upper_expr = _args(expression, 2)
        lower = _int(evaluate_expression(lower_expr, sources, budget=tracker, depth=depth + 1))
        upper = _int(evaluate_expression(upper_expr, sources, budget=tracker, depth=depth + 1))
        if lower > upper:
            raise ValueError("interval lower bound exceeds upper bound")
        return {"lower": lower, "upper": upper}

    if op == "contains_zero":
        (arg_expr,) = _args(expression, 1)
        interval = evaluate_expression(arg_expr, sources, budget=tracker, depth=depth + 1)
        if not isinstance(interval, Mapping):
            raise TypeError("contains_zero requires an interval object")
        lower = _int(interval.get("lower"), "interval.lower")
        upper = _int(interval.get("upper"), "interval.upper")
        return lower <= 0 <= upper

    if op == "in_closed_interval":
        value_expr, lower_expr, upper_expr = _args(expression, 3)
        value = _int(evaluate_expression(value_expr, sources, budget=tracker, depth=depth + 1))
        lower = _int(evaluate_expression(lower_expr, sources, budget=tracker, depth=depth + 1))
        upper = _int(evaluate_expression(upper_expr, sources, budget=tracker, depth=depth + 1))
        return lower <= value <= upper

    if op == "bit":
        value_expr, index_expr = _args(expression, 2)
        value = _int(evaluate_expression(value_expr, sources, budget=tracker, depth=depth + 1))
        index = _int(evaluate_expression(index_expr, sources, budget=tracker, depth=depth + 1))
        if not 0 <= index < 64:
            raise ValueError("bit index must be in 0..63")
        return (value >> index) & 1

    raise ValueError(f"unknown query expression operation: {op}")
