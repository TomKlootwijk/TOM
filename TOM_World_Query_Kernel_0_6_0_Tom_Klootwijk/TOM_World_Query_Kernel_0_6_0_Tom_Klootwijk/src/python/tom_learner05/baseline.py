"""Independent ``fractions.Fraction`` baseline for TOM Learner 0.1.

This module intentionally does not import learner fitting, split, model, or
selection code.  It reimplements the literal profile from raw JSON records so
agreement is meaningful rather than a second call into the implementation
under test.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations
import hashlib
import json
from typing import Any, Mapping

SPLITS = ("train", "validation", "holdout")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _attach(record: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out.pop("content_hash", None)
    out["content_hash"] = "sha256:" + hashlib.sha256(_canonical(out)).hexdigest()
    return out


def _f(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        return Fraction(int(value), 1)
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, Mapping):
        return Fraction(int(value["num"]), int(value["den"]))
    raise TypeError(f"cannot convert {type(value).__name__} to Fraction")


def _q(value: Fraction) -> dict[str, int]:
    return {"num": value.numerator, "den": value.denominator}


def _counts(record: Mapping[str, Any]) -> dict[str, int]:
    observations = record["observations"]
    policy = record["split_policy"]
    n = len(observations)
    minima = {name: int(policy["minimum_counts"][name]) for name in SPLITS}
    remaining = n - sum(minima.values())
    if remaining < 0:
        raise ValueError("baseline split minimum exceeds observation count")
    ratios = {name: int(policy["ratios"][name]) for name in SPLITS}
    total = sum(ratios.values())
    floors: dict[str, int] = {}
    remainders: dict[str, int] = {}
    for name in SPLITS:
        floors[name], remainders[name] = divmod(remaining * ratios[name], total)
    leftover = remaining - sum(floors.values())
    order = sorted(SPLITS, key=lambda name: (-remainders[name], SPLITS.index(name)))
    extra = {name: int(name in order[:leftover]) for name in SPLITS}
    return {name: minima[name] + floors[name] + extra[name] for name in SPLITS}


def _digest(record: Mapping[str, Any], observation_id: str) -> str:
    policy = record["split_policy"]
    basis = {
        "seed_sha256": record["seed_sha256"],
        "observation_set_id": record["id"],
        "split_policy_hash": policy["content_hash"],
        "salt": policy["salt"],
        "observation_id": observation_id,
    }
    return hashlib.sha256(_canonical(basis)).hexdigest()


def _split(record: Mapping[str, Any]) -> dict[str, list[str]]:
    counts = _counts(record)
    ordered = sorted((_digest(record, item["id"]), item["id"]) for item in record["observations"])
    result = {name: [] for name in SPLITS}
    cursor = 0
    for name in SPLITS:
        stop = cursor + counts[name]
        result[name] = sorted(ident for _, ident in ordered[cursor:stop])
        cursor = stop
    return result


def _complexity(value: Fraction) -> int:
    return (1 if value.numerator < 0 else 0) + max(1, abs(value.numerator).bit_length()) + value.denominator.bit_length()


def trusted_affine_learning_baseline(record: Mapping[str, Any]) -> dict[str, Any]:
    """Fit and gate one raw observation-set record independently."""

    observations = {item["id"]: item for item in record["observations"]}
    splits = _split(record)
    train = [observations[ident] for ident in splits["train"]]
    candidate_pairs: dict[tuple[Fraction, Fraction], set[tuple[str, str]]] = {}
    for left, right in combinations(sorted(train, key=lambda item: item["id"]), 2):
        lt, rt = _f(left["t"]), _f(right["t"])
        if lt == rt:
            continue
        ly, ry = _f(left["y"]), _f(right["y"])
        a = (ry - ly) / (rt - lt)
        b = ly - a * lt
        candidate_pairs.setdefault((a, b), set()).add(tuple(sorted((left["id"], right["id"]))))

    def residuals(coeff: tuple[Fraction, Fraction], split: str) -> list[Fraction]:
        a, b = coeff
        return [
            _f(observations[ident]["y"]) - (a * _f(observations[ident]["t"]) + b)
            for ident in splits[split]
        ]

    def rank(coeff: tuple[Fraction, Fraction]) -> tuple[Any, ...]:
        values = residuals(coeff, "train")
        absolute = [abs(value) for value in values]
        return (
            sum(value != 0 for value in values),
            max(absolute, default=Fraction(0)),
            sum(absolute, Fraction(0)),
            _complexity(coeff[0]) + _complexity(coeff[1]) + int(coeff[0] != 0) + int(coeff[1] != 0),
            coeff[0], coeff[1],
        )

    candidates = sorted(candidate_pairs, key=rank)
    exact = [coeff for coeff in candidates if all(value == 0 for value in residuals(coeff, "train"))]
    selected = exact[0] if len(exact) == 1 else None

    contradictions: list[dict[str, Any]] = []
    by_time: dict[Fraction, list[Mapping[str, Any]]] = {}
    for observation in record["observations"]:
        by_time.setdefault(_f(observation["t"]), []).append(observation)
    for time, items in sorted(by_time.items()):
        outputs = sorted({_f(item["y"]) for item in items})
        if len(outputs) > 1:
            contradictions.append({
                "t": _q(time),
                "outputs": [_q(value) for value in outputs],
                "ids": sorted(item["id"] for item in items),
            })

    policy = record["acceptance_policy"]
    accepted = selected is not None
    if selected is not None:
        complexity = _complexity(selected[0]) + _complexity(selected[1]) + int(selected[0] != 0) + int(selected[1] != 0)
        accepted &= complexity <= int(policy["max_model_complexity"])
        accepted &= all(value == 0 for value in residuals(selected, "train"))
        if policy["require_exact_validation"]:
            accepted &= all(value == 0 for value in residuals(selected, "validation"))
        if policy["require_exact_holdout"]:
            accepted &= all(value == 0 for value in residuals(selected, "holdout"))
    if policy["reject_contradictions"]:
        accepted &= not contradictions

    residual_summary: dict[str, Any] = {}
    if selected is not None:
        for name in SPLITS:
            values = residuals(selected, name)
            residual_summary[name] = {
                "count": len(values),
                "nonzero_count": sum(value != 0 for value in values),
                "max_abs_residual": _q(max((abs(value) for value in values), default=Fraction(0))),
            }

    semantic = {
        "schema": "TOM-INDEPENDENT-AFFINE-LEARNING-SEMANTIC-0.1",
        "observation_set_id": record["id"],
        "observation_set_hash": record["content_hash"],
        "splits": splits,
        "candidate_count": len(candidates),
        "exact_training_candidate_count": len(exact),
        "selected_coefficients": None if selected is None else {"a": _q(selected[0]), "b": _q(selected[1])},
        "residual_summary": residual_summary,
        "contradictions": contradictions,
        "accepted": bool(accepted),
    }
    return _attach({
        "schema": "TOM-INDEPENDENT-AFFINE-LEARNING-BASELINE-0.1",
        "implementation": "standalone fractions.Fraction pair-enumeration learner",
        "semantic": semantic,
        "semantic_sha256": "sha256:" + hashlib.sha256(_canonical(semantic)).hexdigest(),
    })
