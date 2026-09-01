from __future__ import annotations

import math

from .motion import LinearMotion, StaticMotion
from .shapes import AxisAlignedBox, Body, Plane, Sphere
from .types import CCDConfig, CCDStatus, CollisionCertificate
from .vector import Vec3
from .oracles import SpherePlaneOracle, SphereSphereOracle


def _linear_velocity(body: Body) -> Vec3 | None:
    if isinstance(body.motion, LinearMotion):
        return body.motion.velocity_vector
    if isinstance(body.motion, StaticMotion):
        return Vec3(0.0, 0.0, 0.0)
    return None


def exact_sphere_sphere(body_a: Body, body_b: Body, config: CCDConfig) -> CollisionCertificate | None:
    if not (isinstance(body_a.shape, Sphere) and isinstance(body_b.shape, Sphere)):
        return None
    va = _linear_velocity(body_a)
    vb = _linear_velocity(body_b)
    if va is None or vb is None:
        return None
    oracle = SphereSphereOracle(body_a, body_b)
    s0 = oracle.evaluate(0.0)
    pair = (body_a.body_id, body_b.body_id)
    if s0.distance < -config.distance_tolerance:
        return CollisionCertificate(CCDStatus.INITIAL_OVERLAP, pair, "exact_sphere_sphere_linear", 0.0, 0.0, s0, reason="negative initial separation").finalize()
    if s0.distance <= config.distance_tolerance:
        return CollisionCertificate(CCDStatus.HIT, pair, "exact_sphere_sphere_linear", 0.0, 0.0, s0, reason="initial contact within tolerance").finalize()

    p = body_b.motion.position(0.0) - body_a.motion.position(0.0)
    v = vb - va
    radius = body_a.shape.radius + body_b.shape.radius
    a = v.dot(v)
    b = 2.0 * p.dot(v)
    c = p.dot(p) - radius * radius
    if a <= config.speed_epsilon * config.speed_epsilon:
        return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_sphere_sphere_linear", reason="zero relative speed and positive separation", sample=s0).finalize()
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_sphere_sphere_linear", reason="quadratic has no real roots", sample=s0).finalize()
    sqrt_disc = math.sqrt(max(0.0, disc))
    q = -0.5 * (b + math.copysign(sqrt_disc, b))
    roots: list[float]
    if abs(q) <= 1e-30:
        roots = [-b / (2.0 * a)]
    else:
        roots = [q / a, c / q]
    valid = sorted(t for t in roots if -config.time_tolerance <= t <= 1.0 + config.time_tolerance)
    if not valid:
        return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_sphere_sphere_linear", reason="roots lie outside the step", sample=s0).finalize()
    toi = min(max(valid[0], 0.0), 1.0)
    sample = oracle.evaluate(toi)
    return CollisionCertificate(CCDStatus.HIT, pair, "exact_sphere_sphere_linear", toi, toi, sample, iterations=1, reason="earliest quadratic root").finalize()


