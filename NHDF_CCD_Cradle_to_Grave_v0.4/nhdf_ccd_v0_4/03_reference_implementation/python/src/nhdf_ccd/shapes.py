from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .motion import Motion
from .vector import Vec3


@dataclass(frozen=True, slots=True)
class Sphere:
    radius: float

    def __post_init__(self) -> None:
        if self.radius < 0.0:
            raise ValueError("sphere radius must be non-negative")


@dataclass(frozen=True, slots=True)
class AxisAlignedBox:
    half_extents: Vec3

    def __post_init__(self) -> None:
        if min(self.half_extents.to_tuple()) < 0.0:
            raise ValueError("AABB half extents must be non-negative")


@dataclass(frozen=True, slots=True)
class Plane:
    normal: Vec3
    offset: float = 0.0

    def __post_init__(self) -> None:
        if self.normal.norm() <= 1e-15:
            raise ValueError("plane normal must be non-zero")
        object.__setattr__(self, "normal", self.normal.normalized())


@dataclass(frozen=True, slots=True)
class PointShape:
    pass


@dataclass(frozen=True, slots=True)
class ImplicitSDF:
    evaluate: Callable[[Vec3], float]
    gradient: Callable[[Vec3], Vec3] | None = None
    lipschitz: float = 1.0
    conservative_bias: float = 0.0
    name: str = "implicit_sdf"

    def __post_init__(self) -> None:
        if self.lipschitz <= 0.0:
            raise ValueError("SDF Lipschitz bound must be positive")
        if self.conservative_bias < 0.0:
            raise ValueError("conservative_bias must be non-negative")


Shape = Sphere | AxisAlignedBox | Plane | PointShape | ImplicitSDF


@dataclass(frozen=True, slots=True)
class Body:
    body_id: str
    shape: Shape
    motion: Motion
