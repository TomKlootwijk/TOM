"""Bounded, side-effect-free expression evaluator for world queries."""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1

EXPRESSION_SOURCES = frozenset({
    "state",
    "pre_state",
    "left",
    "right",
    "context",
    "event",
})

_BINARY_ARG_OPS = frozenset({
    "add", "sub", "mul", "floor_div", "mod",
    "eq", "ne", "lt", "le", "gt", "ge",
})
_UNARY_ARG_OPS = frozenset({"abs", "neg", "not", "contains_zero"})
_TERNARY_ARG_OPS = frozenset({"cyclic_delta", "in_closed_interval"})
_VARIADIC_ARG_OPS = frozenset({"max", "min", "all", "any"})
_KNOWN_OPS = frozenset({
    "const",
    "field",
    "if",
    "interval",
    "bit",
}).union(_BINARY_ARG_OPS, _UNARY_ARG_OPS, _TERNARY_ARG_OPS, _VARIADIC_ARG_OPS)


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


def _require_expression_keys(
    expression: Mapping[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    path: str,
) -> None:
    non_strings = [key for key in expression if not isinstance(key, str)]
    if non_strings:
        raise ValueError(f"{path} expression keys must be strings")
    missing = sorted(required - set(expression))
    if missing:
        raise ValueError(f"{path} is missing required fields: {', '.join(missing)}")
    unknown = sorted(set(expression) - allowed)
    if unknown:
        raise ValueError(f"{path} has unsupported fields: {', '.join(unknown)}")


def _validate_constant(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} floating literal must be finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_constant(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} object literal keys must be strings")
            _validate_constant(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} has unsupported literal type {type(value).__name__}")


def _validate_static_integer(is_static: bool, value: Any, path: str) -> None:
    if is_static and (isinstance(value, bool) or not isinstance(value, int)):
        raise ValueError(f"{path} must be an integer when statically known")


def _static_result(
    expression: Mapping[str, Any],
    path: str,
    budget: ExpressionBudget,
) -> Any:
    try:
        return evaluate_expression(
            expression,
            {},
            budget=ExpressionBudget(max_nodes=budget.max_nodes, max_depth=budget.max_depth),
        )
    except Exception as exc:
        raise ValueError(f"{path} is statically invalid: {exc}") from exc


def _validate_expression_node(
    expression: Any,
    *,
    budget: ExpressionBudget,
    depth: int,
    path: str,
    check_static: bool,
) -> tuple[bool, Any]:
    budget.visit(depth)
    if expression is None or isinstance(expression, (str, bool)):
        return (True, expression) if check_static else (False, None)
    if isinstance(expression, int):
        _validate_constant(expression, path)
        return (True, expression) if check_static else (False, None)
    if isinstance(expression, list):
        values: list[Any] = []
        all_static = True
        for index, item in enumerate(expression):
            is_static, value = _validate_expression_node(
                item,
                budget=budget,
                depth=depth + 1,
                path=f"{path}[{index}]",
                check_static=check_static,
            )
            all_static = all_static and is_static
            values.append(value)
        return all_static, values if all_static else None
    if not isinstance(expression, Mapping):
        raise ValueError(f"{path} has unsupported expression type {type(expression).__name__}")

    if "op" not in expression:
        values: dict[str, Any] = {}
        all_static = True
        for key, item in expression.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} expression object keys must be strings")
            is_static, value = _validate_expression_node(
                item,
                budget=budget,
                depth=depth + 1,
                path=f"{path}.{key}",
                check_static=check_static,
            )
            all_static = all_static and is_static
            values[key] = value
        return all_static, values if all_static else None

    op = expression["op"]
    if not isinstance(op, str) or not op:
        raise ValueError(f"{path}.op must be a nonempty string")
    if op not in _KNOWN_OPS:
        raise ValueError(f"{path} has unknown query expression operation: {op}")

    if op == "const":
        _require_expression_keys(
            expression,
            allowed={"op", "value"},
            required={"op", "value"},
            path=path,
        )
        _validate_constant(expression["value"], f"{path}.value")
        return (True, expression["value"]) if check_static else (False, None)

    if op == "field":
        _require_expression_keys(
            expression,
            allowed={"op", "source", "name", "path"},
            required={"op"},
            path=path,
        )
        source = expression.get("source", "state")
        if not isinstance(source, str) or source not in EXPRESSION_SOURCES:
            raise ValueError(f"{path}.source is unsupported: {source!r}")
        has_name = "name" in expression
        has_path = "path" in expression
        if has_name == has_path:
            raise ValueError(f"{path} field requires exactly one of name or path")
        if has_name:
            name = expression["name"]
            if not isinstance(name, str) or not name:
                raise ValueError(f"{path}.name must be a nonempty string")
        else:
            field_path = expression["path"]
            if not isinstance(field_path, list):
                raise ValueError(f"{path}.path must be an array")
            for index, component in enumerate(field_path):
                valid_string = isinstance(component, str)
                valid_index = (
                    isinstance(component, int)
                    and not isinstance(component, bool)
                )
                if not valid_string and not valid_index:
                    raise ValueError(
                        f"{path}.path[{index}] must be a string or integer"
        )
        return False, None

    if op == "if":
        _require_expression_keys(
            expression,
            allowed={"op", "condition", "then", "else"},
            required={"op", "condition", "then", "else"},
            path=path,
        )
        condition = _validate_expression_node(
            expression["condition"],
            budget=budget,
            depth=depth + 1,
            path=f"{path}.condition",
            check_static=check_static,
        )
        if check_static and condition[0] and isinstance(condition[1], bool):
            check_then = condition[1]
            check_else = not condition[1]
        elif check_static and not condition[0]:
            check_then = True
            check_else = True
        else:
            # An unreachable outer branch, or an invalid statically known
            # condition, still requires valid structure in both branches but
            # must not eagerly enforce their value/type constraints.
            check_then = False
            check_else = False
        then_value = _validate_expression_node(
            expression["then"],
            budget=budget,
            depth=depth + 1,
            path=f"{path}.then",
            check_static=check_then,
        )
        else_value = _validate_expression_node(
            expression["else"],
            budget=budget,
            depth=depth + 1,
            path=f"{path}.else",
            check_static=check_else,
        )
        if check_static and condition[0] and not isinstance(condition[1], bool):
            raise ValueError(f"{path}.condition must be boolean when statically known")
        if not check_static or not condition[0]:
            return False, None
        selected = then_value if condition[1] else else_value
        return (True, _static_result(expression, path, budget)) if selected[0] else (False, None)

    _require_expression_keys(
        expression,
        allowed={"op", "args"},
        required={"op", "args"},
        path=path,
    )
    args = expression["args"]
    if not isinstance(args, list):
        raise ValueError(f"{path}.args must be an array")
    if op in _BINARY_ARG_OPS or op in {"interval", "bit"}:
        expected_count = 2
    elif op in _UNARY_ARG_OPS:
        expected_count = 1
    elif op in _TERNARY_ARG_OPS:
        expected_count = 3
    else:
        expected_count = None
    if expected_count is not None and len(args) != expected_count:
        raise ValueError(f"{path} expression {op} requires {expected_count} args")
    if op in {"max", "min"} and not args:
        raise ValueError(f"{path} expression {op} requires at least one arg")

    validated_args = [
        _validate_expression_node(
            arg,
            budget=budget,
            depth=depth + 1,
            path=f"{path}.args[{index}]",
            check_static=check_static,
        )
        for index, arg in enumerate(args)
    ]

    if check_static:
        integer_positions: range | tuple[int, ...] = ()
        if op in {"add", "sub", "mul", "floor_div", "mod", "interval", "bit"}:
            integer_positions = range(2)
        elif op in {"abs", "neg"}:
            integer_positions = (0,)
        elif op in {"max", "min"}:
            integer_positions = range(len(args))
        elif op in {"cyclic_delta", "in_closed_interval"}:
            integer_positions = range(3)
        for index in integer_positions:
            _validate_static_integer(
                validated_args[index][0],
                validated_args[index][1],
                f"{path}.args[{index}]",
            )

        if op in {"all", "any"}:
            for index, (is_static, value) in enumerate(validated_args):
                if is_static and not isinstance(value, bool):
                    raise ValueError(f"{path}.args[{index}] must be boolean when statically known")
        elif op == "not" and validated_args[0][0] and not isinstance(validated_args[0][1], bool):
            raise ValueError(f"{path}.args[0] must be boolean when statically known")

        if op in {"floor_div", "mod"} and validated_args[1] == (True, 0):
            raise ValueError(f"{path}.args[1] must not be statically zero")
        if op == "cyclic_delta" and validated_args[2][0]:
            period = validated_args[2][1]
            if isinstance(period, int) and not isinstance(period, bool) and period <= 0:
                raise ValueError(f"{path}.args[2] period must be positive")
        if op == "bit" and validated_args[1][0]:
            index = validated_args[1][1]
            if isinstance(index, int) and not isinstance(index, bool) and not 0 <= index < 64:
                raise ValueError(f"{path}.args[1] bit index must be in 0..63")
        if op == "interval" and validated_args[0][0] and validated_args[1][0]:
            lower, upper = validated_args[0][1], validated_args[1][1]
            if isinstance(lower, int) and isinstance(upper, int) and lower > upper:
                raise ValueError(f"{path} interval lower bound exceeds upper bound")
        if op == "in_closed_interval" and validated_args[1][0] and validated_args[2][0]:
            lower, upper = validated_args[1][1], validated_args[2][1]
            if isinstance(lower, int) and isinstance(upper, int) and lower > upper:
                raise ValueError(f"{path} interval lower bound exceeds upper bound")

    all_static = all(is_static for is_static, _ in validated_args)
    return (True, _static_result(expression, path, budget)) if all_static else (False, None)


