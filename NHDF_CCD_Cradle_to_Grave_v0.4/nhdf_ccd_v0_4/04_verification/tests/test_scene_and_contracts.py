from __future__ import annotations

from nhdf_ccd import AxisAlignedBox, Body, CCDConfig, CCDStatus, LinearMotion, Sphere, StaticMotion, Vec3, detect_pair, detect_scene
from nhdf_ccd.broadphase import broadphase_sweep_and_prune


def test_broadphase_prunes_distant_pair() -> None:
    bodies = [
        Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0))),
        Body("b", Sphere(1.0), StaticMotion(Vec3(100.0, 0.0, 0.0))),
        Body("c", Sphere(1.0), LinearMotion(Vec3(-10.0, 0.0, 0.0), Vec3(20.0, 0.0, 0.0))),
    ]
    pairs, overflow = broadphase_sweep_and_prune(bodies, 100)
    assert not overflow
    ids = {(bodies[i].body_id, bodies[j].body_id) for i, j in pairs}
    assert ("a", "c") in ids
    assert ("a", "b") not in ids


def test_scene_reports_hit() -> None:
    bodies = [
        Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0))),
        Body("b", Sphere(1.0), LinearMotion(Vec3(-10.0, 0.0, 0.0), Vec3(20.0, 0.0, 0.0))),
        Body("far", Sphere(1.0), StaticMotion(Vec3(100.0, 0.0, 0.0))),
    ]
    result = detect_scene(bodies)
    assert result.status == CCDStatus.HIT
    assert result.telemetry["candidate_count"] == 1


def test_candidate_capacity_failure_is_explicit() -> None:
    bodies = [Body(str(i), Sphere(10.0), StaticMotion(Vec3(float(i), 0.0, 0.0))) for i in range(8)]
    result = detect_scene(bodies, CCDConfig(max_candidates=3))
    assert result.status == CCDStatus.CAPACITY_EXCEEDED


def test_unsupported_pair_is_explicit() -> None:
    sphere = Body("sphere", Sphere(1.0), StaticMotion())
    box = Body("box", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), StaticMotion(Vec3(10.0, 0.0, 0.0)))
    cert = detect_pair(sphere, box)
    assert cert.status == CCDStatus.UNSUPPORTED


def test_trace_digest_is_deterministic() -> None:
    a = Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0)))
    b = Body("b", Sphere(1.0), LinearMotion(Vec3(10.0, 0.0, 0.0), Vec3(-20.0, 0.0, 0.0)))
    assert detect_pair(a, b).trace_digest == detect_pair(a, b).trace_digest


def test_invalid_config_is_not_silently_corrected() -> None:
    a = Body("a", Sphere(1.0), StaticMotion())
    b = Body("b", Sphere(1.0), StaticMotion(Vec3(10.0, 0.0, 0.0)))
    cert = detect_pair(a, b, CCDConfig(safety_factor=1.2))
    assert cert.status == CCDStatus.INVALID_INPUT
