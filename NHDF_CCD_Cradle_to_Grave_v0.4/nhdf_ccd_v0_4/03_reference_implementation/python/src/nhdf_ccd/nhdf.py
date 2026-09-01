from __future__ import annotations

from dataclasses import dataclass
import math

from .oracles import SeparationOracle
from .types import SeparationSample


@dataclass(frozen=True, slots=True)
class NHDFHint:
    rho_bin: int
    theta_bin: int
    time_bin: int
    packed_word: int
    parity: int
    priority: float

    def to_dict(self) -> dict[str, int | float]:
        return {
            "rho_bin": self.rho_bin,
            "theta_bin": self.theta_bin,
            "time_bin": self.time_bin,
            "packed_word": self.packed_word,
            "parity": self.parity,
            "priority": self.priority,
        }


def nhdf_hint_for_sample(sample: SeparationSample, oracle: SeparationOracle, t: float) -> NHDFHint:
    """Create source-traceable log-polar/parity scheduling metadata.

    This hint is intentionally outside the correctness path. It may prioritize a
    query or choose a refinement budget, but it must never suppress a candidate
    or certify a collision result.
    """
    rho = math.log1p(max(sample.distance, 0.0))
    rel_v = oracle.body_b.motion.velocity(t) - oracle.body_a.motion.velocity(t)
    theta = math.atan2(rel_v.y, rel_v.x)
    rho_bin = max(0, min(4095, int(round(rho * 256.0))))
    theta_bin = max(0, min(4095, int(round((theta + math.pi) * 4095.0 / (2.0 * math.pi)))))
    time_bin = max(0, min(4095, int(round(t * 4095.0))))
    packed = (rho_bin << 24) | (theta_bin << 12) | time_bin
    parity = packed.bit_count() & 1
    priority = 1.0 / (sample.distance + 1e-12)
    return NHDFHint(rho_bin, theta_bin, time_bin, packed, parity, priority)


def second_phase_difference(phi_n: float, phi_nm1: float, phi_nm2: float) -> float:
    raw = phi_n - 2.0 * phi_nm1 + phi_nm2
    return (raw + math.pi) % (2.0 * math.pi) - math.pi
