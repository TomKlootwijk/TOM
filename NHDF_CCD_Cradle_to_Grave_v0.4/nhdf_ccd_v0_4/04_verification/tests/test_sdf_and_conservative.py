from __future__ import annotations

import math

from nhdf_ccd import Body, CCDConfig, CCDStatus, ImplicitSDF, LinearMotion, PointShape, QuadraticMotion, Sphere, StaticMotion, Vec3, detect_pair


def test_point_against_true_sdf_detects_tunneling(unit_sphere_sdf: ImplicitSDF) -> None:
    point = Body("point", PointShape(), LinearMotion(Vec3(-5.0, 0.0, 0.0), Vec3(10.0, 0.0, 0.0)))
    field = Body("field", unit_sphere_sdf, StaticMotion())
    cert = detect_pair(point, field, CCDConfig(distance_tolerance=1e-7, max_iterations=256))
    assert cert.status == CCDStatus.HIT
    assert cert.toi_lower is not None and cert.toi_upper is not None
    assert cert.toi_lower <= 0.4 <= cert.toi_upper + 1e-6


def test_sphere_against_sdf_accounts_for_radius(unit_sphere_sdf: ImplicitSDF) -> None:
    sphere = Body("sphere", Sphere(0.5), LinearMotion(Vec3(-5.0, 0.0, 0.0), Vec3(10.0, 0.0, 0.0)))
    field = Body("field", unit_sphere_sdf, StaticMotion())
    cert = detect_pair(sphere, field, CCDConfig(distance_tolerance=1e-7, max_iterations=256))
    assert cert.status == CCDStatus.HIT
    assert cert.toi_upper is not None
    assert abs(cert.toi_upper - 0.35) < 2e-6


def test_quadratic_motion_uses_conservative_advancement() -> None:
    a = Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body(
        "b",
        Sphere(1.0),
        QuadraticMotion(Vec3(10.0, 0.0, 0.0), Vec3(-4.0, 0.0, 0.0), Vec3(-20.0, 0.0, 0.0)),
    )
    cert = detect_pair(a, b, CCDConfig(distance_tolerance=1e-7, max_iterations=512))
    assert cert.status == CCDStatus.HIT
    expected = (-4.0 + math.sqrt(16.0 + 320.0)) / 20.0
    assert cert.toi_upper is not None
    assert abs(cert.toi_upper - expected) < 3e-5


def test_static_point_outside_sdf_has_no_hit(unit_sphere_sdf: ImplicitSDF) -> None:
    point = Body("point", PointShape(), StaticMotion(Vec3(5.0, 0.0, 0.0)))
    field = Body("field", unit_sphere_sdf, StaticMotion())
    cert = detect_pair(point, field)
    assert cert.status == CCDStatus.NO_HIT
    assert "zero closure-speed" in cert.reason


def test_invalid_lipschitz_rejected() -> None:
    try:
        ImplicitSDF(lambda p: 1.0, lipschitz=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid Lipschitz bound must be rejected")


def test_nhdf_hint_does_not_change_outcome(unit_sphere_sdf: ImplicitSDF) -> None:
    point = Body("point", PointShape(), LinearMotion(Vec3(-5.0, 0.0, 0.0), Vec3(10.0, 0.0, 0.0)))
    field = Body("field", unit_sphere_sdf, StaticMotion())
    with_hint = detect_pair(point, field, CCDConfig(use_nhdf_hints=True, max_iterations=256))
    without_hint = detect_pair(point, field, CCDConfig(use_nhdf_hints=False, max_iterations=256))
    assert with_hint.status == without_hint.status
    assert abs((with_hint.toi_upper or 0.0) - (without_hint.toi_upper or 0.0)) < 1e-12
