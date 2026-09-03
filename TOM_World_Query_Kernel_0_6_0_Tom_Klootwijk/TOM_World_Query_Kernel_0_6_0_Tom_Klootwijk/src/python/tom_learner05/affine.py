"""Exact rational affine candidate generation and residual evidence."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
import hashlib
from typing import Any, Iterable, Mapping

from tom_world03.canonical import attach_hash, canonical_bytes, require_hash
from tom_world03.rational import Q

from .model import Observation, ObservationSet, SPLITS
from .split import SPLIT_CERTIFICATE_SCHEMA

CANDIDATE_SCHEMA = "TOM-AFFINE-HYPOTHESIS-CANDIDATE-0.1"
ENUMERATION_SCHEMA = "TOM-AFFINE-CANDIDATE-ENUMERATION-0.1"
RESIDUAL_EVIDENCE_SCHEMA = "TOM-AFFINE-RESIDUAL-EVIDENCE-0.1"
SELECTION_SCHEMA = "TOM-AFFINE-SELECTION-CERTIFICATE-0.1"
CONTRADICTION_SCHEMA = "TOM-OBSERVATION-CONTRADICTION-0.1"
COUNTEREXAMPLE_SCHEMA = "TOM-AFFINE-COUNTEREXAMPLE-0.1"


def q_complexity(value: Q) -> int:
    """Portable literal complexity in signed numerator/positive denominator bits."""

    sign = 1 if value.numerator < 0 else 0
    return sign + max(1, abs(value.numerator).bit_length()) + value.denominator.bit_length()


def model_complexity(a: Q, b: Q) -> int:
    return q_complexity(a) + q_complexity(b) + int(a != Q(0)) + int(b != Q(0))


def predict(a: Q, b: Q, t: Q) -> Q:
    return a * t + b


def residual(a: Q, b: Q, observation: Observation) -> Q:
    return observation.y - predict(a, b, observation.t)


def _fit_input_record(dataset: ObservationSet, train_ids: Iterable[str]) -> dict[str, Any]:
    by_id = dataset.observation_map()
    ids = sorted(train_ids)
    return {
        "observation_set_id": dataset.id,
        "hypothesis_family_hash": dataset.hypothesis_family.content_hash,
        "training_observations": [
            {
                "id": ident,
                "content_hash": by_id[ident].content_hash,
                "t": by_id[ident].t.to_record(),
                "y": by_id[ident].y.to_record(),
            }
            for ident in ids
        ],
    }


def fit_input_hash(dataset: ObservationSet, train_ids: Iterable[str]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(_fit_input_record(dataset, train_ids))).hexdigest()


def candidate_identity(a: Q, b: Q) -> str:
    basis = {"model": "y=a*t+b", "a": a.to_record(), "b": b.to_record()}
    return "hypothesis:affine:" + hashlib.sha256(canonical_bytes(basis)).hexdigest()[:24]


def derive_candidates(
    dataset: ObservationSet,
    split_certificate: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    require_hash(split_certificate, label="split certificate")
    if split_certificate.get("schema") != SPLIT_CERTIFICATE_SCHEMA:
        raise ValueError("unsupported split certificate")
    if split_certificate.get("observation_set_hash") != dataset.content_hash:
        raise ValueError("split certificate is bound to another observation set")
    train_ids = list(split_certificate.get("splits", {}).get("train", []))
    by_id = dataset.observation_map()
    try:
        training = [by_id[ident] for ident in train_ids]
    except KeyError as exc:
        raise ValueError(f"split references unknown training observation {exc.args[0]}") from exc
    if len(training) < 2:
        raise ValueError("affine fitting requires at least two training observations")

    grouped: dict[tuple[Q, Q], list[tuple[str, str]]] = defaultdict(list)
    pair_count = 0
    for left, right in combinations(sorted(training, key=lambda item: item.id), 2):
        if left.t == right.t:
            continue
        pair_count += 1
        a = (right.y - left.y) / (right.t - left.t)
        b = left.y - a * left.t
        grouped[(a, b)].append((left.id, right.id))
        if len(grouped) > dataset.hypothesis_family.max_candidates:
            raise ValueError("affine candidate budget exceeded")

    fit_hash = fit_input_hash(dataset, train_ids)
    candidates: list[dict[str, Any]] = []
    for (a, b), pairs in grouped.items():
        pairs = sorted(set(tuple(sorted(pair)) for pair in pairs))
        candidate = attach_hash({
            "schema": CANDIDATE_SCHEMA,
            "profile": "TOM-LEARNER-0.1",
            "id": candidate_identity(a, b),
            "observation_set_id": dataset.id,
            "hypothesis_family_hash": dataset.hypothesis_family.content_hash,
            "split_certificate_hash": split_certificate["content_hash"],
            "fit_input_hash": fit_hash,
            "fit_uses_splits": ["train"],
            "model": "y=a*t+b",
            "coefficients": {"a": a.to_record(), "b": b.to_record()},
            "supporting_pairs": [[left, right] for left, right in pairs],
            "complexity": model_complexity(a, b),
        })
        candidates.append(candidate)

    def order_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
        coeffs = candidate["coefficients"]
        return (
            int(candidate["complexity"]),
            Q.from_value(coeffs["a"]),
            Q.from_value(coeffs["b"]),
            str(candidate["id"]),
        )

    candidates.sort(key=order_key)
    enumeration = attach_hash({
        "schema": ENUMERATION_SCHEMA,
        "profile": "TOM-LEARNER-0.1",
        "observation_set_id": dataset.id,
        "observation_set_hash": dataset.content_hash,
        "split_certificate_hash": split_certificate["content_hash"],
        "hypothesis_family_hash": dataset.hypothesis_family.content_hash,
        "fit_input_hash": fit_hash,
        "fit_uses_splits": ["train"],
        "training_observation_ids": sorted(train_ids),
        "distinct_t_pair_count": pair_count,
        "candidate_count": len(candidates),
        "candidate_order": [candidate["content_hash"] for candidate in candidates],
        "candidate_ids": [candidate["id"] for candidate in candidates],
    })
    return candidates, enumeration


def candidate_coefficients(candidate: Mapping[str, Any]) -> tuple[Q, Q]:
    require_hash(candidate, label="affine candidate")
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise ValueError("unsupported affine candidate schema")
    coeffs = candidate.get("coefficients")
    if not isinstance(coeffs, Mapping):
        raise ValueError("candidate coefficients must be an object")
    return Q.from_value(coeffs.get("a")), Q.from_value(coeffs.get("b"))


def _metrics(residuals: list[Q]) -> dict[str, Any]:
    absolute = [abs(value) for value in residuals]
    squared = [value * value for value in residuals]
    maximum = max(absolute, default=Q(0))
    return {
        "count": len(residuals),
        "zero_count": sum(value == Q(0) for value in residuals),
        "nonzero_count": sum(value != Q(0) for value in residuals),
        "max_abs_residual": maximum.to_record(),
        "sum_abs_residual": sum(absolute, Q(0)).to_record(),
        "sum_squared_residual": sum(squared, Q(0)).to_record(),
        "exact": all(value == Q(0) for value in residuals),
    }


def evaluate_candidate(
    dataset: ObservationSet,
    split_certificate: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    a, b = candidate_coefficients(candidate)
    if candidate.get("observation_set_id") != dataset.id:
        raise ValueError("candidate belongs to another observation set")
    if candidate.get("split_certificate_hash") != split_certificate.get("content_hash"):
        raise ValueError("candidate belongs to another split")
    by_id = dataset.observation_map()
    split_records: dict[str, Any] = {}
    for name in SPLITS:
        ids = list(split_certificate.get("splits", {}).get(name, []))
        rows: list[dict[str, Any]] = []
        values: list[Q] = []
        for ident in ids:
            observation = by_id[ident]
            predicted = predict(a, b, observation.t)
            value = observation.y - predicted
            values.append(value)
            rows.append({
                "observation_id": observation.id,
                "observation_hash": observation.content_hash,
                "t": observation.t.to_record(),
                "observed_y": observation.y.to_record(),
                "predicted_y": predicted.to_record(),
                "residual": value.to_record(),
            })
        split_records[name] = {
            "metrics": _metrics(values),
            "residuals": rows,
        }
    return attach_hash({
        "schema": RESIDUAL_EVIDENCE_SCHEMA,
        "profile": "TOM-LEARNER-0.1",
        "observation_set_id": dataset.id,
        "observation_set_hash": dataset.content_hash,
        "split_certificate_hash": split_certificate["content_hash"],
        "candidate_id": candidate["id"],
        "candidate_hash": candidate["content_hash"],
        "fit_input_hash": candidate["fit_input_hash"],
        "splits": split_records,
    })


def training_rank(candidate: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[Any, ...]:
    metrics = evidence["splits"]["train"]["metrics"]
    return (
        int(metrics["nonzero_count"]),
        Q.from_value(metrics["max_abs_residual"]),
        Q.from_value(metrics["sum_abs_residual"]),
        int(candidate["complexity"]),
        Q.from_value(candidate["coefficients"]["a"]),
        Q.from_value(candidate["coefficients"]["b"]),
        str(candidate["id"]),
    )


def select_from_training(
    dataset: ObservationSet,
    split_certificate: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
    evidence: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(candidates) != len(evidence):
        raise ValueError("candidate and evidence counts differ")
    pairs = sorted(zip(candidates, evidence), key=lambda pair: training_rank(pair[0], pair[1]))
    exact = [
        (candidate, proof)
        for candidate, proof in pairs
        if proof["splits"]["train"]["metrics"]["exact"]
    ]
    selected: Mapping[str, Any] | None = None
    reason = ""
    if not pairs:
        reason = "no candidate can be derived from distinct training inputs"
    elif not exact:
        reason = "no candidate has zero residual on every training observation"
    elif len(exact) > 1 and dataset.acceptance_policy.require_unique_exact_train:
        reason = "multiple semantically distinct exact training candidates survive"
    else:
        selected = exact[0][0]
        reason = "unique exact training candidate selected without validation or holdout input"
    best = pairs[0][0] if pairs else None
    return attach_hash({
        "schema": SELECTION_SCHEMA,
        "profile": "TOM-LEARNER-0.1",
        "observation_set_id": dataset.id,
        "observation_set_hash": dataset.content_hash,
        "split_certificate_hash": split_certificate["content_hash"],
        "acceptance_policy_hash": dataset.acceptance_policy.content_hash,
        "selection_uses_splits": ["train"],
        "candidate_count": len(candidates),
        "exact_training_candidate_count": len(exact),
        "ranked_candidate_hashes": [candidate["content_hash"] for candidate, _ in pairs],
        "best_training_candidate_hash": None if best is None else best["content_hash"],
        "selected_candidate_hash": None if selected is None else selected["content_hash"],
        "selected_candidate_id": None if selected is None else selected["id"],
        "reason": reason,
    })


def find_contradictions(dataset: ObservationSet) -> list[dict[str, Any]]:
    grouped: dict[Q, list[Observation]] = defaultdict(list)
    for observation in dataset.observations:
        grouped[observation.t].append(observation)
    result: list[dict[str, Any]] = []
    for time, observations in grouped.items():
        outputs = sorted({observation.y for observation in observations})
        if len(outputs) <= 1:
            continue
        record = attach_hash({
            "schema": CONTRADICTION_SCHEMA,
            "profile": "TOM-LEARNER-0.1",
            "observation_set_id": dataset.id,
            "observation_set_hash": dataset.content_hash,
            "input": time.to_record(),
            "distinct_outputs": [value.to_record() for value in outputs],
            "observations": [
                {"id": item.id, "content_hash": item.content_hash, "y": item.y.to_record()}
                for item in sorted(observations, key=lambda item: item.id)
            ],
            "meaning": "the same exact input carries more than one exact output",
        })
        result.append(record)
    return result


def counterexamples_from_evidence(
    dataset: ObservationSet,
    evidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for split_name in SPLITS:
        for row in evidence["splits"][split_name]["residuals"]:
            value = Q.from_value(row["residual"])
            if value == Q(0):
                continue
            result.append(attach_hash({
                "schema": COUNTEREXAMPLE_SCHEMA,
                "profile": "TOM-LEARNER-0.1",
                "observation_set_id": dataset.id,
                "observation_set_hash": dataset.content_hash,
                "candidate_hash": evidence["candidate_hash"],
                "evidence_hash": evidence["content_hash"],
                "split": split_name,
                "observation_id": row["observation_id"],
                "observation_hash": row["observation_hash"],
                "t": row["t"],
                "observed_y": row["observed_y"],
                "predicted_y": row["predicted_y"],
                "residual": row["residual"],
            }))
    result.sort(key=lambda item: (SPLITS.index(item["split"]), item["observation_id"]))
    return result
