from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Callable

from .geometry import point_triangle_distance2, segment_segment_distance2, triangle_normal
from .model import Certificate, LinearPoint, Status, Vec3, Witness, all_finite
from .polynomial import real_roots_unit_interval


def _coplanarity_vf_coeff(p: LinearPoint, a: LinearPoint, b: LinearPoint, c: LinearPoint) -> list[float]:
    r0 = p.p0 - a.p0
    r1 = p.velocity - a.velocity
    u0 = b.p0 - a.p0
    u1 = b.velocity - a.velocity
    v0 = c.p0 - a.p0
    v1 = c.velocity - a.velocity
    c0 = u0.cross(v0)
    c1 = u1.cross(v0) + u0.cross(v1)
    c2 = u1.cross(v1)
    return [
        r0.dot(c0),
        r1.dot(c0) + r0.dot(c1),
        r1.dot(c1) + r0.dot(c2),
        r1.dot(c2),
    ]


def _coplanarity_ee_coeff(a0: LinearPoint, a1: LinearPoint, b0: LinearPoint, b1: LinearPoint) -> list[float]:
    r0 = b0.p0 - a0.p0
    r1 = b0.velocity - a0.velocity
    u0 = a1.p0 - a0.p0
    u1 = a1.velocity - a0.velocity
    v0 = b1.p0 - b0.p0
    v1 = b1.velocity - b0.velocity
    c0 = u0.cross(v0)
    c1 = u1.cross(v0) + u0.cross(v1)
    c2 = u1.cross(v1)
    return [
        r0.dot(c0),
        r1.dot(c0) + r0.dot(c1),
        r1.dot(c1) + r0.dot(c2),
        r1.dot(c2),
    ]


def _vf_witness(t: float, p: LinearPoint, a: LinearPoint, b: LinearPoint, c: LinearPoint) -> Witness:
    pt, at, bt, ct = p.at(t), a.at(t), b.at(t), c.at(t)
    res = point_triangle_distance2(pt, at, bt, ct)
    diff = pt - res.point
    normal = diff.normalized()
    if normal.norm2() == 0.0:
        normal = triangle_normal(at, bt, ct)
    return Witness(pt, res.point, normal, res.barycentric, None, math.sqrt(res.distance2))


def _ee_witness(t: float, a0: LinearPoint, a1: LinearPoint, b0: LinearPoint, b1: LinearPoint) -> Witness:
    res = segment_segment_distance2(a0.at(t), a1.at(t), b0.at(t), b1.at(t))
    diff = res.point_a - res.point_b
    normal = diff.normalized()
    if normal.norm2() == 0.0:
        da = a1.at(t) - a0.at(t)
        db = b1.at(t) - b0.at(t)
        normal = da.cross(db).normalized()
    return Witness(res.point_a, res.point_b, normal, None, (res.s, res.t), math.sqrt(res.distance2))


@dataclass(order=True)
class _Interval:
    lo: float
    hi: float
    depth: int = 0


