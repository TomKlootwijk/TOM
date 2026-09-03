from __future__ import annotations

import copy
import unittest

from tomagi.formal import (
    OPERATIONS,
    FormalAssertionError,
    FormalBudgetExceeded,
    FormalEvaluationError,
    FormalValidationError,
    Limits,
    attach_program_hash,
    content_address,
    evaluate,
    evaluate_with_steps,
    make_program,
    rational,
    run_program,
    verify_program_hash,
)


def lit(value):
    return {"op": "lit", "value": value}


def ref(name):
    return {"op": "ref", "name": name}


def get(target, key):
    return {"op": "get", "target": target, "key": lit(key)}


def binary(op, left, right):
    return {"op": op, "left": left, "right": right}


def field(name, key):
    return get(ref(name), key)


def affine_candidate_program():
    """A literal generic program which induces exact affine candidates."""

    left_x = get(field("pair", "left"), "x")
    right_x = get(field("pair", "right"), "x")
    left_y = get(field("pair", "left"), "y")
    right_y = get(field("pair", "right"), "y")

    candidate = {
        "op": "let",
        "bindings": [
            {"name": "dx", "value": binary("sub", right_x, left_x)},
            {"name": "dy", "value": binary("sub", right_y, left_y)},
            {"name": "a", "value": binary("div", ref("dy"), ref("dx"))},
            {
                "name": "b",
                "value": binary(
                    "sub", left_y, binary("mul", ref("a"), left_x)
                ),
            },
        ],
        "body": {
            "op": "record",
            "fields": {"a": ref("a"), "b": ref("b")},
        },
    }

    exact_for_observation = binary(
        "eq",
        binary(
            "add",
            binary("mul", field("candidate", "a"), field("observation", "x")),
            field("candidate", "b"),
        ),
        field("observation", "y"),
    )

    expression = {
        "op": "let",
        "bindings": [
            {
                "name": "pairs",
                "value": {"op": "pairs", "source": ref("observations")},
            },
            {
                "name": "distinct_x_pairs",
                "value": {
                    "op": "filter",
                    "source": ref("pairs"),
                    "item": "pair",
                    "predicate": binary("ne", left_x, right_x),
                },
            },
            {
                "name": "raw_candidates",
                "value": {
                    "op": "map",
                    "source": ref("distinct_x_pairs"),
                    "item": "pair",
                    "body": candidate,
                },
            },
            {
                "name": "candidate_groups",
                "value": {
                    "op": "group",
                    "source": ref("raw_candidates"),
                    "item": "candidate",
                    "key": {
                        "op": "list",
                        "items": [field("candidate", "a"), field("candidate", "b")],
                    },
                },
            },
            {
                "name": "unique_candidates",
                "value": {
                    "op": "map",
                    "source": ref("candidate_groups"),
                    "item": "group",
                    "body": {
                        "op": "put",
                        "target": get(field("group", "items"), 0),
                        "key": lit("support"),
                        "value": {"op": "len", "value": field("group", "items")},
                    },
                },
            },
            {
                "name": "exact_candidates",
                "value": {
                    "op": "filter",
                    "source": ref("unique_candidates"),
                    "item": "candidate",
                    "predicate": {
                        "op": "fold",
                        "source": ref("observations"),
                        "item": "observation",
                        "accumulator": "all_exact",
                        "initial": lit(True),
                        "body": {
                            "op": "and",
                            "values": [ref("all_exact"), exact_for_observation],
                        },
                    },
                },
            },
            {
                "name": "ranked",
                "value": {
                    "op": "sort",
                    "source": ref("exact_candidates"),
                    "item": "candidate",
                    "key": {
                        "op": "list",
                        "items": [field("candidate", "a"), field("candidate", "b")],
                    },
                },
            },
        ],
        "body": {
            "op": "assert",
            "condition": binary(
                "gt", {"op": "len", "value": ref("ranked")}, lit(0)
            ),
            "message": "no exact affine candidate",
            "value": get(ref("ranked"), 0),
        },
    }
    return make_program(expression, program_id="generic:finite-affine-induction")