def exact_sphere_plane(body_a: Body, body_b: Body, config: CCDConfig) -> CollisionCertificate | None:
    reverse = False
    sphere_body, plane_body = body_a, body_b
    if isinstance(body_a.shape, Plane) and isinstance(body_b.shape, Sphere):
        reverse = True
        sphere_body, plane_body = body_b, body_a
    if not (isinstance(sphere_body.shape, Sphere) and isinstance(plane_body.shape, Plane)):
        return None
    vs = _linear_velocity(sphere_body)
    vp = _linear_velocity(plane_body)
    if vs is None or vp is None:
        return None
    oracle = SpherePlaneOracle(sphere_body, plane_body)
    s0 = oracle.evaluate(0.0)
    pair = (body_a.body_id, body_b.body_id)
    if s0.distance < -config.distance_tolerance:
        cert = CollisionCertificate(CCDStatus.INITIAL_OVERLAP, pair, "exact_sphere_plane_linear", 0.0, 0.0, s0, reason="negative initial separation")
        return cert.finalize()
    if s0.distance <= config.distance_tolerance:
        return CollisionCertificate(CCDStatus.HIT, pair, "exact_sphere_plane_linear", 0.0, 0.0, s0, reason="initial contact within tolerance").finalize()
    plane = plane_body.shape
    relative_velocity = vs - vp
    derivative = plane.normal.dot(relative_velocity)
    if derivative >= -config.speed_epsilon:
        return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_sphere_plane_linear", reason="sphere is not approaching the one-sided plane", sample=s0).finalize()
    toi = -s0.distance / derivative
    if toi < -config.time_tolerance or toi > 1.0 + config.time_tolerance:
        return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_sphere_plane_linear", reason="contact lies outside the step", sample=s0).finalize()
    toi = min(max(toi, 0.0), 1.0)
    sample = oracle.evaluate(toi)
    if reverse:
        sample = type(sample)(sample.t, sample.distance, -sample.normal, sample.witness_b, sample.witness_a)
    return CollisionCertificate(CCDStatus.HIT, pair, "exact_sphere_plane_linear", toi, toi, sample, iterations=1, reason="linear signed-distance root").finalize()


def exact_aabb_aabb(body_a: Body, body_b: Body, config: CCDConfig) -> CollisionCertificate | None:
    if not (isinstance(body_a.shape, AxisAlignedBox) and isinstance(body_b.shape, AxisAlignedBox)):
        return None
    va = _linear_velocity(body_a)
    vb = _linear_velocity(body_b)
    if va is None or vb is None:
        return None
    ca = body_a.motion.position(0.0)
    cb = body_b.motion.position(0.0)
    p = cb - ca
    v = vb - va
    ext = body_a.shape.half_extents + body_b.shape.half_extents
    pair = (body_a.body_id, body_b.body_id)
    initially_overlapping = all(abs(p.component(axis)) <= ext.component(axis) for axis in range(3))
    if initially_overlapping:
        return CollisionCertificate(CCDStatus.INITIAL_OVERLAP, pair, "exact_swept_aabb_linear", 0.0, 0.0, reason="AABBs overlap at t=0").finalize()

    t_enter = 0.0
    t_exit = 1.0
    enter_axis = 0
    enter_sign = 1.0
    for axis in range(3):
        pi = p.component(axis)
        vi = v.component(axis)
        ei = ext.component(axis)
        if abs(vi) <= config.speed_epsilon:
            if abs(pi) > ei:
                return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_swept_aabb_linear", reason=f"separated static slab on axis {axis}").finalize()
            continue
        t1 = (-ei - pi) / vi
        t2 = (ei - pi) / vi
        lo, hi = (t1, t2) if t1 <= t2 else (t2, t1)
        if lo > t_enter:
            t_enter = lo
            enter_axis = axis
            enter_sign = -1.0 if vi > 0.0 else 1.0
        t_exit = min(t_exit, hi)
        if t_enter > t_exit:
            return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_swept_aabb_linear", reason="slab intervals do not overlap").finalize()
    if t_exit < 0.0 or t_enter > 1.0:
        return CollisionCertificate(CCDStatus.NO_HIT, pair, "exact_swept_aabb_linear", reason="overlap interval lies outside the step").finalize()
    toi = max(0.0, t_enter)
    normal_components = [0.0, 0.0, 0.0]
    normal_components[enter_axis] = enter_sign
    normal = Vec3.from_iterable(normal_components)
    ca_t = body_a.motion.position(toi)
    cb_t = body_b.motion.position(toi)
    from .types import SeparationSample
    sample = SeparationSample(toi, 0.0, normal, ca_t, cb_t)
    return CollisionCertificate(CCDStatus.HIT, pair, "exact_swept_aabb_linear", toi, toi, sample, iterations=1, reason="slab entry time").finalize()