def _distance_interval_fallback(
    distance_at: Callable[[float], tuple[float, Witness]],
    lipschitz: float,
    thickness: float,
    time_tol: float,
    geom_tol: float,
    max_intervals: int,
    query_type: str,
    pair_id: str,
    method: str,
) -> Certificate:
    """Conservative branch-and-bound fallback using a sound distance-rate bound."""
    pq: list[_Interval] = [_Interval(0.0, 1.0, 0)]
    heapq.heapify(pq)
    best_hit: tuple[float, float, Witness] | None = None
    unresolved: list[tuple[float, float]] = []
    iterations = 0
    trace: list[dict] = []

    while pq and iterations < max_intervals:
        iv = heapq.heappop(pq)
        iterations += 1
        if best_hit is not None and iv.lo >= best_hit[1]:
            continue
        mid = 0.5 * (iv.lo + iv.hi)
        samples = []
        for t in (iv.lo, mid, iv.hi):
            d, w = distance_at(t)
            samples.append((t, d, w))
        sample_t, sample_d, sample_w = min(samples, key=lambda x: (x[1], x[0]))
        lower_bounds = []
        for t, d, _ in samples:
            radius = max(abs(t - iv.lo), abs(iv.hi - t))
            lower_bounds.append(d - lipschitz * radius)
        lb = max(0.0, max(lower_bounds))
        if len(trace) < 64:
            trace.append({"lo": iv.lo, "hi": iv.hi, "sample_min": sample_d, "distance_lower_bound": lb, "depth": iv.depth})
        if lb > thickness + geom_tol:
            continue
        contacts = [(t, w) for t, d, w in samples if d <= thickness + geom_tol]
        if contacts:
            t_hit, w_hit = min(contacts, key=lambda x: x[0])
            candidate = (iv.lo, t_hit, w_hit)
            if best_hit is None or t_hit < best_hit[1]:
                best_hit = candidate
        if iv.hi - iv.lo <= time_tol:
            if not contacts:
                unresolved.append((iv.lo, iv.hi))
            continue
        left = _Interval(iv.lo, mid, iv.depth + 1)
        right = _Interval(mid, iv.hi, iv.depth + 1)
        heapq.heappush(pq, right)
        heapq.heappush(pq, left)

    if pq:
        earliest = min(x.lo for x in pq)
        unresolved.append((earliest, min(1.0, earliest + time_tol)))
    if best_hit is not None:
        earlier_uncertain = [u for u in unresolved if u[0] < best_hit[1] - time_tol]
        if earlier_uncertain:
            return Certificate(
                Status.INCONCLUSIVE, query_type, pair_id=pair_id,
                toi_lower=min(u[0] for u in earlier_uncertain), toi_upper=best_hit[1],
                witness=best_hit[2], iterations=iterations, method=method,
                termination_reason="contact sample found but earlier interval remained unresolved",
                tolerance=geom_tol, trace=trace,
            )
        return Certificate(
            Status.HIT, query_type, pair_id=pair_id,
            toi_lower=max(0.0, best_hit[0]), toi_upper=best_hit[1],
            witness=best_hit[2], iterations=iterations, method=method,
            termination_reason="Lipschitz-pruned interval search isolated a contact upper bound",
            tolerance=geom_tol, trace=trace,
        )
    if unresolved:
        lo = min(x[0] for x in unresolved)
        hi = max(x[1] for x in unresolved if x[0] == lo)
        status = Status.RESOURCE_EXHAUSTED if pq else Status.INCONCLUSIVE
        return Certificate(
            status, query_type, pair_id=pair_id, toi_lower=lo, toi_upper=hi,
            iterations=iterations, method=method,
            termination_reason="distance lower bound could not separate the features within the budget",
            tolerance=geom_tol, trace=trace,
        )
    return Certificate(
        Status.MISS, query_type, pair_id=pair_id, iterations=iterations,
        method=method, termination_reason="all time intervals certified separated",
        tolerance=geom_tol, trace=trace,
    )


