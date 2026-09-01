from __future__ import annotations

import unittest

from tom_world.expression import evaluate_expression


class ExpressionIntegrityTests(unittest.TestCase):
    def test_max_and_min_reject_results_outside_i64(self):
        with self.assertRaisesRegex(OverflowError, "signed 64-bit"):
            evaluate_expression({"op": "max", "args": [1 << 80, 0]}, {})
        with self.assertRaisesRegex(OverflowError, "signed 64-bit"):
            evaluate_expression({"op": "min", "args": [-(1 << 80), 0]}, {})

    def test_contains_zero_rejects_reversed_interval(self):
        expression = {
            "op": "contains_zero",
            "args": [{"lower": 1, "upper": -1}],
        }
        with self.assertRaisesRegex(ValueError, "lower bound exceeds upper bound"):
            evaluate_expression(expression, {})

    def test_in_closed_interval_rejects_reversed_bounds(self):
        expression = {
            "op": "in_closed_interval",
            "args": [0, 1, -1],
        }
        with self.assertRaisesRegex(ValueError, "lower bound exceeds upper bound"):
            evaluate_expression(expression, {})


if __name__ == "__main__":
    unittest.main()
