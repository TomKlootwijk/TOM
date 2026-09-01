from __future__ import annotations

from nhdf_ccd import Body, CCDConfig, CCDStatus, ImplicitSDF, LinearMotion, PointShape, StaticMotion, Vec3
from nhdf_ccd.interval import bounded_interval_refinement
from nhdf_ccd.oracles import make_oracle


def _oracle() -> object:
    sdf = ImplicitSDF(lambda p: p.norm() - 1.0, gradient=lambda p: p.normalized(), lipschitz=1.0)
    point = Body("point", PointShape(), LinearMotion(Vec3(-5.0, 0.0, 0.0), Vec3(10.0, 0.0, 0.0)))
    field = Body("field", sdf, StaticMotion())
    oracle = make_oracle(point, field)
    assert oracle is not None
    return oracle


def test_midpoint_refinement_finds_hit() -> None:
    cert = bounded_interval_refinement(_oracle(), CCDConfig(split_policy="midpoint", distance_tolerance=1e-6, time_tolerance=1e-6, interval_max_nodes=10000))
    assert cert.status == CCDStatus.HIT


def test_golden_refinement_finds_same_hit_class() -> None:
    cert = bounded_interval_refinement(_oracle(), CCDConfig(split_policy="golden", distance_tolerance=1e-6, time_tolerance=1e-6, interval_max_nodes=10000))
    assert cert.status == CCDStatus.HIT
