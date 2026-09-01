from __future__ import annotations

from dataclasses import dataclass
import math

from .shapes import AxisAlignedBox, Body, Plane, PointShape, Sphere
from .vector import Vec3


@dataclass(frozen=True, slots=True)
class AABB:
    minimum: Vec3
    maximum: Vec3

    def overlaps(self, other: "AABB") -> bool:
        return all(
            self.minimum.component(axis) <= other.maximum.component(axis)
            and other.minimum.component(axis) <= self.maximum.component(axis)
            for axis in range(3)
        )


def swept_aabb(body: Body, t0: float = 0.0, t1: float = 1.0) -> AABB | None:
    if isinstance(body.shape, Plane):
        return None
    if isinstance(body.shape, Sphere):
        ext = Vec3(body.shape.radius, body.shape.radius, body.shape.radius)
    elif isinstance(body.shape, AxisAlignedBox):
        ext = body.shape.half_extents
    elif isinstance(body.shape, PointShape):
        ext = Vec3(0.0, 0.0, 0.0)
    else:
        # Generic implicit fields need an explicit finite support bound before
        # they can participate in the broad phase.
        return None
    mins: list[float] = []
    maxs: list[float] = []
    for axis in range(3):
        lo, hi = body.motion.coordinate_bounds(axis, t0, t1)
        e = ext.component(axis)
        mins.append(lo - e)
        maxs.append(hi + e)
    return AABB(Vec3.from_iterable(mins), Vec3.from_iterable(maxs))


def broadphase_sweep_and_prune(bodies: list[Body], max_candidates: int) -> tuple[list[tuple[int, int]], bool]:
    bounded: list[tuple[int, AABB]] = []
    unbounded: list[int] = []
    for i, body in enumerate(bodies):
        bounds = swept_aabb(body)
        if bounds is None:
            unbounded.append(i)
        else:
            bounded.append((i, bounds))
    bounded.sort(key=lambda item: (item[1].minimum.x, bodies[item[0]].body_id))
    active: list[tuple[int, AABB]] = []
    candidates: list[tuple[int, int]] = []
    overflow = False
    for idx, box in bounded:
        active = [(j, b) for j, b in active if b.maximum.x >= box.minimum.x]
        for j, other in active:
            if box.overlaps(other):
                candidates.append((min(idx, j), max(idx, j)))
                if len(candidates) >= max_candidates:
                    overflow = True
                    return sorted(set(candidates)), overflow
        active.append((idx, box))
    # Planes and other explicitly unbounded objects are conservatively paired
    # with every other body. Unsupported narrow phases remain explicit.
    for i in unbounded:
        for j in range(len(bodies)):
            if i == j:
                continue
            candidates.append((min(i, j), max(i, j)))
            if len(candidates) >= max_candidates:
                overflow = True
                return sorted(set(candidates)), overflow
    return sorted(set(candidates)), overflow
