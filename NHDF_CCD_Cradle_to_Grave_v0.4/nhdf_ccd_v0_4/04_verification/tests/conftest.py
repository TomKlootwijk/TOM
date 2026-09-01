from __future__ import annotations

import math

import pytest

from nhdf_ccd import Body, ImplicitSDF, LinearMotion, Plane, PointShape, Sphere, StaticMotion, Vec3


@pytest.fixture
def unit_sphere_sdf() -> ImplicitSDF:
    return ImplicitSDF(
        evaluate=lambda p: p.norm() - 1.0,
        gradient=lambda p: p.normalized(),
        lipschitz=1.0,
        name="unit_sphere",
    )
