from __future__ import annotations

import unittest

from tom_world.expression import I64_MAX, evaluate_expression, validate_expression
from tom_world.records import make_record


class StructuralExpressionValidationTests(unittest.TestCase):
    def test_every_implemented_operation_has_an_accepted_structural_form(self):
        expressions = {
            "const": {"op": "const", "value": {"answer": 42}},
            "field-name": {"op": "field", "source": "state", "name": "rho"},
            "field-path": {"op": "field", "source": "event", "path": ["items", 0]},
            "add": {"op": "add", "args": [1, 2]},
            "sub": {"op": "sub", "args": [1, 2]},
            "mul": {"op": "mul", "args": [1, 2]},
            "floor_div": {"op": "floor_div", "args": [4, 2]},
            "mod": {"op": "mod", "args": [5, 2]},
            "abs": {"op": "abs", "args": [-1]},
            "neg": {"op": "neg", "args": [1]},
            "max": {"op": "max", "args": [1, 2, 3]},
            "min": {"op": "min", "args": [1]},
            "eq": {"op": "eq", "args": [1, 1]},
            "ne": {"op": "ne", "args": [1, 2]},
            "lt": {"op": "lt", "args": [1, 2]},
            "le": {"op": "le", "args": [1, 1]},
            "gt": {"op": "gt", "args": [2, 1]},
            "ge": {"op": "ge", "args": [1, 1]},
            "all": {"op": "all", "args": [True, True]},
            "any": {"op": "any", "args": [False, True]},
            "not": {"op": "not", "args": [False]},
            "if": {"op": "if", "condition": True, "then": 1, "else": 2},
            "cyclic_delta": {"op": "cyclic_delta", "args": [15, 1, 16]},
            "interval": {"op": "interval", "args": [-1, 2]},
            "contains_zero": {
                "op": "contains_zero",
                "args": [{"op": "interval", "args": [-1, 2]}],
            },
            "in_closed_interval": {"op": "in_closed_interval", "args": [2, 1, 3]},
            "bit": {"op": "bit", "args": [4, 2]},
        }
        for name, expression in expressions.items():
            with self.subTest(name=name):
                self.assertIsNone(validate_expression(expression))

    def test_unknown_operations_fields_and_argument_shapes_are_rejected(self):
        invalid = {
            "unknown-op": {"op": "sqrt", "args": [4]},
            "non-string-op": {"op": 3, "args": []},
            "missing-const-value": {"op": "const"},
            "extra-field": {"op": "const", "value": 1, "args": []},
            "missing-args": {"op": "add"},
            "args-not-array": {"op": "add", "args": (1, 2)},
            "wrong-binary-arity": {"op": "add", "args": [1]},
            "wrong-unary-arity": {"op": "not", "args": [True, False]},
            "empty-max": {"op": "max", "args": []},
            "missing-if-else": {"op": "if", "condition": True, "then": 1},
        }
        for name, expression in invalid.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_expression(expression)

    def test_field_sources_and_paths_are_validated_without_resolving_fields(self):
        invalid = {
            "unknown-source": {"op": "field", "source": "clock", "name": "now"},
            "missing-selector": {"op": "field", "source": "state"},
            "two-selectors": {"op": "field", "name": "rho", "path": ["rho"]},
            "empty-name": {"op": "field", "name": ""},
            "path-not-array": {"op": "field", "path": "rho"},
            "boolean-index": {"op": "field", "path": [True]},
        }
        for name, expression in invalid.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_expression(expression)

        # Whether a declared field exists and what value it yields depends on
        # the query source and therefore remains a runtime check.
        validate_expression({"op": "field", "source": "context", "path": ["unknown", 0]})
        validate_expression({"op": "field", "source": "context", "path": []})
        validate_expression({"op": "field", "source": "context", "path": ["items", -1]})

    def test_statically_invalid_literal_parameters_are_rejected(self):
        invalid = {
            "non-integer-arithmetic": {"op": "add", "args": [1, "two"]},
            "zero-divisor": {
                "op": "floor_div",
                "args": [{"op": "field", "name": "rho"}, {"op": "const", "value": 0}],
            },
            "zero-modulus": {"op": "mod", "args": [5, 0]},
            "nonpositive-period": {
                "op": "cyclic_delta",
                "args": [{"op": "field", "name": "theta"}, 0, -1],
            },
            "bad-bit-index": {"op": "bit", "args": [{"op": "field", "name": "status"}, 64]},
            "reversed-interval": {"op": "interval", "args": [2, 1]},
            "reversed-closed-bounds": {
                "op": "in_closed_interval",
                "args": [{"op": "field", "name": "rho"}, 2, 1],
            },
            "static-overflow": {"op": "add", "args": [I64_MAX, 1]},
            "raw-floating-expression": 1.5,
            "nonfinite-constant": {"op": "const", "value": float("inf")},
        }
        for name, expression in invalid.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_expression(expression)

    def test_field_dependent_type_and_value_errors_remain_dynamic(self):
        validate_expression({
            "op": "floor_div",
            "args": [
                {"op": "field", "source": "context", "name": "numerator"},
                {"op": "field", "source": "context", "name": "divisor"},
            ],
        })
        validate_expression({
            "op": "all",
            "args": [{"op": "field", "source": "context", "name": "predicate"}],
        })

    def test_static_if_validation_is_lazy_but_still_checks_branch_structure(self):
        unreachable_failure = {
            "op": "if",
            "condition": True,
            "then": 1,
            "else": {"op": "floor_div", "args": [1, 0]},
        }
        validate_expression(unreachable_failure)
        self.assertEqual(evaluate_expression(unreachable_failure, {}), 1)

        unreachable_type_error = {
            "op": "if",
            "condition": False,
            "then": {"op": "add", "args": [1, "not-an-integer"]},
            "else": 2,
        }
        validate_expression(unreachable_type_error)
        self.assertEqual(evaluate_expression(unreachable_type_error, {}), 2)

        with self.assertRaisesRegex(ValueError, "statically zero"):
            validate_expression({
                "op": "if",
                "condition": False,
                "then": 1,
                "else": {"op": "floor_div", "args": [1, 0]},
            })
        with self.assertRaises(ValueError):
            validate_expression({
                "op": "if",
                "condition": True,
                "then": 1,
                "else": {"op": "floor_div", "args": [1]},
            })
        with self.assertRaisesRegex(ValueError, "statically zero"):
            validate_expression({
                "op": "if",
                "condition": {"op": "field", "source": "context", "name": "choose"},
                "then": 1,
                "else": {"op": "floor_div", "args": [1, 0]},
            })


