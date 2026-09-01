from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any, Iterable


@dataclass(frozen=True, order=True)
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

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

    def norm2(self) -> float:
        return self.dot(self)

    def norm(self) -> float:
        return math.sqrt(max(0.0, self.norm2()))

    def normalized(self, eps: float = 1e-30) -> "Vec3":
        n = self.norm()
        if n <= eps:
            return Vec3(0.0, 0.0, 0.0)
        return self / n

    def finite(self) -> bool:
        return math.isfinite(self.x) and math.isfinite(self.y) and math.isfinite(self.z)

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass(frozen=True)
class LinearPoint:
    p0: Vec3
    p1: Vec3

    def at(self, t: float) -> Vec3:
        return self.p0 * (1.0 - t) + self.p1 * t

    @property
    def velocity(self) -> Vec3:
        return self.p1 - self.p0

    @property
    def speed(self) -> float:
        return self.velocity.norm()


class Status(str, Enum):
    HIT = "HIT"
    MISS = "MISS"
    INITIAL_OVERLAP = "INITIAL_OVERLAP"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNSUPPORTED = "UNSUPPORTED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"


@dataclass(frozen=True)
class Witness:
    point_a: Vec3 | None = None
    point_b: Vec3 | None = None
    normal: Vec3 | None = None
    barycentric: tuple[float, float, float] | None = None
    edge_parameters: tuple[float, float] | None = None
    distance: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_a": None if self.point_a is None else self.point_a.to_list(),
            "point_b": None if self.point_b is None else self.point_b.to_list(),
            "normal": None if self.normal is None else self.normal.to_list(),
            "barycentric": self.barycentric,
            "edge_parameters": self.edge_parameters,
            "distance": self.distance,
        }


@dataclass
class Certificate:
    status: Status
    query_type: str
    pair_id: str = ""
    feature_ids: tuple[str, ...] = ()
    toi_lower: float | None = None
    toi_upper: float | None = None
    witness: Witness | None = None
    iterations: int = 0
    candidate_roots: int = 0
    method: str = ""
    termination_reason: str = ""
    tolerance: float = 0.0
    condition_indicator: float | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_contact(self) -> bool:
        return self.status in {Status.HIT, Status.INITIAL_OVERLAP}

    @property
    def conclusive(self) -> bool:
        return self.status in {Status.HIT, Status.MISS, Status.INITIAL_OVERLAP}

    def validate(self) -> None:
        if self.toi_lower is not None and not (0.0 <= self.toi_lower <= 1.0):
            raise ValueError("toi_lower outside normalized step")
        if self.toi_upper is not None and not (0.0 <= self.toi_upper <= 1.0):
            raise ValueError("toi_upper outside normalized step")
        if self.toi_lower is not None and self.toi_upper is not None and self.toi_lower > self.toi_upper:
            raise ValueError("invalid TOI interval")
        if self.is_contact and self.toi_upper is None:
            raise ValueError("contact certificate requires an upper TOI")

    def to_dict(self, include_trace: bool = True) -> dict[str, Any]:
        self.validate()
        out: dict[str, Any] = {
            "status": self.status.value,
            "query_type": self.query_type,
            "pair_id": self.pair_id,
            "feature_ids": list(self.feature_ids),
            "toi_lower": self.toi_lower,
            "toi_upper": self.toi_upper,
            "witness": None if self.witness is None else self.witness.to_dict(),
            "iterations": self.iterations,
            "candidate_roots": self.candidate_roots,
            "method": self.method,
            "termination_reason": self.termination_reason,
            "tolerance": self.tolerance,
            "condition_indicator": self.condition_indicator,
            "metadata": self.metadata,
        }
        if include_trace:
            out["trace"] = self.trace
        return out

    def canonical_json(self, include_trace: bool = True) -> str:
        return json.dumps(self.to_dict(include_trace=include_trace), sort_keys=True, separators=(",", ":"), allow_nan=False)

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def all_finite(points: Iterable[Vec3]) -> bool:
    return all(p.finite() for p in points)
