"""Certified interval crossing, simultaneous event sets, and deterministic ordering."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .canonical import attach_hash
from .expression import affine_coefficients, evaluate_dual_interval, evaluate_point
from .interval import ClosedInterval
from .model import IntervalWorld, Relation
from .rational import Q


@dataclass(frozen=True, slots=True)
class CrossingResult:
    relation: Relation
    accepted: bool
    status: str
    exact_root: Q | None
    bracket: ClosedInterval
    certificate: Mapping[str, Any]


def qrecord(value: Q | None) -> dict[str, int] | None:
    return None if value is None else value.to_record()


def state_record(state: Mapping[str, Q]) -> dict[str, dict[str, int]]:
    return {name: value.to_record() for name, value in sorted(state.items())}


def _opposite_sign(a: Q, b: Q) -> bool:
    return a.sign() * b.sign() < 0


def certify_crossing(
    world: IntervalWorld,
    relation: Relation,
    bracket: ClosedInterval,
    *,
    refine_steps: int | None = None,
) -> CrossingResult:
    trajectory = world.trajectory
    active = relation.active_time.intersection(bracket)
    if active is None or active != bracket:
        record = attach_hash({
            "schema": "TOM-CERTIFIED-CROSSING-0.3",
            "world_hash": world.content_hash,
            "relation_id": relation.id,
            "relation_hash": relation.content_hash,
            "status": "outside-active-time",
            "accepted": False,
            "bracket": bracket.to_record(),
        })
        return CrossingResult(relation, False, "outside-active-time", None, bracket, record)

    steps = int(world.solver.get("refine_steps", 24) if refine_steps is None else refine_steps)
    max_steps = int(world.solver.get("max_refine_steps", 128))
    if steps < 0 or steps > max_steps:
        raise ValueError(f"refine_steps {steps} outside 0..{max_steps}")

    f0 = evaluate_point(relation.expression, trajectory, bracket.lower)
    f1 = evaluate_point(relation.expression, trajectory, bracket.upper)
    dual = evaluate_dual_interval(relation.expression, trajectory, bracket)
    affine = affine_coefficients(relation.expression, trajectory)
    exact_root: Q | None = None
    existence = False
    root_kind = "none"

    if f0 == Q(0):
        exact_root = bracket.lower
        existence = True
        root_kind = "left-endpoint"
    elif f1 == Q(0):
        exact_root = bracket.upper
        existence = True
        root_kind = "right-endpoint"
    elif _opposite_sign(f0, f1):
        existence = True
        root_kind = "sign-change"
        if affine is not None and affine[0] != Q(0):
            candidate = -affine[1] / affine[0]
            if bracket.contains(candidate):
                exact_root = candidate
                root_kind = "exact-affine"

    refined = bracket
    rf0, rf1 = f0, f1
    bisections = 0
    if existence and exact_root is None and _opposite_sign(f0, f1):
        lo, hi = bracket.lower, bracket.upper
        flo, fhi = f0, f1
        for _ in range(steps):
            mid = (lo + hi) / 2
            fm = evaluate_point(relation.expression, trajectory, mid)
            bisections += 1
            if fm == Q(0):
                exact_root = mid
                lo = hi = mid
                flo = fhi = fm
                root_kind = "exact-bisection"
                break
            if _opposite_sign(flo, fm):
                hi, fhi = mid, fm
            else:
                lo, flo = mid, fm
        refined = ClosedInterval(lo, hi)
        rf0, rf1 = flo, fhi

    derivative_excludes_zero = dual.derivative.excludes_zero()
    unique = existence and derivative_excludes_zero
    root_state: dict[str, Q] | None = None
    support_ok = False
    compatibility_ok = False
    if exact_root is not None:
        root_state = trajectory.state_at(exact_root)
        support_ok = world.supports[relation.support_id].accepts_point(root_state)
        compatibility_ok = world.compatibilities[relation.compatibility_id].accepts(root_state)
    elif existence:
        root_state_interval = trajectory.state_interval(refined)
        support_ok = world.supports[relation.support_id].contains_interval(root_state_interval)
        # Equality compatibility over a nonpoint bracket is certified only when
        # each constrained field interval is the required point.
        compatibility = world.compatibilities[relation.compatibility_id]
        compatibility_ok = all(
            name in root_state_interval
            and root_state_interval[name].is_point()
            and root_state_interval[name].lower == expected
            for name, expected in compatibility.equals.items()
        )

    accepted = existence and support_ok and compatibility_ok
    if not existence:
        status = "no-certified-crossing"
    elif not support_ok:
        status = "outside-support"
    elif not compatibility_ok:
        status = "incompatible"
    elif exact_root is None:
        status = "accepted-bracket"
    else:
        status = "accepted-exact-root"

    record: dict[str, Any] = {
        "schema": "TOM-CERTIFIED-CROSSING-0.3",
        "world_hash": world.content_hash,
        "trajectory_id": trajectory.id,
        "trajectory_hash": trajectory.content_hash,
        "relation_id": relation.id,
        "relation_hash": relation.content_hash,
        "event_id": relation.event_id,
        "priority": relation.priority,
        "status": status,
        "accepted": accepted,
        "continuity_basis": "finite expression over exact rational affine fields using +,-,*",
        "original_bracket": bracket.to_record(),
        "original_endpoint_residuals": {
            "lower": f0.to_record(),
            "upper": f1.to_record(),
        },
        "original_residual_interval": dual.value.to_record(),
        "derivative_interval": dual.derivative.to_record(),
        "derivative_excludes_zero": derivative_excludes_zero,
        "existence_certified_by_sign_change_or_exact_endpoint": existence,
        "uniqueness_certified_by_monotonic_derivative": unique,
        "root_kind": root_kind,
        "exact_root_time": qrecord(exact_root),
        "refined_bracket": refined.to_record(),
        "refined_endpoint_residuals": {
            "lower": rf0.to_record(),
            "upper": rf1.to_record(),
        },
        "bisections": bisections,
        "support_id": relation.support_id,
        "support_ok": support_ok,
        "compatibility_id": relation.compatibility_id,
        "compatibility_ok": compatibility_ok,
        "root_state": None if root_state is None else state_record(root_state),
        "ordering_key": None if exact_root is None else [
            exact_root.to_record(), relation.priority, relation.id,
            relation.event_id, relation.content_hash,
        ],
    }
    record = attach_hash(record)
    return CrossingResult(relation, accepted, status, exact_root, refined, record)


def certified_events(
    world: IntervalWorld,
    start: Any,
    end: Any,
    *,
    refine_steps: int | None = None,
) -> list[CrossingResult]:
    start_q = Q.from_value(start)
    end_q = Q.from_value(end)
    if end_q < start_q:
        raise ValueError("event interval end is before start")
    if not world.trajectory.domain.contains(start_q) or not world.trajectory.domain.contains(end_q):
        raise ValueError("event interval lies outside trajectory domain")

    results: list[CrossingResult] = []
    seen: set[tuple[str, str]] = set()
    for tick in range(start_q.floor(), end_q.ceil()):
        bracket = ClosedInterval(max(start_q, Q(tick)), min(end_q, Q(tick + 1)))
        if bracket.upper < bracket.lower:
            continue
        for relation in world.relations:
            result = certify_crossing(world, relation, bracket, refine_steps=refine_steps)
            if not result.accepted:
                continue
            root_key = result.exact_root.to_text() if result.exact_root is not None else result.bracket.to_text()
            key = (relation.id, root_key)
            if key in seen:
                continue
            seen.add(key)
            results.append(result)
    results.sort(key=event_order_key)
    return results


def event_order_key(result: CrossingResult) -> tuple[Any, ...]:
    if result.exact_root is None:
        time_key = (1, result.bracket.lower.as_fraction(), result.bracket.upper.as_fraction())
    else:
        time_key = (0, result.exact_root.as_fraction(), result.exact_root.as_fraction())
    relation = result.relation
    return (*time_key, relation.priority, relation.id, relation.event_id, relation.content_hash)


def next_event_set(
    world: IntervalWorld,
    after: Any,
    before: Any,
    *,
    include_after: bool = False,
    refine_steps: int | None = None,
) -> dict[str, Any]:
    after_q = Q.from_value(after)
    results = certified_events(world, after_q, before, refine_steps=refine_steps)
    results = [
        result for result in results
        if result.exact_root is not None
        and (result.exact_root >= after_q if include_after else result.exact_root > after_q)
    ]
    if not results:
        return attach_hash({
            "schema": "TOM-NEXT-EVENT-SET-0.3",
            "world_hash": world.content_hash,
            "after": after_q.to_record(),
            "before": Q.from_value(before).to_record(),
            "status": "none",
            "events": [],
        })
    earliest = results[0].exact_root
    assert earliest is not None
    simultaneous = [result for result in results if result.exact_root == earliest]
    simultaneous.sort(key=event_order_key)
    record = {
        "schema": "TOM-NEXT-EVENT-SET-0.3",
        "world_hash": world.content_hash,
        "trajectory_id": world.trajectory.id,
        "after": after_q.to_record(),
        "before": Q.from_value(before).to_record(),
        "include_after": include_after,
        "status": "accepted",
        "event_time": earliest.to_record(),
        "simultaneity_basis": "exact equal canonical rational root time",
        "event_count": len(simultaneous),
        "event_order": [result.relation.event_id for result in simultaneous],
        "relation_order": [result.relation.id for result in simultaneous],
        "ordering_rule": ["root_time", "priority", "relation_id", "event_id", "relation_hash"],
        "events": [dict(result.certificate) for result in simultaneous],
    }
    return attach_hash(record)


def events_certificate(
    world: IntervalWorld,
    start: Any,
    end: Any,
    *,
    refine_steps: int | None = None,
) -> dict[str, Any]:
    results = certified_events(world, start, end, refine_steps=refine_steps)
    return attach_hash({
        "schema": "TOM-CERTIFIED-EVENTS-IN-SUPPORT-0.3",
        "world_hash": world.content_hash,
        "start": Q.from_value(start).to_record(),
        "end": Q.from_value(end).to_record(),
        "event_count": len(results),
        "ordering_rule": ["root_time", "priority", "relation_id", "event_id", "relation_hash"],
        "events": [dict(result.certificate) for result in results],
    })
