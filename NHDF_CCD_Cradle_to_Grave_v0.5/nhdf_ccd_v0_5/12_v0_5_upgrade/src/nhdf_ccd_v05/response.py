from __future__ import annotations

from dataclasses import dataclass, replace
from .model import Vec3


@dataclass(frozen=True)
class BodyState:
    body_id: str
    mass: float
    position: Vec3
    velocity: Vec3

    @property
    def inverse_mass(self) -> float:
        if self.mass < 0.0:
            raise ValueError("mass must be nonnegative")
        return 0.0 if self.mass == 0.0 else 1.0 / self.mass

    def advanced(self, dt: float) -> "BodyState":
        return replace(self, position=self.position + self.velocity * dt)


@dataclass(frozen=True)
class ImpulseResult:
    body_a: BodyState
    body_b: BodyState
    impulse_magnitude: float
    pre_normal_relative_speed: float
    post_normal_relative_speed: float
    applied: bool


def apply_frictionless_impulse(a: BodyState, b: BodyState, normal_b_to_a: Vec3, restitution: float = 0.0) -> ImpulseResult:
    if not (0.0 <= restitution <= 1.0):
        raise ValueError("restitution must lie in [0,1]")
    n = normal_b_to_a.normalized()
    if n.norm2() == 0.0:
        return ImpulseResult(a, b, 0.0, 0.0, 0.0, False)
    rel = a.velocity - b.velocity
    vn = rel.dot(n)
    inv_sum = a.inverse_mass + b.inverse_mass
    if vn >= 0.0 or inv_sum <= 0.0:
        return ImpulseResult(a, b, 0.0, vn, vn, False)
    j = -(1.0 + restitution) * vn / inv_sum
    va = a.velocity + n * (j * a.inverse_mass)
    vb = b.velocity - n * (j * b.inverse_mass)
    a2 = replace(a, velocity=va)
    b2 = replace(b, velocity=vb)
    post = (a2.velocity - b2.velocity).dot(n)
    return ImpulseResult(a2, b2, j, vn, post, True)


def advance_split_step(a: BodyState, b: BodyState, toi: float, dt: float, normal_b_to_a: Vec3, restitution: float = 0.0) -> ImpulseResult:
    if not (0.0 <= toi <= 1.0) or dt < 0.0:
        raise ValueError("invalid normalized TOI or dt")
    a_hit = a.advanced(dt * toi)
    b_hit = b.advanced(dt * toi)
    impulse = apply_frictionless_impulse(a_hit, b_hit, normal_b_to_a, restitution)
    remain = dt * (1.0 - toi)
    return ImpulseResult(
        impulse.body_a.advanced(remain),
        impulse.body_b.advanced(remain),
        impulse.impulse_magnitude,
        impulse.pre_normal_relative_speed,
        impulse.post_normal_relative_speed,
        impulse.applied,
    )
