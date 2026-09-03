"""Typed, content-addressed records for TOM Learner 0.1.

The authority boundary is deliberately explicit:

    observations -> deterministic split -> candidate hypotheses -> evidence
    -> acceptance decision -> optional learned definition -> promotion

The learner never mutates the base world directly.  A candidate can become
visible in the authoritative learner overlay only through ``LearnerStore`` and
a parent-bound promotion transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from tom_world03.canonical import require_hash
from tom_world03.rational import Q

CANONICAL_SEED_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
BASE_WORLD_HASH = "sha256:c25c99eeeb728f50b52a06e89b9f669470ccb294fd8f0cc6e4ccb87bde9ff2d9"
BASE_HANDOFF_HASH = "sha256:3d2b46cfd33ba6e5cf0a13697fb59e374a64ad30450fdd3c256c98a04ebc474b"

PROFILE = "TOM-LEARNER-0.1"
OBSERVATION_SCHEMA = "TOM-EXACT-OBSERVATION-0.1"
OBSERVATION_SET_SCHEMA = "TOM-AFFINE-OBSERVATION-SET-0.1"
SPLIT_POLICY_SCHEMA = "TOM-LEARNER-SPLIT-POLICY-0.1"
HYPOTHESIS_FAMILY_SCHEMA = "TOM-AFFINE-HYPOTHESIS-FAMILY-0.1"
ACCEPTANCE_POLICY_SCHEMA = "TOM-LEARNER-ACCEPTANCE-POLICY-0.1"

SPLITS = ("train", "validation", "holdout")


def _require_nonempty(value: Any, label: str) -> str:
    text = str(value)
    if not text:
        raise ValueError(f"{label} must be nonempty")
    return text


def _require_hash_text(value: Any, label: str) -> str:
    text = str(value)
    if not text.startswith("sha256:") or len(text) != 71:
        raise ValueError(f"{label} must be a sha256: content hash")
    try:
        int(text[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{label} must contain hexadecimal SHA-256") from exc
    if text[7:] != text[7:].lower():
        raise ValueError(f"{label} must use lowercase hexadecimal")
    return text


def _positive_integer(value: Any, label: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class Observation:
    id: str
    t: Q
    y: Q
    provenance: Mapping[str, Any]
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Observation":
        require_hash(record, label="observation")
        if record.get("schema") != OBSERVATION_SCHEMA:
            raise ValueError(f"observation schema must be {OBSERVATION_SCHEMA}")
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping):
            raise ValueError("observation provenance must be an object")
        return cls(
            id=_require_nonempty(record.get("id", ""), "observation id"),
            t=Q.from_value(record.get("t")),
            y=Q.from_value(record.get("y")),
            provenance=dict(provenance),
            content_hash=_require_hash_text(record.get("content_hash"), "observation content_hash"),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": OBSERVATION_SCHEMA,
            "id": self.id,
            "t": self.t.to_record(),
            "y": self.y.to_record(),
            "provenance": dict(self.provenance),
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class SplitPolicy:
    strategy: str
    ratios: Mapping[str, int]
    minimum_counts: Mapping[str, int]
    salt: str
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "SplitPolicy":
        require_hash(record, label="split policy")
        if record.get("schema") != SPLIT_POLICY_SCHEMA:
            raise ValueError(f"split policy schema must be {SPLIT_POLICY_SCHEMA}")
        strategy = str(record.get("strategy", ""))
        if strategy != "sha256-id-order-largest-remainder":
            raise ValueError("unsupported split strategy")
        ratios_raw = record.get("ratios")
        minima_raw = record.get("minimum_counts")
        if not isinstance(ratios_raw, Mapping) or set(ratios_raw) != set(SPLITS):
            raise ValueError("split ratios must name train, validation, and holdout exactly")
        if not isinstance(minima_raw, Mapping) or set(minima_raw) != set(SPLITS):
            raise ValueError("minimum_counts must name train, validation, and holdout exactly")
        ratios = {name: _positive_integer(ratios_raw[name], f"ratio {name}") for name in SPLITS}
        minima = {name: _positive_integer(minima_raw[name], f"minimum {name}", minimum=0) for name in SPLITS}
        if minima["train"] < 2:
            raise ValueError("training minimum must be at least two")
        return cls(
            strategy=strategy,
            ratios=ratios,
            minimum_counts=minima,
            salt=_require_nonempty(record.get("salt", ""), "split salt"),
            content_hash=_require_hash_text(record.get("content_hash"), "split policy hash"),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": SPLIT_POLICY_SCHEMA,
            "strategy": self.strategy,
            "ratios": {name: int(self.ratios[name]) for name in SPLITS},
            "minimum_counts": {name: int(self.minimum_counts[name]) for name in SPLITS},
            "salt": self.salt,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class HypothesisFamily:
    model: str
    candidate_source: str
    max_candidates: int
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "HypothesisFamily":
        require_hash(record, label="hypothesis family")
        if record.get("schema") != HYPOTHESIS_FAMILY_SCHEMA:
            raise ValueError(f"hypothesis family schema must be {HYPOTHESIS_FAMILY_SCHEMA}")
        if record.get("model") != "y=a*t+b":
            raise ValueError("TOM Learner 0.1 supports only y=a*t+b")
        source = str(record.get("candidate_source", ""))
        if source != "all-distinct-t-unordered-training-pairs":
            raise ValueError("unsupported affine candidate source")
        return cls(
            model="y=a*t+b",
            candidate_source=source,
            max_candidates=_positive_integer(record.get("max_candidates"), "max_candidates"),
            content_hash=_require_hash_text(record.get("content_hash"), "hypothesis family hash"),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": HYPOTHESIS_FAMILY_SCHEMA,
            "model": self.model,
            "candidate_source": self.candidate_source,
            "max_candidates": self.max_candidates,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class AcceptancePolicy:
    require_unique_exact_train: bool
    require_exact_validation: bool
    require_exact_holdout: bool
    reject_contradictions: bool
    max_model_complexity: int
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "AcceptancePolicy":
        require_hash(record, label="acceptance policy")
        if record.get("schema") != ACCEPTANCE_POLICY_SCHEMA:
            raise ValueError(f"acceptance policy schema must be {ACCEPTANCE_POLICY_SCHEMA}")
        bool_fields = (
            "require_unique_exact_train",
            "require_exact_validation",
            "require_exact_holdout",
            "reject_contradictions",
        )
        for field in bool_fields:
            if not isinstance(record.get(field), bool):
                raise ValueError(f"acceptance policy {field} must be boolean")
        return cls(
            require_unique_exact_train=bool(record["require_unique_exact_train"]),
            require_exact_validation=bool(record["require_exact_validation"]),
            require_exact_holdout=bool(record["require_exact_holdout"]),
            reject_contradictions=bool(record["reject_contradictions"]),
            max_model_complexity=_positive_integer(record.get("max_model_complexity"), "max_model_complexity"),
            content_hash=_require_hash_text(record.get("content_hash"), "acceptance policy hash"),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": ACCEPTANCE_POLICY_SCHEMA,
            "require_unique_exact_train": self.require_unique_exact_train,
            "require_exact_validation": self.require_exact_validation,
            "require_exact_holdout": self.require_exact_holdout,
            "reject_contradictions": self.reject_contradictions,
            "max_model_complexity": self.max_model_complexity,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class ObservationSet:
    id: str
    seed_sha256: str
    base_world_hash: str
    base_handoff_hash: str
    input_name: str
    output_name: str
    observations: tuple[Observation, ...]
    split_policy: SplitPolicy
    hypothesis_family: HypothesisFamily
    acceptance_policy: AcceptancePolicy
    provenance: Mapping[str, Any]
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "ObservationSet":
        require_hash(record, label="observation set")
        if record.get("schema") != OBSERVATION_SET_SCHEMA:
            raise ValueError(f"observation-set schema must be {OBSERVATION_SET_SCHEMA}")
        if record.get("profile") != PROFILE:
            raise ValueError(f"observation-set profile must be {PROFILE}")
        seed = str(record.get("seed_sha256", ""))
        if seed != CANONICAL_SEED_SHA256:
            raise ValueError("observation set is not bound to the canonical TOM seed")
        base = _require_hash_text(record.get("base_world_hash"), "base_world_hash")
        if base != BASE_WORLD_HASH:
            raise ValueError("observation set is bound to an unsupported base world")
        handoff = _require_hash_text(record.get("base_handoff_hash"), "base_handoff_hash")
        if handoff != BASE_HANDOFF_HASH:
            raise ValueError("observation set is bound to an unsupported literal handoff")
        domain = record.get("domain")
        if not isinstance(domain, Mapping) or domain.get("numeric") != "exact-rational":
            raise ValueError("observation-set domain must declare exact-rational numeric semantics")
        values = record.get("observations")
        if not isinstance(values, list) or not values:
            raise ValueError("observation set requires a nonempty observations array")
        observations = tuple(Observation.from_record(value) for value in values)
        ids = [item.id for item in observations]
        if len(ids) != len(set(ids)):
            raise ValueError("observation IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("observations must be sorted by ID")
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping):
            raise ValueError("observation-set provenance must be an object")
        split = record.get("split_policy")
        family = record.get("hypothesis_family")
        policy = record.get("acceptance_policy")
        if not all(isinstance(value, Mapping) for value in (split, family, policy)):
            raise ValueError("observation-set policies must be objects")
        return cls(
            id=_require_nonempty(record.get("id", ""), "observation-set id"),
            seed_sha256=seed,
            base_world_hash=base,
            base_handoff_hash=handoff,
            input_name=_require_nonempty(domain.get("input", ""), "input field name"),
            output_name=_require_nonempty(domain.get("output", ""), "output field name"),
            observations=observations,
            split_policy=SplitPolicy.from_record(split),
            hypothesis_family=HypothesisFamily.from_record(family),
            acceptance_policy=AcceptancePolicy.from_record(policy),
            provenance=dict(provenance),
            content_hash=_require_hash_text(record.get("content_hash"), "observation-set hash"),
        )

    def observation_map(self) -> dict[str, Observation]:
        return {item.id: item for item in self.observations}

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": OBSERVATION_SET_SCHEMA,
            "profile": PROFILE,
            "id": self.id,
            "seed_sha256": self.seed_sha256,
            "base_world_hash": self.base_world_hash,
            "base_handoff_hash": self.base_handoff_hash,
            "domain": {
                "input": self.input_name,
                "output": self.output_name,
                "numeric": "exact-rational",
            },
            "observations": [item.to_record() for item in self.observations],
            "split_policy": self.split_policy.to_record(),
            "hypothesis_family": self.hypothesis_family.to_record(),
            "acceptance_policy": self.acceptance_policy.to_record(),
            "provenance": dict(self.provenance),
            "content_hash": self.content_hash,
        }

    def source_records(self) -> list[Mapping[str, Any]]:
        """Return every literal content-addressed input record in causal order."""

        return [
            self.split_policy.to_record(),
            self.hypothesis_family.to_record(),
            self.acceptance_policy.to_record(),
            *(item.to_record() for item in self.observations),
            self.to_record(),
        ]


def require_dataset_sequence(values: Any) -> Sequence[Mapping[str, Any]]:
    if not isinstance(values, list) or not values:
        raise ValueError("benchmark datasets must be a nonempty array")
    if not all(isinstance(value, Mapping) for value in values):
        raise ValueError("benchmark dataset entries must be objects")
    return values  # type: ignore[return-value]
