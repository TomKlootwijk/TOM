"""Deterministic observation-to-hypothesis pipeline for TOM Learner 0.1."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from tom_world03.canonical import attach_hash, canonical_bytes, require_hash
from tom_world03.rational import Q

from .affine import (
    candidate_coefficients,
    counterexamples_from_evidence,
    derive_candidates,
    evaluate_candidate,
    find_contradictions,
    select_from_training,
)
from .model import ObservationSet, PROFILE
from .split import deterministic_split

DECISION_SCHEMA = "TOM-LEARNER-ACCEPTANCE-DECISION-0.1"
CERTIFICATE_SCHEMA = "TOM-LEARNING-CERTIFICATE-0.1"
LEARNED_DEFINITION_SCHEMA = "TOM-LEARNED-AFFINE-DEFINITION-0.1"
REJECTION_LINEAGE_SCHEMA = "TOM-REJECTED-CANDIDATE-LINEAGE-0.1"


def _hash_values(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _selected_candidate(
    selection: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    selected_hash = selection.get("selected_candidate_hash")
    if selected_hash is None:
        return None
    for candidate in candidates:
        if candidate.get("content_hash") == selected_hash:
            return candidate
    raise ValueError("selection references a candidate absent from enumeration")


def _evidence_for(
    candidate: Mapping[str, Any] | None,
    candidates: list[Mapping[str, Any]],
    evidence: list[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    if candidate is None:
        return evidence[0] if evidence else None
    wanted = candidate["content_hash"]
    for item in evidence:
        if item.get("candidate_hash") == wanted:
            return item
    raise ValueError("selected candidate has no residual evidence")


def _decision(
    dataset: ObservationSet,
    split: Mapping[str, Any],
    selection: Mapping[str, Any],
    candidate: Mapping[str, Any] | None,
    evidence: Mapping[str, Any] | None,
    contradictions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            reasons.append(detail)

    counts = split["counts"]
    check("minimum training observations", int(counts["train"]) >= 2,
          "training split has fewer than two observations")
    check("minimum validation observations", int(counts["validation"]) >= 1,
          "validation split is empty")
    check("minimum holdout observations", int(counts["holdout"]) >= 1,
          "holdout split is empty")
    check("selected exact training candidate", candidate is not None,
          str(selection.get("reason", "no exact training candidate")))
    if candidate is not None:
        check("model complexity",
              int(candidate["complexity"]) <= dataset.acceptance_policy.max_model_complexity,
              "selected model exceeds the declared complexity budget")
    else:
        check("model complexity", False, "no selected model exists")

    if evidence is None:
        check("exact training residuals", False, "no residual evidence exists")
        check("exact validation residuals", False, "no validation residual evidence exists")
        check("exact holdout residuals", False, "no holdout residual evidence exists")
    else:
        train_exact = bool(evidence["splits"]["train"]["metrics"]["exact"])
        validation_exact = bool(evidence["splits"]["validation"]["metrics"]["exact"])
        holdout_exact = bool(evidence["splits"]["holdout"]["metrics"]["exact"])
        check("exact training residuals", train_exact,
              "selected/best candidate has a nonzero training residual")
        check("exact validation residuals",
              validation_exact or not dataset.acceptance_policy.require_exact_validation,
              "selected candidate has a nonzero validation residual")
        check("exact holdout residuals",
              holdout_exact or not dataset.acceptance_policy.require_exact_holdout,
              "selected candidate has a nonzero holdout residual")

    check("no exact-input contradictions",
          not contradictions or not dataset.acceptance_policy.reject_contradictions,
          "observation set contains contradictory exact outputs for one input")

    accepted = all(item["passed"] for item in checks)
    return attach_hash({
        "schema": DECISION_SCHEMA,
        "profile": PROFILE,
        "observation_set_id": dataset.id,
        "observation_set_hash": dataset.content_hash,
        "split_certificate_hash": split["content_hash"],
        "acceptance_policy_hash": dataset.acceptance_policy.content_hash,
        "selection_certificate_hash": selection["content_hash"],
        "selected_candidate_hash": None if candidate is None else candidate["content_hash"],
        "evidence_hash": None if evidence is None else evidence["content_hash"],
        "contradiction_hashes": [item["content_hash"] for item in contradictions],
        "checks": checks,
        "accepted": accepted,
        "reasons": reasons,
        "policy_boundary": {
            "fit_and_selection_splits": ["train"],
            "validation_role": "acceptance gate only",
            "holdout_role": "final acceptance audit only",
        },
    })


def _learned_definition(
    dataset: ObservationSet,
    candidate: Mapping[str, Any],
    certificate_hash: str,
) -> dict[str, Any]:
    a, b = candidate_coefficients(candidate)
    suffix = hashlib.sha256(canonical_bytes({
        "dataset": dataset.id,
        "candidate": candidate["content_hash"],
    })).hexdigest()[:24]
    return attach_hash({
        "schema": LEARNED_DEFINITION_SCHEMA,
        "profile": PROFILE,
        "id": f"definition:learned-affine:{suffix}",
        "kind": "learned-exact-affine-relation",
        "domain": {
            "input": dataset.input_name,
            "output": dataset.output_name,
            "numeric": "exact-rational",
        },
        "codomain": "exact-rational-residual",
        "relation_interface": "SDF0@Def",
        "model": "y=a*t+b",
        "coefficients": {"a": a.to_record(), "b": b.to_record()},
        "expression": {
            "op": "sub",
            "args": [
                {"op": "field", "name": dataset.output_name},
                {
                    "op": "add",
                    "args": [
                        {
                            "op": "mul",
                            "args": [
                                {"op": "const", "value": a.to_record()},
                                {"op": "field", "name": dataset.input_name},
                            ],
                        },
                        {"op": "const", "value": b.to_record()},
                    ],
                },
            ],
        },
        "zero_locus": f"{dataset.output_name} = a*{dataset.input_name} + b",
        "source_observation_set_hash": dataset.content_hash,
        "source_candidate_hash": candidate["content_hash"],
        "source_learning_certificate_hash": certificate_hash,
        "base_world_hash": dataset.base_world_hash,
        "base_handoff_hash": dataset.base_handoff_hash,
        "provenance": {
            "class": "deterministically-induced-and-held-out-verified",
            "learner": PROFILE,
        },
    })


@dataclass(frozen=True, slots=True)
class LearningRun:
    dataset: ObservationSet
    split_certificate: Mapping[str, Any]
    candidates: tuple[Mapping[str, Any], ...]
    enumeration: Mapping[str, Any]
    evidence: tuple[Mapping[str, Any], ...]
    selection: Mapping[str, Any]
    contradictions: tuple[Mapping[str, Any], ...]
    counterexamples: tuple[Mapping[str, Any], ...]
    decision: Mapping[str, Any]
    certificate: Mapping[str, Any]
    learned_definition: Mapping[str, Any] | None
    rejection_lineage: Mapping[str, Any] | None

    @property
    def accepted(self) -> bool:
        return bool(self.decision["accepted"])

    def all_records(self) -> list[Mapping[str, Any]]:
        values: list[Mapping[str, Any]] = [
            *self.dataset.source_records(),
            self.split_certificate,
            *self.candidates,
            self.enumeration,
            *self.evidence,
            self.selection,
            *self.contradictions,
            *self.counterexamples,
            self.decision,
            self.certificate,
        ]
        if self.learned_definition is not None:
            values.append(self.learned_definition)
        if self.rejection_lineage is not None:
            values.append(self.rejection_lineage)
        return values

    def summary(self) -> dict[str, Any]:
        candidate = self.learned_definition
        return {
            "observation_set_id": self.dataset.id,
            "observation_set_hash": self.dataset.content_hash,
            "accepted": self.accepted,
            "selected_candidate_hash": self.selection.get("selected_candidate_hash"),
            "learned_definition_hash": None if candidate is None else candidate["content_hash"],
            "candidate_count": len(self.candidates),
            "counterexample_count": len(self.counterexamples),
            "contradiction_count": len(self.contradictions),
            "decision_hash": self.decision["content_hash"],
            "certificate_hash": self.certificate["content_hash"],
        }


def learn_observation_set(dataset: ObservationSet) -> LearningRun:
    split = deterministic_split(dataset)
    candidates, enumeration = derive_candidates(dataset, split)
    evidence = [evaluate_candidate(dataset, split, candidate) for candidate in candidates]
    selection = select_from_training(dataset, split, candidates, evidence)
    selected = _selected_candidate(selection, candidates)
    selected_evidence = _evidence_for(selected, candidates, evidence)
    contradictions = find_contradictions(dataset)
    counterexamples = [] if selected_evidence is None else counterexamples_from_evidence(dataset, selected_evidence)
    decision = _decision(dataset, split, selection, selected, selected_evidence, contradictions)

    certificate = attach_hash({
        "schema": CERTIFICATE_SCHEMA,
        "profile": PROFILE,
        "observation_set_id": dataset.id,
        "observation_set_hash": dataset.content_hash,
        "base_world_hash": dataset.base_world_hash,
        "base_handoff_hash": dataset.base_handoff_hash,
        "split_certificate_hash": split["content_hash"],
        "assignment_basis_hash": split["assignment_basis_hash"],
        "candidate_enumeration_hash": enumeration["content_hash"],
        "fit_input_hash": enumeration["fit_input_hash"],
        "selection_certificate_hash": selection["content_hash"],
        "selected_candidate_hash": selection.get("selected_candidate_hash"),
        "selected_evidence_hash": None if selected_evidence is None else selected_evidence["content_hash"],
        "contradiction_hashes": [item["content_hash"] for item in contradictions],
        "counterexample_hashes": [item["content_hash"] for item in counterexamples],
        "acceptance_decision_hash": decision["content_hash"],
        "accepted": decision["accepted"],
        "phase_trace": [
            "parse-observations",
            "deterministic-id-only-split",
            "fit-train-only",
            "select-train-only",
            "validation-gate",
            "holdout-audit",
            "contradiction-gate",
            "candidate-certificate",
        ],
        "causal_boundary": "certificate is a proposal record; it is not authoritative world state",
    })

    learned_definition = None
    rejection_lineage = None
    if decision["accepted"]:
        if selected is None:
            raise AssertionError("accepted decision has no selected candidate")
        learned_definition = _learned_definition(dataset, selected, certificate["content_hash"])
    else:
        rejection_lineage = attach_hash({
            "schema": REJECTION_LINEAGE_SCHEMA,
            "profile": PROFILE,
            "observation_set_id": dataset.id,
            "observation_set_hash": dataset.content_hash,
            "learning_certificate_hash": certificate["content_hash"],
            "acceptance_decision_hash": decision["content_hash"],
            "candidate_hashes": [candidate["content_hash"] for candidate in candidates],
            "counterexample_hashes": [item["content_hash"] for item in counterexamples],
            "contradiction_hashes": [item["content_hash"] for item in contradictions],
            "reasons": list(decision["reasons"]),
            "retention": "rejected candidates and counterexamples remain in append-only lineage",
        })

    return LearningRun(
        dataset=dataset,
        split_certificate=split,
        candidates=tuple(candidates),
        enumeration=enumeration,
        evidence=tuple(evidence),
        selection=selection,
        contradictions=tuple(contradictions),
        counterexamples=tuple(counterexamples),
        decision=decision,
        certificate=certificate,
        learned_definition=learned_definition,
        rejection_lineage=rejection_lineage,
    )
