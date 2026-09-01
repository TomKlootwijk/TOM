from __future__ import annotations

import math

from .nhdf import nhdf_hint_for_sample
from .oracles import SeparationOracle
from .types import CCDConfig, CCDStatus, CollisionCertificate


def conservative_advancement(
    oracle: SeparationOracle,
    config: CCDConfig,
    *,
    t0: float = 0.0,
    t1: float = 1.0,
) -> CollisionCertificate:
    """Certified time advancement under an oracle-supplied Lipschitz speed bound.

    Safety is conditional on two contracts:
      1. ``evaluate(t).distance`` does not overstate true separation; and
      2. ``closure_speed_bound(a,b)`` upper-bounds the absolute rate of change
         of that separation over the interval.
    """
    config.validate()
    pair = (oracle.body_a.body_id, oracle.body_b.body_id)
    backend = "conservative_advancement"
    trace: list[dict[str, float | int]] = []
    t = t0
    previous_t = t0
    sample = oracle.evaluate(t)
    if not math.isfinite(sample.distance):
        return CollisionCertificate(CCDStatus.INVALID_INPUT, pair, backend, reason="non-finite initial separation").finalize()
    if sample.distance < -config.distance_tolerance:
        return CollisionCertificate(CCDStatus.INITIAL_OVERLAP, pair, backend, t, t, sample, reason="negative initial separation").finalize()
    if sample.distance <= config.distance_tolerance:
        return CollisionCertificate(CCDStatus.HIT, pair, backend, t, t, sample, reason="initial contact within tolerance").finalize()

    metadata: dict[str, object] = {}
    for iteration in range(1, config.max_iterations + 1):
        speed_bound = float(oracle.closure_speed_bound(t, t1))
        if not math.isfinite(speed_bound) or speed_bound < 0.0:
            return CollisionCertificate(CCDStatus.INVALID_INPUT, pair, backend, iterations=iteration, reason="invalid closure-speed bound", trace=trace).finalize()
        if config.use_nhdf_hints:
            metadata["nhdf_hint"] = nhdf_hint_for_sample(sample, oracle, t).to_dict()
        if speed_bound <= config.speed_epsilon:
            return CollisionCertificate(
                CCDStatus.NO_HIT,
                pair,
                backend,
                sample=sample,
                iterations=iteration,
                reason="positive separation with zero closure-speed bound",
                trace=trace,
                metadata=metadata,
            ).finalize()

        remaining = t1 - t
        safe_step = config.safety_factor * sample.distance / speed_bound
        no_hit_margin = sample.distance - speed_bound * remaining
        trace_item = {
            "iteration": iteration,
            "t": t,
            "distance": sample.distance,
            "speed_bound": speed_bound,
            "safe_step": safe_step,
            "remaining": remaining,
            "no_hit_margin": no_hit_margin,
        }
        if len(trace) < config.max_trace_steps:
            trace.append(trace_item)

        if no_hit_margin > 0.0:
            return CollisionCertificate(
                CCDStatus.NO_HIT,
                pair,
                backend,
                sample=sample,
                iterations=iteration,
                reason="Lipschitz no-hit certificate covers the remaining interval",
                trace=trace,
                metadata=metadata,
            ).finalize()

        if safe_step <= config.time_tolerance:
            # The query is closer than the declared temporal resolution. Returning
            # INCONCLUSIVE is safer than silently stepping past a possible contact.
            return CollisionCertificate(
                CCDStatus.INCONCLUSIVE,
                pair,
                backend,
                toi_lower=max(previous_t, t0),
                toi_upper=min(t + config.time_tolerance, t1),
                sample=sample,
                iterations=iteration,
                reason="advancement stalled at temporal resolution before contact tolerance",
                trace=trace,
                metadata=metadata,
            ).finalize()

        previous_t = t
        t = min(t + safe_step, t1)
        sample = oracle.evaluate(t)
        if not math.isfinite(sample.distance):
            return CollisionCertificate(CCDStatus.INVALID_INPUT, pair, backend, iterations=iteration, reason="non-finite separation", trace=trace).finalize()
        if sample.distance < -config.distance_tolerance:
            # A valid conservative oracle should not jump from a certified positive
            # interval to deep overlap. Preserve the failure rather than hide it.
            return CollisionCertificate(
                CCDStatus.INCONCLUSIVE,
                pair,
                backend,
                toi_lower=previous_t,
                toi_upper=t,
                sample=sample,
                iterations=iteration,
                reason="oracle contract violation or numerical overshoot",
                trace=trace,
                metadata=metadata,
            ).finalize()
        if sample.distance <= config.distance_tolerance:
            return CollisionCertificate(
                CCDStatus.HIT,
                pair,
                backend,
                toi_lower=previous_t,
                toi_upper=t,
                sample=sample,
                iterations=iteration,
                reason="conservative contact bracket reached",
                trace=trace,
                metadata=metadata,
            ).finalize()
        if t >= t1:
            return CollisionCertificate(
                CCDStatus.NO_HIT,
                pair,
                backend,
                sample=sample,
                iterations=iteration,
                reason="reached end of interval with positive separation",
                trace=trace,
                metadata=metadata,
            ).finalize()

    return CollisionCertificate(
        CCDStatus.INCONCLUSIVE,
        pair,
        backend,
        toi_lower=previous_t,
        toi_upper=t,
        sample=sample,
        iterations=config.max_iterations,
        reason="iteration budget exhausted",
        trace=trace,
        metadata=metadata,
    ).finalize()
