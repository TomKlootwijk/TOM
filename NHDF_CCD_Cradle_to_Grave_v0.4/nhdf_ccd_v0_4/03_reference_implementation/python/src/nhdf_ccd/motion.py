from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from .vector import Vec3, ZERO


class Motion(Protocol):
    def position(self, t: float) -> Vec3: ...
    def velocity(self, t: float) -> Vec3: ...
    def speed_bound(self, t0: float, t1: float) -> float: ...
    def coordinate_bounds(self, axis: int, t0: float, t1: float) -> tuple[float, float]: ...


@dataclass(frozen=True, slots=True)
class StaticMotion:
    origin: Vec3 = ZERO

    def position(self, t: float) -> Vec3:
        return self.origin

    def velocity(self, t: float) -> Vec3:
        return ZERO

    def speed_bound(self, t0: float, t1: float) -> float:
        return 0.0

    def coordinate_bounds(self, axis: int, t0: float, t1: float) -> tuple[float, float]:
        value = self.origin.component(axis)
        return value, value


@dataclass(frozen=True, slots=True)
class LinearMotion:
    origin: Vec3
    velocity_vector: Vec3

    def position(self, t: float) -> Vec3:
        return self.origin + self.velocity_vector * t

    def velocity(self, t: float) -> Vec3:
        return self.velocity_vector

    def speed_bound(self, t0: float, t1: float) -> float:
        return self.velocity_vector.norm()

    def coordinate_bounds(self, axis: int, t0: float, t1: float) -> tuple[float, float]:
        a = self.position(t0).component(axis)
        b = self.position(t1).component(axis)
        return min(a, b), max(a, b)


@dataclass(frozen=True, slots=True)
class QuadraticMotion:
    origin: Vec3
    velocity_vector: Vec3
    acceleration_vector: Vec3

    def position(self, t: float) -> Vec3:
        return self.origin + self.velocity_vector * t + self.acceleration_vector * (0.5 * t * t)

    def velocity(self, t: float) -> Vec3:
        return self.velocity_vector + self.acceleration_vector * t

    def speed_bound(self, t0: float, t1: float) -> float:
        # Triangle inequality gives a conservative bound over the interval.
        max_abs_t = max(abs(t0), abs(t1))
        return self.velocity_vector.norm() + self.acceleration_vector.norm() * max_abs_t

    def coordinate_bounds(self, axis: int, t0: float, t1: float) -> tuple[float, float]:
        values = [self.position(t0).component(axis), self.position(t1).component(axis)]
        v = self.velocity_vector.component(axis)
        a = self.acceleration_vector.component(axis)
        if abs(a) > 1e-15:
            extremum = -v / a
            if t0 <= extremum <= t1:
                values.append(self.position(extremum).component(axis))
        return min(values), max(values)
