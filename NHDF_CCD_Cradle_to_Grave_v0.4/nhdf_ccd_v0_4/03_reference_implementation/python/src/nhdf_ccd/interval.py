from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math

from .oracles import SeparationOracle
from .types import CCDConfig, CCDStatus, CollisionCertificate


PHI = (1.0 + 5.0 ** 0.5) / 2.0


@dataclass(order=True, slots=True)
class _Node:
    priority: tuple[float, int]
    a: float = field(compare=False)
    b: float = field(compare=False)
    depth: int = field(compare=False)


def bounded_interval_refinement(oracle: SeparationOracle, config: CCDConfig) -> CollisionCertificate:
    """Bounded earliest-first interval search.

    The split policy can be midpoint or golden-ratio. The policy changes work
    ordering only; it is not allowed to change the safety test.
    """
    config.validate()
    pair = (oracle.body_a.body_id, oracle.body_b.body_id)
    backend = f"bounded_interval_{config.split_policy}"
    s0 = oracle.evaluate(0.0)
    if s0.distance < -config.distance_tolerance:
        return CollisionCertificate(CCDStatus.INITIAL_OVERLAP, pair, backend, 0.0, 0.0, s0, reason="negative initial separation").finalize()
    if s0.distance <= config.distance_tolerance:
        return CollisionCertificate(CCDStatus.HIT, pair, backend, 0.0, 0.0, s0, reason="initial contact").finalize()

    queue: list[_Node] = [_Node((0.0, 0), 0.0, 1.0, 0)]
    trace: list[dict[str, float | int | str]] = []
    nodes = 0
    unresolved: tuple[float, float] | None = None
    while queue and nodes < config.interval_max_nodes:
        node = heapq.heappop(queue)
        nodes += 1
        a, b = node.a, node.b
        mid = 0.5 * (a + b)
        sm = oracle.evaluate(mid)
        L = oracle.closure_speed_bound(a, b)
        if not math.isfinite(sm.distance) or not math.isfinite(L) or L < 0.0:
            return CollisionCertificate(CCDStatus.INVALID_INPUT, pair, backend, reason="invalid oracle value", iterations=nodes, trace=trace).finalize()
        lower_bound = sm.distance - L * (b - a) * 0.5
        if len(trace) < config.max_trace_steps:
            trace.append({"node": nodes, "a": a, "b": b, "mid": mid, "distance_mid": sm.distance, "L": L, "lower_bound": lower_bound})
        if lower_bound > 0.0:
            continue
        if sm.distance <= config.distance_tolerance:
            return CollisionCertificate(
                CCDStatus.HIT,
                pair,
                backend,
                toi_lower=a,
                toi_upper=b,
                sample=sm,
                iterations=nodes,
                reason="sampled contact inside an uncertified interval",
                trace=trace,
            ).finalize()
        if b - a <= config.time_tolerance:
            unresolved = (a, b) if unresolved is None or a < unresolved[0] else unresolved
            continue
        if config.split_policy == "golden":
            c = a + (b - a) / PHI
        else:
            c = mid
        if not (a < c < b):
            c = mid
        heapq.heappush(queue, _Node((a, node.depth + 1), a, c, node.depth + 1))
        heapq.heappush(queue, _Node((c, node.depth + 1), c, b, node.depth + 1))

    if queue or unresolved is not None:
        bracket = unresolved or (queue[0].a, queue[0].b)
        return CollisionCertificate(
            CCDStatus.INCONCLUSIVE,
            pair,
            backend,
            toi_lower=bracket[0],
            toi_upper=bracket[1],
            iterations=nodes,
            reason="bounded refinement could not certify all remaining intervals",
            trace=trace,
        ).finalize()
    return CollisionCertificate(CCDStatus.NO_HIT, pair, backend, iterations=nodes, reason="all intervals certified collision-free", trace=trace).finalize()
