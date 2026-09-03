from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world03.baseline import trusted_affine_baseline
from tom_world03.canonical import attach_hash, canonical_bytes, verify_hash
from tom_world03.expression import affine_coefficients, evaluate_dual_interval, evaluate_point
from tom_world03.interval import ClosedInterval
from tom_world03.io import load_world
from tom_world03.model import IntervalWorld, Relation, TransitionOp
from tom_world03.rational import Q
from tom_world03.solver import certify_crossing, certified_events, events_certificate, next_event_set
from tom_world03.transitions import TransitionConflict, apply_event_set, merge_transition_ops

WORLD_PATH = ROOT / "examples/world03/interval_event_world.json"
WORLD_RECORD, WORLD = load_world(WORLD_PATH)


def relation_by_id(ident: str) -> Relation:
    return next(r for r in WORLD.relations if r.id == ident)


def const(value: int, den: int = 1):
    return {"op": "const", "value": {"num": value, "den": den}}


def field(name: str):
    return {"op": "field", "name": name}


def time_expr():
    return {"op": "time"}


def binary(op: str, a, b):
    return {"op": op, "args": [a, b]}


class RationalTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(Q(10, -20), Q(-1, 2))
        self.assertEqual(Q(0, 99), Q(0, 1))

    def test_arithmetic(self):
        self.assertEqual(Q(1, 2) + Q(1, 3), Q(5, 6))
        self.assertEqual(Q(2, 3) * Q(9, 4), Q(3, 2))
        self.assertEqual(Q(3, 5) / Q(9, 10), Q(2, 3))

    def test_text_and_record_roundtrip(self):
        q = Q.from_value("-14/6")
        self.assertEqual(q.to_text(), "-7/3")
        self.assertEqual(Q.from_value(q.to_record()), q)

    def test_floor_ceil_negative(self):
        self.assertEqual(Q(-7, 3).floor(), -3)
        self.assertEqual(Q(-7, 3).ceil(), -2)

    def test_zero_denominator_rejected(self):
        with self.assertRaisesRegex(ValueError, "denominator"):
            Q(1, 0)


class IntervalTests(unittest.TestCase):
    def test_sign_classes(self):
        self.assertEqual(ClosedInterval(Q(-2), Q(-1)).sign_class(), "negative")
        self.assertEqual(ClosedInterval(Q(1), Q(2)).sign_class(), "positive")
        self.assertEqual(ClosedInterval(Q(-1), Q(2)).sign_class(), "straddles-zero")
        self.assertEqual(ClosedInterval.point(0).sign_class(), "zero")

    def test_exact_arithmetic(self):
        a = ClosedInterval(Q(-1), Q(2))
        b = ClosedInterval(Q(3), Q(4))
        self.assertEqual(a + b, ClosedInterval(Q(2), Q(6)))
        self.assertEqual(a - b, ClosedInterval(Q(-5), Q(-1)))
        self.assertEqual(a * b, ClosedInterval(Q(-4), Q(8)))

    def test_reciprocal_and_division(self):
        a = ClosedInterval(Q(2), Q(4))
        self.assertEqual(a.reciprocal(), ClosedInterval(Q(1, 4), Q(1, 2)))
        self.assertEqual(ClosedInterval.point(1) / a, ClosedInterval(Q(1, 4), Q(1, 2)))
        with self.assertRaises(ZeroDivisionError):
            ClosedInterval(Q(-1), Q(1)).reciprocal()

    def test_intersection_and_subset(self):
        a = ClosedInterval(Q(0), Q(5))
        self.assertEqual(a.intersection([3, 7]), ClosedInterval(Q(3), Q(5)))
        self.assertTrue(ClosedInterval(Q(1), Q(2)).subset_of(a))
        self.assertIsNone(a.intersection([6, 7]))

    def test_inverted_interval_rejected(self):
        with self.assertRaisesRegex(ValueError, "below lower"):
            ClosedInterval(Q(2), Q(1))


class ExpressionTests(unittest.TestCase):
    def test_affine_trajectory_state(self):
        state = WORLD.trajectory.state_at(Q(5, 2))
        self.assertEqual(state["x"], Q(5))
        self.assertEqual(state["clock"], Q(5, 2))
        self.assertEqual(state["mode"], Q(1))

    def test_point_and_dual_interval(self):
        expr = binary("sub", field("x"), const(5))
        self.assertEqual(evaluate_point(expr, WORLD.trajectory, Q(2)), Q(-1))
        dual = evaluate_dual_interval(expr, WORLD.trajectory, ClosedInterval(Q(2), Q(3)))
        self.assertEqual(dual.value, ClosedInterval(Q(-1), Q(1)))
        self.assertEqual(dual.derivative, ClosedInterval.point(2))

    def test_affine_coefficients(self):
        expr = binary("sub", binary("mul", const(3), field("x")), const(15))
        self.assertEqual(affine_coefficients(expr, WORLD.trajectory), (Q(6), Q(-15)))

    def test_nonlinear_expression_is_not_affine(self):
        expr = binary("mul", binary("sub", time_expr(), const(2)), binary("sub", time_expr(), const(4)))
        self.assertIsNone(affine_coefficients(expr, WORLD.trajectory))
        dual = evaluate_dual_interval(expr, WORLD.trajectory, ClosedInterval(Q(1), Q(3)))
        self.assertTrue(dual.value.contains_zero())