def _literal_result_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, Mapping):
        lower = value.get("lower")
        upper = value.get("upper")
        if (
            isinstance(lower, int)
            and not isinstance(lower, bool)
            and isinstance(upper, int)
            and not isinstance(upper, bool)
        ):
            return "interval"
        return "object"
    if isinstance(value, list):
        return "list"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "unknown"


def _expression_result_kind(expression: Any) -> str:
    if isinstance(expression, Mapping) and "op" not in expression:
        if "lower" in expression and "upper" in expression:
            lower_kind = _expression_result_kind(expression["lower"])
            upper_kind = _expression_result_kind(expression["upper"])
            if lower_kind in {"int", "unknown"} and upper_kind in {"int", "unknown"}:
                return "interval"
        return "object"
    if not isinstance(expression, Mapping):
        return _literal_result_kind(expression)
    op = expression["op"]
    if op == "const":
        return _literal_result_kind(expression["value"])
    if op == "field":
        return "unknown"
    if op in {
        "add", "sub", "mul", "floor_div", "mod", "abs", "neg",
        "max", "min", "cyclic_delta", "bit",
    }:
        return "int"
    if op in {
        "eq", "ne", "lt", "le", "gt", "ge", "all", "any", "not",
        "contains_zero", "in_closed_interval",
    }:
        return "bool"
    if op == "interval":
        return "interval"
    if op == "if":
        try:
            condition = evaluate_expression(expression["condition"], {})
        except Exception:
            condition = None
        if isinstance(condition, bool):
            return _expression_result_kind(expression["then"] if condition else expression["else"])
        then_kind = _expression_result_kind(expression["then"])
        else_kind = _expression_result_kind(expression["else"])
        if then_kind == else_kind:
            return then_kind
        # A field contributes no statically known type. Preserve any type that
        # is known from the other reachable branch, and distinguish genuinely
        # incompatible known branches from field-dependent uncertainty.
        if then_kind == "unknown":
            return else_kind
        if else_kind == "unknown":
            return then_kind
        return "mixed"
    return "unknown"