class StoredExpressionValidationTests(unittest.TestCase):
    def test_relation_support_and_compatibility_validate_their_expressions(self):
        cases = [
            (
                "relation",
                "relation:invalid-expression",
                {
                    "instance_id": "instance:any",
                    "expression": {"op": "unknown"},
                },
            ),
            (
                "support",
                "support:invalid-expression",
                {"expression": {"op": "eq", "args": [1]}},
            ),
            (
                "compatibility",
                "compatibility:invalid-expression",
                {"expression": {"op": "field", "source": "filesystem", "name": "path"}},
            ),
        ]
        for record_type, ident, payload in cases:
            with self.subTest(record_type=record_type), self.assertRaisesRegex(ValueError, "expression is invalid"):
                make_record(record_type, ident, payload)

    def test_transition_validates_fields_expressions_and_lineage_salt(self):
        with self.assertRaisesRegex(ValueError, "unknown State64 fields"):
            make_record(
                "transition",
                "transition:unknown-field",
                {"set": {"imaginary": {"op": "const", "value": 1}}},
            )
        with self.assertRaisesRegex(ValueError, "set.output is invalid"):
            make_record(
                "transition",
                "transition:invalid-expression",
                {"set": {"output": {"op": "add", "args": [1]}}},
            )
        for invalid_salt in (True, "1", None):
            with self.subTest(lineage_salt=invalid_salt), self.assertRaisesRegex(
                ValueError, "lineage_salt must be an integer"
            ):
                make_record(
                    "transition",
                    "transition:invalid-salt",
                    {"set": {"output": 1}, "lineage_salt": invalid_salt},
                )

        valid = make_record(
            "transition",
            "transition:valid-structure",
            {
                "set": {"output": {"op": "const", "value": 1}},
                "add": {
                    "rho": {"op": "field", "source": "context", "name": "dynamic_delta"}
                },
                "xor": {"status": 1},
                "lineage_salt": 7,
            },
        )
        self.assertEqual(valid["record_type"], "transition")


if __name__ == "__main__":
    unittest.main()
