from __future__ import annotations

from dataclasses import dataclass
import math
from .model import Vec3


@dataclass(frozen=True)
class RigidMotionBound:
    linear_velocity: Vec3
    angular_speed: float
    support_radius: float

    def point_speed_bound(self) -> float:
        if self.angular_speed < 0.0 or self.support_radius < 0.0:
            raise ValueError("angular speed and support radius must be nonnegative")
        return self.linear_velocity.norm() + self.angular_speed * self.support_radius


def relative_speed_bound(a: RigidMotionBound, b: RigidMotionBound) -> float:
    if a.angular_speed < 0.0 or b.angular_speed < 0.0 or a.support_radius < 0.0 or b.support_radius < 0.0:
        raise ValueError("invalid rigid-motion bound")
    return (a.linear_velocity - b.linear_velocity).norm() + a.angular_speed * a.support_radius + b.angular_speed * b.support_radius


def rotational_margin(angular_speed: float, support_radius: float, dt: float) -> float:
    """Safe chord/arc envelope: min(2r, r|omega|dt)."""
    if angular_speed < 0.0 or support_radius < 0.0 or dt < 0.0:
        raise ValueError("inputs must be nonnegative")
    return min(2.0 * support_radius, support_radius * angular_speed * dt)


def conservative_advance_step(separation_lower_bound: float, speed_upper_bound: float, safety: float = 0.9, minimum: float = 0.0) -> float:
    if separation_lower_bound <= 0.0:
        return 0.0
    if speed_upper_bound <= 0.0:
        return math.inf
    if not (0.0 < safety <= 1.0):
        raise ValueError("safety must lie in (0,1]")
    return max(minimum, safety * separation_lower_bound / speed_upper_bound)