class CrossingTests(unittest.TestCase):
    def test_certified_exact_affine_crossing(self):
        result = certify_crossing(
            WORLD, relation_by_id("relation:x-equals-five"), ClosedInterval(Q(2), Q(3))
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.exact_root, Q(5, 2))
        self.assertEqual(result.status, "accepted-exact-root")
        self.assertTrue(result.certificate["existence_certified_by_sign_change_or_exact_endpoint"])
        self.assertTrue(result.certificate["uniqueness_certified_by_monotonic_derivative"])
        self.assertEqual(result.certificate["original_endpoint_residuals"]["lower"], Q(-1).to_record())
        self.assertEqual(result.certificate["original_endpoint_residuals"]["upper"], Q(1).to_record())
        self.assertTrue(verify_hash(result.certificate))

    def test_outside_support_is_rejected(self):
        result = certify_crossing(
            WORLD, relation_by_id("relation:unsupported-x-equals-five"), ClosedInterval(Q(2), Q(3))
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "outside-support")

    def test_incompatible_is_rejected(self):
        result = certify_crossing(
            WORLD, relation_by_id("relation:incompatible-x-equals-six"), ClosedInterval(Q(2), Q(4))
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "incompatible")

    def test_outside_active_time_is_rejected(self):
        result = certify_crossing(
            WORLD, relation_by_id("relation:inactive-x-equals-two"), ClosedInterval(Q(0), Q(2))
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "outside-active-time")

    def test_same_sign_has_no_certified_crossing(self):
        result = certify_crossing(
            WORLD, relation_by_id("relation:x-equals-five"), ClosedInterval(Q(0), Q(1))
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "no-certified-crossing")

    def test_nonlinear_sign_change_and_exact_bisection(self):
        expr = binary("mul", binary("sub", time_expr(), const(2)), binary("sub", time_expr(), const(4)))
        relation_record = attach_hash({
            "id": "relation:nonlinear-test",
            "kind": "continuous-zero-relation",
            "relation_interface": "SDF0@Def",
            "domain": "affine-rational-trajectory",
            "codomain": "exact-rational-residual",
            "zero_locus": "(t-2)(t-4)=0",
            "priority": 0,
            "expression": expr,
            "support_id": "support:main",
            "compatibility_id": "compat:mode-1",
            "active_time": {"lower": Q(0).to_record(), "upper": Q(10).to_record()},
            "event_id": "event:nonlinear",
            "transition": [],
        })
        relation = Relation.from_record(relation_record)
        result = certify_crossing(WORLD, relation, ClosedInterval(Q(1), Q(3)), refine_steps=4)
        self.assertTrue(result.accepted)
        self.assertEqual(result.exact_root, Q(2))
        self.assertEqual(result.certificate["root_kind"], "exact-bisection")
        # The derivative interval touches zero, so the interval proof does not
        # overclaim uniqueness even though this particular bracket contains one root.
        self.assertFalse(result.certificate["uniqueness_certified_by_monotonic_derivative"])

    def test_refinement_budget_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            certify_crossing(
                WORLD, relation_by_id("relation:x-equals-five"), ClosedInterval(Q(2), Q(3)),
                refine_steps=999,
            )

    def test_certificate_is_deterministic(self):
        relation = relation_by_id("relation:x-equals-five")
        a = certify_crossing(WORLD, relation, ClosedInterval(Q(2), Q(3))).certificate
        b = certify_crossing(WORLD, relation, ClosedInterval(Q(2), Q(3))).certificate
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))


class EventSetTests(unittest.TestCase):
    def test_events_are_deduplicated_at_integer_boundaries(self):
        results = certified_events(WORLD, 0, 10)
        ids = [(r.relation.id, r.exact_root.to_text()) for r in results]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 4)

    def test_simultaneous_set_and_order(self):
        event_set = next_event_set(WORLD, 0, 10)
        self.assertEqual(event_set["event_time"], Q(5, 2).to_record())
        self.assertEqual(event_set["event_count"], 3)
        self.assertEqual(event_set["relation_order"], [
            "relation:time-equals-five-halves",
            "relation:triple-x-equals-fifteen",
            "relation:x-equals-five",
        ])
        self.assertTrue(verify_hash(event_set))

    def test_include_after_semantics(self):
        excluded = next_event_set(WORLD, Q(5, 2), 10)
        included = next_event_set(WORLD, Q(5, 2), 10, include_after=True)
        self.assertEqual(excluded["event_time"], Q(5).to_record())
        self.assertEqual(included["event_time"], Q(5, 2).to_record())

    def test_events_certificate_order(self):
        record = events_certificate(WORLD, 0, 10)
        roots = [Q.from_value(e["exact_root_time"]) for e in record["events"]]
        self.assertEqual(roots, [Q(5, 2), Q(5, 2), Q(5, 2), Q(5)])
        self.assertTrue(verify_hash(record))

    def test_no_event_result(self):
        record = next_event_set(WORLD, 9, 10)
        self.assertEqual(record["status"], "none")
        self.assertEqual(record["events"], [])


