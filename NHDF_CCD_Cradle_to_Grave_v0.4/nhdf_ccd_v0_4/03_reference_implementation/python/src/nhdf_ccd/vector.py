from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Vec3:
    x: float
    y: float
    z: float

    @classmethod
    def from_iterable(cls, values: Iterable[float]) -> "Vec3":
        x, y, z = values
        return cls(float(x), float(y), float(z))

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> "Vec3":
        if scalar == 0.0:
            raise ZeroDivisionError("Vec3 division by zero")
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def norm_sq(self) -> float:
        return self.dot(self)

    def norm(self) -> float:
        return math.sqrt(self.norm_sq())

    def normalized(self, eps: float = 1e-15) -> "Vec3":
        n = self.norm()
        if n <= eps:
            return Vec3(1.0, 0.0, 0.0)
        return self / n

    def component(self, axis: int) -> float:
        if axis == 0:
            return self.x
        if axis == 1:
            return self.y
        if axis == 2:
            return self.z
        raise IndexError(axis)

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def is_finite(self) -> bool:
        return math.isfinite(self.x) and math.isfinite(self.y) and math.isfinite(self.z)


ZERO = Vec3(0.0, 0.0, 0.0)


def vec_min(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))


def vec_max(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))
