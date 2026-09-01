from __future__ import annotations

from dataclasses import dataclass
import math
from .model import Vec3


@dataclass(frozen=True)
class PointTriangleResult:
    distance2: float
    point: Vec3
    barycentric: tuple[float, float, float]
    degenerate: bool = False


@dataclass(frozen=True)
class SegmentSegmentResult:
    distance2: float
    point_a: Vec3
    point_b: Vec3
    s: float
    t: float
    degenerate: bool = False


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def closest_point_segment(p: Vec3, a: Vec3, b: Vec3) -> tuple[Vec3, float]:
    ab = b - a
    d = ab.norm2()
    if d <= 1e-30:
        return a, 0.0
    t = clamp((p - a).dot(ab) / d, 0.0, 1.0)
    return a + ab * t, t


def point_triangle_distance2(p: Vec3, a: Vec3, b: Vec3, c: Vec3) -> PointTriangleResult:
    """Closest point using Voronoi regions; degeneracy falls back to edges."""
    ab = b - a
    ac = c - a
    n2 = ab.cross(ac).norm2()
    scale2 = max(ab.norm2(), ac.norm2(), (c - b).norm2(), 1.0)
    if n2 <= 1e-28 * scale2 * scale2:
        candidates: list[tuple[float, Vec3, tuple[float, float, float]]] = []
        q, t = closest_point_segment(p, a, b)
        candidates.append(((p - q).norm2(), q, (1.0 - t, t, 0.0)))
        q, t = closest_point_segment(p, b, c)
        candidates.append(((p - q).norm2(), q, (0.0, 1.0 - t, t)))
        q, t = closest_point_segment(p, c, a)
        candidates.append(((p - q).norm2(), q, (t, 0.0, 1.0 - t)))
        d2, q, bary = min(candidates, key=lambda x: x[0])
        return PointTriangleResult(max(0.0, d2), q, bary, True)

    ap = p - a
    d1 = ab.dot(ap)
    d2 = ac.dot(ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return PointTriangleResult(ap.norm2(), a, (1.0, 0.0, 0.0))

    bp = p - b
    d3 = ab.dot(bp)
    d4 = ac.dot(bp)
    if d3 >= 0.0 and d4 <= d3:
        return PointTriangleResult(bp.norm2(), b, (0.0, 1.0, 0.0))

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        q = a + ab * v
        return PointTriangleResult((p - q).norm2(), q, (1.0 - v, v, 0.0))

    cp = p - c
    d5 = ab.dot(cp)
    d6 = ac.dot(cp)
    if d6 >= 0.0 and d5 <= d6:
        return PointTriangleResult(cp.norm2(), c, (0.0, 0.0, 1.0))

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        q = a + ac * w
        return PointTriangleResult((p - q).norm2(), q, (1.0 - w, 0.0, w))

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        bc = c - b
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        q = b + bc * w
        return PointTriangleResult((p - q).norm2(), q, (0.0, 1.0 - w, w))

    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    u = 1.0 - v - w
    q = a * u + b * v + c * w
    return PointTriangleResult(max(0.0, (p - q).norm2()), q, (u, v, w))


def segment_segment_distance2(p1: Vec3, q1: Vec3, p2: Vec3, q2: Vec3) -> SegmentSegmentResult:
    """Robust closest points for two closed 3D segments."""
    d1 = q1 - p1
    d2 = q2 - p2
    r = p1 - p2
    a = d1.dot(d1)
    e = d2.dot(d2)
    f = d2.dot(r)
    eps = 1e-30
    deg = False

    if a <= eps and e <= eps:
        return SegmentSegmentResult(r.norm2(), p1, p2, 0.0, 0.0, True)
    if a <= eps:
        deg = True
        s = 0.0
        t = clamp(f / e, 0.0, 1.0)
    else:
        c = d1.dot(r)
        if e <= eps:
            deg = True
            t = 0.0
            s = clamp(-c / a, 0.0, 1.0)
        else:
            b = d1.dot(d2)
            denom = a * e - b * b
            if abs(denom) > eps * max(a * e, 1.0):
                s = clamp((b * f - c * e) / denom, 0.0, 1.0)
            else:
                deg = True
                s = 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0
                s = clamp(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t = 1.0
                s = clamp((b - c) / a, 0.0, 1.0)

    c1 = p1 + d1 * s
    c2 = p2 + d2 * t
    return SegmentSegmentResult(max(0.0, (c1 - c2).norm2()), c1, c2, s, t, deg)


def triangle_normal(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    return (b - a).cross(c - a).normalized()
