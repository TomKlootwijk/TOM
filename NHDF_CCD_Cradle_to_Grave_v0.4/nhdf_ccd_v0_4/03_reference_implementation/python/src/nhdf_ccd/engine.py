from __future__ import annotations

from .broadphase import broadphase_sweep_and_prune
from .conservative import conservative_advancement
from .exact import exact_aabb_aabb, exact_sphere_plane, exact_sphere_sphere
from .oracles import make_oracle
from .shapes import Body
from .types import CCDConfig, CCDStatus, CollisionCertificate, SceneResult


def detect_pair(body_a: Body, body_b: Body, config: CCDConfig | None = None) -> CollisionCertificate:
    config = config or CCDConfig()
    try:
        config.validate()
    except ValueError as exc:
        return CollisionCertificate(CCDStatus.INVALID_INPUT, (body_a.body_id, body_b.body_id), "dispatcher", reason=str(exc)).finalize()

    for solver in (exact_sphere_sphere, exact_sphere_plane, exact_aabb_aabb):
        cert = solver(body_a, body_b, config)
        if cert is not None:
            return cert
    oracle = make_oracle(body_a, body_b)
    if oracle is None:
        return CollisionCertificate(
            CCDStatus.UNSUPPORTED,
            (body_a.body_id, body_b.body_id),
            "dispatcher",
            reason=f"no narrow-phase backend for {type(body_a.shape).__name__} versus {type(body_b.shape).__name__}",
        ).finalize()
    return conservative_advancement(oracle, config)


def detect_scene(bodies: list[Body], config: CCDConfig | None = None) -> SceneResult:
    config = config or CCDConfig()
    try:
        config.validate()
    except ValueError as exc:
        return SceneResult([], [], CCDStatus.INVALID_INPUT, {"reason": str(exc)})
    pairs, overflow = broadphase_sweep_and_prune(bodies, config.max_candidates)
    if overflow:
        return SceneResult(
            [],
            [(bodies[i].body_id, bodies[j].body_id) for i, j in pairs],
            CCDStatus.CAPACITY_EXCEEDED,
            {"reason": "broad-phase candidate capacity exceeded", "candidate_count": len(pairs)},
        )
    certs = [detect_pair(bodies[i], bodies[j], config) for i, j in pairs]
    scene_status = CCDStatus.NO_HIT
    if any(c.status == CCDStatus.INITIAL_OVERLAP for c in certs):
        scene_status = CCDStatus.INITIAL_OVERLAP
    elif any(c.status == CCDStatus.HIT for c in certs):
        scene_status = CCDStatus.HIT
    elif any(c.status in {CCDStatus.INCONCLUSIVE, CCDStatus.UNSUPPORTED, CCDStatus.INVALID_INPUT} for c in certs):
        scene_status = CCDStatus.INCONCLUSIVE
    return SceneResult(
        certs,
        [(bodies[i].body_id, bodies[j].body_id) for i, j in pairs],
        scene_status,
        {
            "body_count": len(bodies),
            "candidate_count": len(pairs),
            "hit_count": sum(c.hit for c in certs),
            "unsupported_count": sum(c.status == CCDStatus.UNSUPPORTED for c in certs),
        },
    )
