from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from .shapes import Body, ImplicitSDF, Plane, PointShape, Sphere
from .types import SeparationSample
from .vector import Vec3


class SeparationOracle(Protocol):
    body_a: Body
    body_b: Body

    def evaluate(self, t: float) -> SeparationSample: ...
    def closure_speed_bound(self, t0: float, t1: float) -> float: ...


def _finite_difference_normal(sdf: ImplicitSDF, p: Vec3, h: float = 1e-5) -> Vec3:
    ex = Vec3(h, 0.0, 0.0)
    ey = Vec3(0.0, h, 0.0)
    ez = Vec3(0.0, 0.0, h)
    g = Vec3(
        sdf.evaluate(p + ex) - sdf.evaluate(p - ex),
        sdf.evaluate(p + ey) - sdf.evaluate(p - ey),
        sdf.evaluate(p + ez) - sdf.evaluate(p - ez),
    )
    return g.normalized()


@dataclass(slots=True)
class SphereSphereOracle:
    body_a: Body
    body_b: Body

    def evaluate(self, t: float) -> SeparationSample:
        assert isinstance(self.body_a.shape, Sphere)
        assert isinstance(self.body_b.shape, Sphere)
        ca = self.body_a.motion.position(t)
        cb = self.body_b.motion.position(t)
        delta = cb - ca
        center_distance = delta.norm()
        normal = delta.normalized()
        distance = center_distance - self.body_a.shape.radius - self.body_b.shape.radius
        wa = ca + normal * self.body_a.shape.radius
        wb = cb - normal * self.body_b.shape.radius
        return SeparationSample(t, distance, normal, wa, wb)

    def closure_speed_bound(self, t0: float, t1: float) -> float:
        return self.body_a.motion.speed_bound(t0, t1) + self.body_b.motion.speed_bound(t0, t1)


@dataclass(slots=True)
class SpherePlaneOracle:
    body_a: Body
    body_b: Body

    def evaluate(self, t: float) -> SeparationSample:
        assert isinstance(self.body_a.shape, Sphere)
        assert isinstance(self.body_b.shape, Plane)
        sphere = self.body_a.shape
        plane = self.body_b.shape
        center = self.body_a.motion.position(t)
        plane_translation = self.body_b.motion.position(t)
        world_offset = plane.offset + plane.normal.dot(plane_translation)
        signed_center = plane.normal.dot(center) - world_offset
        distance = signed_center - sphere.radius
        wa = center - plane.normal * sphere.radius
        wb = wa - plane.normal * distance
        return SeparationSample(t, distance, plane.normal, wa, wb)

    def closure_speed_bound(self, t0: float, t1: float) -> float:
        return self.body_a.motion.speed_bound(t0, t1) + self.body_b.motion.speed_bound(t0, t1)


@dataclass(slots=True)
class PointSDFOracle:
    body_a: Body
    body_b: Body
    point_radius: float = 0.0

    def evaluate(self, t: float) -> SeparationSample:
        assert isinstance(self.body_b.shape, ImplicitSDF)
        sdf = self.body_b.shape
        point_world = self.body_a.motion.position(t)
        sdf_origin = self.body_b.motion.position(t)
        local = point_world - sdf_origin
        raw = float(sdf.evaluate(local))
        # Subtracting a known conservative bias prevents an over-estimated field
        # from certifying unsafe time advances.
        distance = raw - sdf.conservative_bias - self.point_radius
        normal = (sdf.gradient(local) if sdf.gradient is not None else _finite_difference_normal(sdf, local)).normalized()
        wa = point_world - normal * self.point_radius
        wb = point_world - normal * (raw - sdf.conservative_bias)
        return SeparationSample(t, distance, normal, wa, wb)

    def closure_speed_bound(self, t0: float, t1: float) -> float:
        sdf = self.body_b.shape
        assert isinstance(sdf, ImplicitSDF)
        relative_speed = self.body_a.motion.speed_bound(t0, t1) + self.body_b.motion.speed_bound(t0, t1)
        return sdf.lipschitz * relative_speed


@dataclass(slots=True)
class ReversedOracle:
    inner: SeparationOracle

    @property
    def body_a(self) -> Body:
        return self.inner.body_b

    @property
    def body_b(self) -> Body:
        return self.inner.body_a

    def evaluate(self, t: float) -> SeparationSample:
        s = self.inner.evaluate(t)
        return SeparationSample(t, s.distance, -s.normal, s.witness_b, s.witness_a)

    def closure_speed_bound(self, t0: float, t1: float) -> float:
        return self.inner.closure_speed_bound(t0, t1)


def make_oracle(body_a: Body, body_b: Body) -> SeparationOracle | None:
    if isinstance(body_a.shape, Sphere) and isinstance(body_b.shape, Sphere):
        return SphereSphereOracle(body_a, body_b)
    if isinstance(body_a.shape, Sphere) and isinstance(body_b.shape, Plane):
        return SpherePlaneOracle(body_a, body_b)
    if isinstance(body_a.shape, Plane) and isinstance(body_b.shape, Sphere):
        return ReversedOracle(SpherePlaneOracle(body_b, body_a))
    if isinstance(body_a.shape, PointShape) and isinstance(body_b.shape, ImplicitSDF):
        return PointSDFOracle(body_a, body_b, 0.0)
    if isinstance(body_a.shape, Sphere) and isinstance(body_b.shape, ImplicitSDF):
        return PointSDFOracle(body_a, body_b, body_a.shape.radius)
    if isinstance(body_a.shape, ImplicitSDF) and isinstance(body_b.shape, PointShape):
        return ReversedOracle(PointSDFOracle(body_b, body_a, 0.0))
    if isinstance(body_a.shape, ImplicitSDF) and isinstance(body_b.shape, Sphere):
        return ReversedOracle(PointSDFOracle(body_b, body_a, body_b.shape.radius))
    return None