def vertex_face_ccd(
    p: LinearPoint,
    a: LinearPoint,
    b: LinearPoint,
    c: LinearPoint,
    *,
    thickness: float = 0.0,
    geom_tol: float = 1e-9,
    time_tol: float = 1e-10,
    max_intervals: int = 200_000,
    pair_id: str = "",
    feature_ids: tuple[str, ...] = (),
) -> Certificate:
    points = (p.p0, p.p1, a.p0, a.p1, b.p0, b.p1, c.p0, c.p1)
    if not all_finite(points) or thickness < 0.0 or geom_tol < 0.0 or time_tol <= 0.0:
        return Certificate(Status.NUMERICAL_FAILURE, "vertex-face", pair_id=pair_id, feature_ids=feature_ids, method="input-validation", termination_reason="non-finite or invalid input")

    w0 = _vf_witness(0.0, p, a, b, c)
    if w0.distance is not None and w0.distance <= thickness + geom_tol:
        return Certificate(Status.INITIAL_OVERLAP, "vertex-face", pair_id=pair_id, feature_ids=feature_ids, toi_lower=0.0, toi_upper=0.0, witness=w0, method="initial-distance", termination_reason="features already within contact thickness", tolerance=geom_tol)

    coeff = _coplanarity_vf_coeff(p, a, b, c)
    roots, condition, identically_zero = real_roots_unit_interval(coeff, root_tol=max(time_tol, 1e-12))
    root_hits: list[tuple[float, Witness]] = []
    for t in roots:
        w = _vf_witness(t, p, a, b, c)
        if w.distance is not None and w.distance <= thickness + geom_tol:
            root_hits.append((t, w))
    if root_hits:
        t, w = min(root_hits, key=lambda x: x[0])
        cert = Certificate(
            Status.HIT, "vertex-face", pair_id=pair_id, feature_ids=feature_ids,
            toi_lower=max(0.0, t - time_tol), toi_upper=min(1.0, t + time_tol),
            witness=w, iterations=len(roots), candidate_roots=len(roots),
            method="cubic-coplanarity+closest-point-containment",
            termination_reason="earliest admissible coplanarity root lies within the closed triangle",
            tolerance=geom_tol, condition_indicator=condition,
            metadata={"polynomial_coefficients_ascending": coeff, "persistent_coplanarity": False},
        )
        cert.validate()
        return cert

    if not identically_zero and math.isfinite(condition) and condition < 1e18:
        return Certificate(
            Status.MISS, "vertex-face", pair_id=pair_id, feature_ids=feature_ids,
            iterations=len(roots), candidate_roots=len(roots), method="cubic-coplanarity+closest-point-containment",
            termination_reason="no admissible coplanarity root produced contact",
            tolerance=geom_tol, condition_indicator=condition,
            metadata={"polynomial_coefficients_ascending": coeff, "persistent_coplanarity": False},
        )

    def distance_at(t: float) -> tuple[float, Witness]:
        w = _vf_witness(t, p, a, b, c)
        assert w.distance is not None
        return w.distance, w

    lipschitz = p.speed + max(a.speed, b.speed, c.speed)
    cert = _distance_interval_fallback(
        distance_at, lipschitz, thickness, time_tol, geom_tol, max_intervals,
        "vertex-face", pair_id, "persistent/ill-conditioned coplanarity Lipschitz fallback",
    )
    cert.feature_ids = feature_ids
    cert.candidate_roots = len(roots)
    cert.condition_indicator = condition
    cert.metadata.update({"polynomial_coefficients_ascending": coeff, "persistent_coplanarity": identically_zero, "distance_rate_bound": lipschitz})
    return cert


def edge_edge_ccd(
    a0: LinearPoint,
    a1: LinearPoint,
    b0: LinearPoint,
    b1: LinearPoint,
    *,
    thickness: float = 0.0,
    geom_tol: float = 1e-9,
    time_tol: float = 1e-10,
    max_intervals: int = 200_000,
    pair_id: str = "",
    feature_ids: tuple[str, ...] = (),
) -> Certificate:
    points = (a0.p0, a0.p1, a1.p0, a1.p1, b0.p0, b0.p1, b1.p0, b1.p1)
    if not all_finite(points) or thickness < 0.0 or geom_tol < 0.0 or time_tol <= 0.0:
        return Certificate(Status.NUMERICAL_FAILURE, "edge-edge", pair_id=pair_id, feature_ids=feature_ids, method="input-validation", termination_reason="non-finite or invalid input")

    w0 = _ee_witness(0.0, a0, a1, b0, b1)
    if w0.distance is not None and w0.distance <= thickness + geom_tol:
        return Certificate(Status.INITIAL_OVERLAP, "edge-edge", pair_id=pair_id, feature_ids=feature_ids, toi_lower=0.0, toi_upper=0.0, witness=w0, method="initial-distance", termination_reason="features already within contact thickness", tolerance=geom_tol)

    coeff = _coplanarity_ee_coeff(a0, a1, b0, b1)
    roots, condition, identically_zero = real_roots_unit_interval(coeff, root_tol=max(time_tol, 1e-12))
    root_hits: list[tuple[float, Witness]] = []
    for t in roots:
        w = _ee_witness(t, a0, a1, b0, b1)
        if w.distance is not None and w.distance <= thickness + geom_tol:
            root_hits.append((t, w))
    if root_hits:
        t, w = min(root_hits, key=lambda x: x[0])
        cert = Certificate(
            Status.HIT, "edge-edge", pair_id=pair_id, feature_ids=feature_ids,
            toi_lower=max(0.0, t - time_tol), toi_upper=min(1.0, t + time_tol),
            witness=w, iterations=len(roots), candidate_roots=len(roots),
            method="cubic-coplanarity+segment-distance",
            termination_reason="earliest admissible coplanarity root intersects both closed segments",
            tolerance=geom_tol, condition_indicator=condition,
            metadata={"polynomial_coefficients_ascending": coeff, "persistent_coplanarity": False},
        )
        cert.validate()
        return cert

    if not identically_zero and math.isfinite(condition) and condition < 1e18:
        return Certificate(
            Status.MISS, "edge-edge", pair_id=pair_id, feature_ids=feature_ids,
            iterations=len(roots), candidate_roots=len(roots), method="cubic-coplanarity+segment-distance",
            termination_reason="no admissible coplanarity root produced segment intersection",
            tolerance=geom_tol, condition_indicator=condition,
            metadata={"polynomial_coefficients_ascending": coeff, "persistent_coplanarity": False},
        )

    def distance_at(t: float) -> tuple[float, Witness]:
        w = _ee_witness(t, a0, a1, b0, b1)
        assert w.distance is not None
        return w.distance, w

    lipschitz = max(a0.speed, a1.speed) + max(b0.speed, b1.speed)
    cert = _distance_interval_fallback(
        distance_at, lipschitz, thickness, time_tol, geom_tol, max_intervals,
        "edge-edge", pair_id, "persistent/ill-conditioned coplanarity Lipschitz fallback",
    )
    cert.feature_ids = feature_ids
    cert.candidate_roots = len(roots)
    cert.condition_indicator = condition
    cert.metadata.update({"polynomial_coefficients_ascending": coeff, "persistent_coplanarity": identically_zero, "distance_rate_bound": lipschitz})
    return cert


