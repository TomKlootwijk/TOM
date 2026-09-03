"""Deterministic label-independent train/validation/holdout assignment."""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from tom_world03.canonical import attach_hash, canonical_bytes, require_hash

from .model import ObservationSet, SPLITS

SPLIT_CERTIFICATE_SCHEMA = "TOM-LEARNER-SPLIT-CERTIFICATE-0.1"


def _allocation(dataset: ObservationSet) -> dict[str, int]:
    n = len(dataset.observations)
    minima = dict(dataset.split_policy.minimum_counts)
    minimum_total = sum(minima.values())
    if n < minimum_total:
        raise ValueError(
            f"observation count {n} is below split minimum total {minimum_total}"
        )
    remaining = n - minimum_total
    ratios = dict(dataset.split_policy.ratios)
    total_ratio = sum(ratios.values())
    floors: dict[str, int] = {}
    remainders: dict[str, int] = {}
    for name in SPLITS:
        numerator = remaining * ratios[name]
        floors[name], remainders[name] = divmod(numerator, total_ratio)
    leftover = remaining - sum(floors.values())
    # The split-name order is a normative final tie break.
    remainder_order = sorted(
        SPLITS,
        key=lambda name: (-remainders[name], SPLITS.index(name)),
    )
    extras = {name: 0 for name in SPLITS}
    for name in remainder_order[:leftover]:
        extras[name] += 1
    counts = {
        name: minima[name] + floors[name] + extras[name]
        for name in SPLITS
    }
    if sum(counts.values()) != n:
        raise AssertionError("split allocation did not consume every observation")
    return counts


def assignment_digest(dataset: ObservationSet, observation_id: str) -> str:
    """Digest only identity and policy, never ``t`` or ``y`` values."""

    basis = {
        "seed_sha256": dataset.seed_sha256,
        "observation_set_id": dataset.id,
        "split_policy_hash": dataset.split_policy.content_hash,
        "salt": dataset.split_policy.salt,
        "observation_id": observation_id,
    }
    return hashlib.sha256(canonical_bytes(basis)).hexdigest()


def deterministic_split(dataset: ObservationSet) -> dict[str, Any]:
    counts = _allocation(dataset)
    ordered = sorted(
        (
            assignment_digest(dataset, observation.id),
            observation.id,
        )
        for observation in dataset.observations
    )
    assignments: list[dict[str, str]] = []
    split_ids: dict[str, list[str]] = {name: [] for name in SPLITS}
    cursor = 0
    for name in SPLITS:
        stop = cursor + counts[name]
        for digest, observation_id in ordered[cursor:stop]:
            assignments.append({
                "observation_id": observation_id,
                "assignment_digest": digest,
                "split": name,
            })
            split_ids[name].append(observation_id)
        cursor = stop
    assignments.sort(key=lambda item: item["observation_id"])
    for ids in split_ids.values():
        ids.sort()
    basis = {
        "strategy": dataset.split_policy.strategy,
        "seed_sha256": dataset.seed_sha256,
        "observation_set_id": dataset.id,
        "split_policy_hash": dataset.split_policy.content_hash,
        "salt": dataset.split_policy.salt,
        "observation_ids": sorted(observation.id for observation in dataset.observations),
    }
    return attach_hash({
        "schema": SPLIT_CERTIFICATE_SCHEMA,
        "profile": "TOM-LEARNER-0.1",
        "observation_set_id": dataset.id,
        "observation_set_hash": dataset.content_hash,
        "split_policy_hash": dataset.split_policy.content_hash,
        "assignment_basis_hash": "sha256:" + hashlib.sha256(canonical_bytes(basis)).hexdigest(),
        "assignment_uses_values": False,
        "counts": counts,
        "assignments": assignments,
        "splits": split_ids,
    })


def validate_split_certificate(dataset: ObservationSet, certificate: Mapping[str, Any]) -> None:
    require_hash(certificate, label="split certificate")
    if certificate.get("schema") != SPLIT_CERTIFICATE_SCHEMA:
        raise ValueError("unsupported split certificate schema")
    if certificate.get("observation_set_hash") != dataset.content_hash:
        raise ValueError("split certificate is bound to another observation set")
    expected = deterministic_split(dataset)
    if canonical_bytes(expected) != canonical_bytes(certificate):
        raise ValueError("split certificate does not reproduce deterministically")
