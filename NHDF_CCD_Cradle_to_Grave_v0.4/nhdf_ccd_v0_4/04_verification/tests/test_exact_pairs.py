from __future__ import annotations

import math

from nhdf_ccd import AxisAlignedBox, Body, CCDStatus, LinearMotion, Plane, Sphere, StaticMotion, Vec3, detect_pair


def test_sphere_sphere_linear_hit_exact_toi() -> None:
    a = Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("b", Sphere(1.0), LinearMotion(Vec3(10.0, 0.0, 0.0), Vec3(-20.0, 0.0, 0.0)))
    cert = detect_pair(a, b)
    assert cert.status == CCDStatus.HIT
    assert cert.toi_lower == cert.toi_upper
    assert math.isclose(cert.toi_lower or -1.0, 0.4, rel_tol=0.0, abs_tol=1e-12)


def test_sphere_sphere_endpoints_miss_but_ccd_hits() -> None:
    a = Body("stationary", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("bullet", Sphere(1.0), LinearMotion(Vec3(-10.0, 0.0, 0.0), Vec3(20.0, 0.0, 0.0)))
    d0 = (b.motion.position(0.0) - a.motion.position(0.0)).norm() - 2.0
    d1 = (b.motion.position(1.0) - a.motion.position(1.0)).norm() - 2.0
    assert d0 > 0.0 and d1 > 0.0
    cert = detect_pair(a, b)
    assert cert.status == CCDStatus.HIT
    assert math.isclose(cert.toi_lower or -1.0, 0.4, abs_tol=1e-12)


def test_sphere_sphere_no_hit() -> None:
    a = Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("b", Sphere(1.0), LinearMotion(Vec3(10.0, 0.0, 0.0), Vec3(0.0, 5.0, 0.0)))
    assert detect_pair(a, b).status == CCDStatus.NO_HIT


def test_sphere_sphere_initial_overlap() -> None:
    a = Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("b", Sphere(1.0), StaticMotion(Vec3(1.0, 0.0, 0.0)))
    assert detect_pair(a, b).status == CCDStatus.INITIAL_OVERLAP


def test_sphere_plane_high_speed() -> None:
    sphere = Body("sphere", Sphere(1.0), LinearMotion(Vec3(0.0, 10.0, 0.0), Vec3(0.0, -100.0, 0.0)))
    plane = Body("plane", Plane(Vec3(0.0, 1.0, 0.0)), StaticMotion())
    cert = detect_pair(sphere, plane)
    assert cert.status == CCDStatus.HIT
    assert math.isclose(cert.toi_lower or -1.0, 0.09, abs_tol=1e-12)


def test_sphere_plane_moving_away() -> None:
    sphere = Body("sphere", Sphere(1.0), LinearMotion(Vec3(0.0, 10.0, 0.0), Vec3(0.0, 1.0, 0.0)))
    plane = Body("plane", Plane(Vec3(0.0, 1.0, 0.0)), StaticMotion())
    assert detect_pair(sphere, plane).status == CCDStatus.NO_HIT


def test_swept_aabb_hit() -> None:
    a = Body("a", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("b", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), LinearMotion(Vec3(-5.0, 0.0, 0.0), Vec3(10.0, 0.0, 0.0)))
    cert = detect_pair(a, b)
    assert cert.status == CCDStatus.HIT
    assert math.isclose(cert.toi_lower or -1.0, 0.3, abs_tol=1e-12)


def test_swept_aabb_no_hit_separate_axis() -> None:
    a = Body("a", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("b", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), LinearMotion(Vec3(-5.0, 10.0, 0.0), Vec3(10.0, 0.0, 0.0)))
    assert detect_pair(a, b).status == CCDStatus.NO_HIT