def analyze_expression(
    expression: Any,
    *,
    max_nodes: int = 10_000,
    max_depth: int = 64,
) -> tuple[str, bool, Any]:
    """Validate an expression and return its known result kind/static value.

    Field-dependent result types and values remain runtime concerns.  Invalid
    literal-only operations are rejected because their failure is knowable when
    the expression is accepted.
    """

    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes < 1:
        raise ValueError("max_nodes must be a positive integer")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be a nonnegative integer")
    is_static, value = _validate_expression_node(
        expression,
        budget=ExpressionBudget(max_nodes=max_nodes, max_depth=max_depth),
        depth=0,
        path="$",
        check_static=True,
    )
    return _expression_result_kind(expression), is_static, value


def validate_expression(
    expression: Any,
    *,
    max_nodes: int = 10_000,
    max_depth: int = 64,
) -> None:
    """Validate the accepted structural form of one bounded expression."""

    analyze_expression(expression, max_nodes=max_nodes, max_depth=max_depth)


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
        return _i64(max(values) if op == "max" else min(values))

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
        if lower > upper:
            raise ValueError("interval lower bound exceeds upper bound")
        return lower <= 0 <= upper

    if op == "in_closed_interval":
        value_expr, lower_expr, upper_expr = _args(expression, 3)
        value = _int(evaluate_expression(value_expr, sources, budget=tracker, depth=depth + 1))
        lower = _int(evaluate_expression(lower_expr, sources, budget=tracker, depth=depth + 1))
        upper = _int(evaluate_expression(upper_expr, sources, budget=tracker, depth=depth + 1))
        if lower > upper:
            raise ValueError("interval lower bound exceeds upper bound")
        return lower <= value <= upper

    if op == "bit":
        value_expr, index_expr = _args(expression, 2)
        value = _int(evaluate_expression(value_expr, sources, budget=tracker, depth=depth + 1))
        index = _int(evaluate_expression(index_expr, sources, budget=tracker, depth=depth + 1))
        if not 0 <= index < 64:
            raise ValueError("bit index must be in 0..63")
        return (value >> index) & 1

    raise ValueError(f"unknown query expression operation: {op}")
