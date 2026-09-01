from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Any

from .vector import Vec3


class CCDStatus(str, Enum):
    HIT = "HIT"
    NO_HIT = "NO_HIT"
    INITIAL_OVERLAP = "INITIAL_OVERLAP"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"


@dataclass(frozen=True, slots=True)
class CCDConfig:
    distance_tolerance: float = 1e-8
    time_tolerance: float = 1e-10
    safety_factor: float = 0.8
    max_iterations: int = 128
    speed_epsilon: float = 1e-14
    max_candidates: int = 100_000
    max_trace_steps: int = 256
    interval_max_nodes: int = 4096
    split_policy: str = "midpoint"
    use_nhdf_hints: bool = True

    def validate(self) -> None:
        if not (self.distance_tolerance > 0.0 and math.isfinite(self.distance_tolerance)):
            raise ValueError("distance_tolerance must be positive and finite")
        if not (self.time_tolerance > 0.0 and math.isfinite(self.time_tolerance)):
            raise ValueError("time_tolerance must be positive and finite")
        if not (0.0 < self.safety_factor <= 1.0):
            raise ValueError("safety_factor must lie in (0, 1]")
        if self.max_iterations <= 0 or self.max_candidates <= 0 or self.interval_max_nodes <= 0:
            raise ValueError("iteration and capacity limits must be positive")
        if self.split_policy not in {"midpoint", "golden"}:
            raise ValueError("split_policy must be 'midpoint' or 'golden'")


@dataclass(frozen=True, slots=True)
class SeparationSample:
    t: float
    distance: float
    normal: Vec3
    witness_a: Vec3
    witness_b: Vec3


@dataclass(slots=True)
class CollisionCertificate:
    status: CCDStatus
    pair: tuple[str, str]
    backend: str
    toi_lower: float | None = None
    toi_upper: float | None = None
    sample: SeparationSample | None = None
    iterations: int = 0
    reason: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    trace_digest: str = ""

    def finalize(self) -> "CollisionCertificate":
        payload = {
            "status": self.status.value,
            "pair": self.pair,
            "backend": self.backend,
            "toi_lower": self.toi_lower,
            "toi_upper": self.toi_upper,
            "iterations": self.iterations,
            "reason": self.reason,
            "trace": self.trace,
            "metadata": self.metadata,
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.trace_digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return self

    @property
    def hit(self) -> bool:
        return self.status in {CCDStatus.HIT, CCDStatus.INITIAL_OVERLAP}

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status.value,
            "pair": list(self.pair),
            "backend": self.backend,
            "toi_lower": self.toi_lower,
            "toi_upper": self.toi_upper,
            "iterations": self.iterations,
            "reason": self.reason,
            "trace": self.trace,
            "metadata": self.metadata,
            "trace_digest": self.trace_digest,
        }
        if self.sample is not None:
            result["sample"] = {
                "t": self.sample.t,
                "distance": self.sample.distance,
                "normal": list(self.sample.normal.to_tuple()),
                "witness_a": list(self.sample.witness_a.to_tuple()),
                "witness_b": list(self.sample.witness_b.to_tuple()),
            }
        return result


@dataclass(slots=True)
class SceneResult:
    certificates: list[CollisionCertificate]
    candidates: list[tuple[str, str]]
    status: CCDStatus = CCDStatus.NO_HIT
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "candidates": [list(pair) for pair in self.candidates],
            "telemetry": self.telemetry,
            "certificates": [c.to_dict() for c in self.certificates],
        }