class TransitionTests(unittest.TestCase):
    def test_simultaneous_transition_merge(self):
        event_set = next_event_set(WORLD, 0, 10)
        result = apply_event_set(WORLD, event_set)
        self.assertEqual(Q.from_value(result["post_state"]["counter"]), Q(3))
        self.assertEqual(Q.from_value(result["post_state"]["output"]), Q(25))
        self.assertEqual(Q.from_value(result["pre_state"]["x"]), Q(5))
        self.assertTrue(verify_hash(result))

    def test_equal_sets_and_adds_merge(self):
        a = relation_by_id("relation:x-equals-five")
        b = relation_by_id("relation:triple-x-equals-fifteen")
        audit, merged = merge_transition_ops([a, b])
        self.assertEqual(merged["counter"], ("add", Q(3)))
        self.assertEqual(len(audit), 1)

    def test_unequal_set_conflict(self):
        a = Relation(
            "a", 0, const(0), "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)),
            "ea", (TransitionOp("output", "set", Q(1)),), "sha256:" + "a" * 64,
        )
        b = Relation(
            "b", 0, const(0), "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)),
            "eb", (TransitionOp("output", "set", Q(2)),), "sha256:" + "b" * 64,
        )
        with self.assertRaisesRegex(TransitionConflict, "set conflict"):
            merge_transition_ops([a, b])

    def test_mixed_mode_conflict(self):
        a = Relation(
            "a", 0, const(0), "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)),
            "ea", (TransitionOp("output", "set", Q(1)),), "sha256:" + "a" * 64,
        )
        b = Relation(
            "b", 0, const(0), "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)),
            "eb", (TransitionOp("output", "add", Q(2)),), "sha256:" + "b" * 64,
        )
        with self.assertRaisesRegex(TransitionConflict, "mixed modes"):
            merge_transition_ops([a, b])


class BaselineAndIntegrationTests(unittest.TestCase):
    def test_independent_baseline_matches_solver(self):
        baseline = trusted_affine_baseline(WORLD_RECORD, 0, 10)
        solver = events_certificate(WORLD, 0, 10)
        selected = [
            {
                "relation_id": event["relation_id"],
                "event_id": event["event_id"],
                "priority": event["priority"],
                "root": event["exact_root_time"],
            }
            for event in solver["events"]
        ]
        self.assertEqual(selected, baseline["events"])
        self.assertTrue(verify_hash(baseline))

    def test_tomagi_integer_anchor_comparison(self):
        report = json.loads((ROOT / "validation/world03/tomagi_trajectory_baseline.json").read_text())
        self.assertTrue(report["affine_trajectory_matches_all_integer_tomagi_anchors"])
        self.assertTrue(report["python_c_full_trace_equal"])
        self.assertEqual(len(report["anchors"]), 11)
        self.assertTrue(verify_hash(report))

    def test_tomagi_abi_unchanged(self):
        from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE
        self.assertEqual((HEADER_SIZE, STATE_SIZE, CELL_SIZE), (128, 64, 48))

    def test_fixture_report_is_passing(self):
        report = json.loads((ROOT / "validation/world03/fixture_report.json").read_text())
        self.assertTrue(report["trusted_baseline_equal"])
        self.assertTrue(report["tomagi_integer_anchor_equal"])
        self.assertTrue(report["python_c_tomagi_trace_equal"])
        self.assertTrue(report["conflict_rejection"])
        self.assertTrue(verify_hash(report))

    def test_world_hash_tamper_rejected(self):
        bad = copy.deepcopy(WORLD_RECORD)
        bad["solver"]["refine_steps"] += 1
        with self.assertRaisesRegex(ValueError, "content hash mismatch"):
            IntervalWorld.from_record(bad)

    def test_canonical_seed_is_still_exact(self):
        seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
        self.assertEqual(len(seed), 244)
        self.assertFalse(seed.endswith(b"\n"))
        self.assertEqual(
            hashlib.sha256(seed).hexdigest(),
            "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
        )

    def test_cli_next_event_set(self):
        output = subprocess.check_output([
            sys.executable, "-m", "tom_world03", "next-event-set",
            str(WORLD_PATH), "0", "10",
        ], cwd=ROOT, env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src/python")})
        record = json.loads(output)
        self.assertEqual(record["event_count"], 3)

    def test_schema_when_jsonschema_is_available(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "spec/tom_world_query_kernel_0_3.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(WORLD_RECORD)


if __name__ == "__main__":
    unittest.main()