def sphere_sphere_ccd(
    center_a: LinearPoint,
    radius_a: float,
    center_b: LinearPoint,
    radius_b: float,
    *,
    geom_tol: float = 1e-12,
    pair_id: str = "",
) -> Certificate:
    if radius_a < 0.0 or radius_b < 0.0 or not all_finite((center_a.p0, center_a.p1, center_b.p0, center_b.p1)):
        return Certificate(Status.NUMERICAL_FAILURE, "sphere-sphere", pair_id=pair_id, method="quadratic", termination_reason="invalid input")
    r = radius_a + radius_b
    s = center_a.p0 - center_b.p0
    v = center_a.velocity - center_b.velocity
    c = s.dot(s) - r * r
    if c <= geom_tol:
        n = s.normalized()
        w = Witness(center_a.p0 - n * radius_a, center_b.p0 + n * radius_b, n, distance=max(0.0, s.norm() - r))
        return Certificate(Status.INITIAL_OVERLAP, "sphere-sphere", pair_id=pair_id, toi_lower=0.0, toi_upper=0.0, witness=w, method="quadratic", termination_reason="initial separation not positive", tolerance=geom_tol)
    a = v.dot(v)
    if a <= 1e-30:
        return Certificate(Status.MISS, "sphere-sphere", pair_id=pair_id, method="quadratic", termination_reason="zero relative velocity with positive separation", tolerance=geom_tol)
    b = 2.0 * s.dot(v)
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return Certificate(Status.MISS, "sphere-sphere", pair_id=pair_id, method="quadratic", termination_reason="negative discriminant", tolerance=geom_tol)
    sqrt_disc = math.sqrt(max(0.0, disc))
    t = (-b - sqrt_disc) / (2.0 * a)
    if not (0.0 <= t <= 1.0):
        return Certificate(Status.MISS, "sphere-sphere", pair_id=pair_id, method="quadratic", termination_reason="first root outside normalized step", tolerance=geom_tol)
    pa, pb = center_a.at(t), center_b.at(t)
    n = (pa - pb).normalized()
    w = Witness(pa - n * radius_a, pb + n * radius_b, n, distance=max(0.0, (pa - pb).norm() - r))
    return Certificate(Status.HIT, "sphere-sphere", pair_id=pair_id, toi_lower=t, toi_upper=t, witness=w, method="quadratic", termination_reason="first admissible quadratic root", tolerance=geom_tol)