class FormalValueTests(unittest.TestCase):
    def test_is_string_is_type_strict(self):
        self.assertTrue(evaluate({"op": "is_string", "value": lit("dataset:x")}))
        for value in (None, True, 1, ["dataset:x"], {"value": "dataset:x"}):
            with self.subTest(value=value):
                self.assertFalse(evaluate({"op": "is_string", "value": lit(value)}))

    def test_exact_rational_arithmetic_normalizes(self):
        expression = binary(
            "add",
            {"op": "rat", "num": lit(2), "den": lit(4)},
            binary("mul", lit(2), lit({"num": -1, "den": 3})),
        )
        self.assertEqual(evaluate(expression), {"num": -1, "den": 6})
        self.assertEqual(rational(6, -8), {"num": -3, "den": 4})

    def test_noncanonical_rational_and_zero_division_reject(self):
        with self.assertRaisesRegex(FormalValidationError, "reduced"):
            evaluate(lit({"num": 2, "den": 4}))
        with self.assertRaisesRegex(FormalValidationError, "positive"):
            evaluate(lit({"num": 1, "den": -2}))
        with self.assertRaisesRegex(FormalEvaluationError, "division by zero"):
            evaluate(binary("div", lit(1), lit(0)))

    def test_float_nan_and_non_json_values_reject(self):
        for value in (1.5, float("nan"), (1, 2)):
            with self.subTest(value=repr(value)):
                with self.assertRaises(FormalValidationError):
                    evaluate(lit(value))
        with self.assertRaisesRegex(FormalValidationError, "floating-point"):
            evaluate(ref("x"), {"x": 0.25})

    def test_records_lists_conditionals_hash_and_assert(self):
        expression = {
            "op": "if",
            "condition": binary("lt", lit(1), lit(2)),
            "then": {
                "op": "hash",
                "value": {
                    "op": "record",
                    "fields": {
                        "b": lit([2, 3]),
                        "a": binary("add", lit(1), lit(2)),
                    },
                },
            },
            "else": lit("not selected"),
        }
        expected = content_address({"a": rational(3), "b": [2, 3]})
        self.assertEqual(evaluate(expression), expected)
        with self.assertRaisesRegex(FormalAssertionError, "declared failure"):
            evaluate({
                "op": "assert",
                "condition": lit(False),
                "message": "declared failure",
                "value": lit(None),
            })

    def test_floor_and_bit_length_have_exact_integer_contracts(self):
        self.assertEqual(evaluate({"op": "floor", "value": lit(rational(-3, 2))}), -2)
        self.assertEqual(evaluate({"op": "floor", "value": lit(7)}), 7)
        self.assertEqual(evaluate({"op": "bit_length", "value": lit(0)}), 0)
        self.assertEqual(evaluate({"op": "bit_length", "value": lit(8)}), 4)
        self.assertEqual(evaluate({"op": "integer_abs", "value": lit(-9)}), 9)
        with self.assertRaisesRegex(FormalEvaluationError, "requires an integer"):
            evaluate({"op": "integer_abs", "value": lit(rational(-9))})
        for value in (-1, rational(8), True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(FormalEvaluationError, "non-negative integer"):
                    evaluate({"op": "bit_length", "value": lit(value)})


class FormalCollectionTests(unittest.TestCase):
    def test_generic_program_induces_affine_candidate(self):
        observations = [
            {"x": rational(-1), "y": rational(-1)},
            {"x": rational(0), "y": rational(1)},
            {"x": rational(0), "y": rational(1)},
            {"x": rational(1), "y": rational(3)},
            {"x": rational(2), "y": rational(5)},
        ]
        program = affine_candidate_program()
        first = run_program(program, {"observations": observations})
        second = run_program(copy.deepcopy(program), {"observations": copy.deepcopy(observations)})

        self.assertEqual(first, second)
        self.assertEqual(
            first["value"],
            {"a": rational(2), "b": rational(1), "support": 9},
        )
        self.assertEqual(first["program_hash"], program["content_hash"])
        body = {key: value for key, value in first.items() if key != "content_hash"}
        self.assertEqual(first["content_hash"], content_address(body))

    def test_pairs_are_finite_declared_order(self):
        value = evaluate({"op": "pairs", "source": lit(["a", "b", "c"])})
        self.assertEqual(
            [(item["left_index"], item["right_index"]) for item in value],
            [(0, 1), (0, 2), (1, 2)],
        )
        self.assertEqual([(item["left"], item["right"]) for item in value],
                         [("a", "b"), ("a", "c"), ("b", "c")])

    def test_unique_uses_canonical_identity_and_preserves_first_occurrence(self):
        first = {"b": 2, "a": 1}
        same = {"a": 1, "b": 2}
        value = evaluate({
            "op": "unique",
            "source": lit([first, "x", same, "x", rational(1), 1]),
        })
        self.assertEqual(value, [first, "x", rational(1), 1])

    def test_fold_map_filter_sort_and_group_are_deterministic(self):
        grouped = evaluate({
            "op": "group",
            "source": {
                "op": "sort",
                "source": {
                    "op": "filter",
                    "source": {
                        "op": "map",
                        "source": lit([3, 1, 2, 4]),
                        "item": "x",
                        "body": binary("mul", ref("x"), lit(2)),
                    },
                    "item": "x",
                    "predicate": binary("gt", ref("x"), lit(3)),
                },
                "item": "x",
                "key": ref("x"),
                "descending": True,
            },
            "item": "x",
            "key": binary("eq", ref("x"), lit(4)),
        })
        self.assertEqual(
            grouped,
            [
                {"key": False, "items": [rational(8), rational(6)]},
                {"key": True, "items": [rational(4)]},
            ],
        )


class FormalProgramBoundaryTests(unittest.TestCase):
    def test_program_hash_is_canonical_and_tamper_evident(self):
        program = make_program({"op": "record", "fields": {"b": lit(2), "a": lit(1)}})
        reordered = attach_program_hash({
            "expression": {"fields": {"a": lit(1), "b": lit(2)}, "op": "record"},
            "schema": program["schema"],
        })
        self.assertEqual(program["content_hash"], reordered["content_hash"])
        self.assertTrue(verify_program_hash(program))
        program["expression"]["fields"]["a"] = lit(9)
        self.assertFalse(verify_program_hash(program))
        with self.assertRaisesRegex(FormalValidationError, "content hash mismatch"):
            run_program(program)

    def test_unknown_and_unbounded_operations_reject(self):
        self.assertTrue({"floor", "integer_abs", "bit_length", "is_string", "unique"}.issubset(OPERATIONS))
        with self.assertRaisesRegex(FormalValidationError, "unknown formal operation"):
            evaluate({"op": "invented"})
        with self.assertRaisesRegex(FormalValidationError, "unbounded loops"):
            evaluate({"op": "while"})
        with self.assertRaisesRegex(FormalValidationError, "unbounded loops"):
            evaluate({
                "op": "if",
                "condition": lit(True),
                "then": lit("selected"),
                "else": {"op": "while"},
            })

    def test_step_count_is_exposed_and_deterministic(self):
        expression = binary("add", lit(1), lit(2))
        first = evaluate_with_steps(expression)
        second = evaluate_with_steps(copy.deepcopy(expression))
        self.assertEqual(first, second)
        self.assertEqual(first, {"value": rational(3), "steps": 3})
        result = run_program(make_program(expression))
        self.assertEqual(result["steps"], first["steps"])

    def test_step_pair_depth_and_collection_budgets_reject(self):
        mapped = {
            "op": "map",
            "source": lit(list(range(20))),
            "item": "x",
            "body": ref("x"),
        }
        with self.assertRaisesRegex(FormalBudgetExceeded, "max_steps"):
            evaluate(mapped, limits=Limits(max_steps=10))

        with self.assertRaisesRegex(FormalBudgetExceeded, "pairs result"):
            evaluate(
                {"op": "pairs", "source": lit(list(range(6)))},
                limits=Limits(max_collection_items=10),
            )

        deep = lit(0)
        for _ in range(10):
            deep = {"op": "neg", "value": deep}
        with self.assertRaisesRegex(FormalBudgetExceeded, "max_depth"):
            evaluate(deep, limits=Limits(max_depth=5))


if __name__ == "__main__":
    unittest.main()
