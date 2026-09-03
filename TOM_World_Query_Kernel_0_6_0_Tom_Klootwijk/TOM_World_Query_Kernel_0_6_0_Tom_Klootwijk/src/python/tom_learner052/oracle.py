"""Independent reference oracle for TOM Learner 0.1 promotion authority 0.5.2.

This module is deliberately not the authority.  The authoritative semantics are
``examples/learner052/promotion_authority.formal.json`` evaluated inside the
seeded TOMAGI definition graph.  The oracle is a separately written ordinary
Python reconstruction used to detect formal-program mistakes.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence


class OracleError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def address(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def addressed(body: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(body))
    if "content_hash" in result:
        raise OracleError("addressed body must not already contain content_hash")
    result["content_hash"] = address(result)
    return result


def verify_addressed(record: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise OracleError(f"{label} must be an object")
    value = copy.deepcopy(dict(record))
    claimed = value.pop("content_hash", None)
    if claimed != address(value):
        raise OracleError(f"{label} content hash mismatch")
    value["content_hash"] = claimed
    return value


def _write(namespace: str, record: Mapping[str, Any]) -> dict[str, Any]:
    return {"namespace": namespace, "record": copy.deepcopy(dict(record))}


def _unique(values: Sequence[str], label: str) -> list[str]:
    result = list(values)
    if len(result) != len(set(result)):
        raise OracleError(f"{label} must be unique")
    return result


def _dataset_map(datasets: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, dataset in enumerate(datasets):
        checked = verify_addressed(dataset, f"dataset {index}")
        ident = checked.get("id")
        if not isinstance(ident, str) or not ident:
            raise OracleError("dataset id must be a non-empty string")
        if ident in result:
            raise OracleError(f"duplicate dataset id {ident}")
        result[ident] = checked
    return result


def build_promotion_result(
    promotion_program: Mapping[str, Any],
    learner_program: Mapping[str, Any],
    learner_execution: Mapping[str, Any],
    datasets: Sequence[Mapping[str, Any]],
    context: Mapping[str, Any],
    corrective_handoff: Mapping[str, Any],
    token_registry: Mapping[str, Any],
) -> dict[str, Any]:
    promotion_program = verify_addressed(promotion_program, "promotion program")
    learner_program = verify_addressed(learner_program, "learner program")
    learner_execution = verify_addressed(learner_execution, "learner execution")
    learner_value = verify_addressed(learner_execution["value"], "learner value")
    context = verify_addressed(context, "promotion context")
    corrective_handoff = verify_addressed(corrective_handoff, "corrective handoff")
    token_registry = verify_addressed(token_registry, "token registry")
    datasets_by_id = _dataset_map(datasets)

    if context.get("profile") != "TOM-LEARNER-0.1-PROMOTION-AUTHORITY":
        raise OracleError("promotion context profile mismatch")
    if context.get("canonical_seed_sha256") != "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5":
        raise OracleError("promotion context seed mismatch")
    if corrective_handoff["content_hash"] != context.get("corrective_handoff_content_hash"):
        raise OracleError("corrective handoff mismatch")
    if token_registry["content_hash"] != context.get("token_registry_content_hash"):
        raise OracleError("token registry mismatch")
    if learner_program["content_hash"] != context.get("expected_learner_program_content_hash"):
        raise OracleError("learner program binding mismatch")
    if learner_execution.get("program_hash") != learner_program["content_hash"]:
        raise OracleError("learner execution program binding mismatch")
    if learner_execution["content_hash"] != context.get("expected_learner_execution_content_hash"):
        raise OracleError("learner execution identity mismatch")
    if learner_value["content_hash"] != context.get("expected_learner_value_content_hash"):
        raise OracleError("learner value identity mismatch")

    rows = learner_value.get("results")
    if not isinstance(rows, list):
        raise OracleError("learner result rows must be an array")
    if len(datasets) != context.get("expected_dataset_count") or len(rows) != len(datasets):
        raise OracleError("dataset/result count mismatch")
    bindings = [{"id": d["id"], "content_hash": d["content_hash"]} for d in datasets]
    if bindings != learner_value.get("inputs"):
        raise OracleError("literal dataset order differs from learner bindings")
    if learner_value.get("accepted_count") != context.get("expected_accepted_count"):
        raise OracleError("accepted count mismatch")
    if learner_value.get("rejected_count") != context.get("expected_rejected_count"):
        raise OracleError("rejected count mismatch")

    shared_objects = [
        promotion_program,
        learner_program,
        learner_execution,
        learner_value,
        context,
        corrective_handoff,
        token_registry,
    ]
    shared_hashes = _unique([x["content_hash"] for x in shared_objects], "shared authority hashes")

    descriptor = addressed({
        "schema": "TOMAGI-IMMUTABLE-STORE-DESCRIPTOR-1.0",
        "profile": context["profile"],
        "seed_sha256": context["canonical_seed_sha256"],
        "base_world_hash": context["base_world_hash"],
        "base_handoff_hash": context["base_handoff_hash"],
        "corrective_handoff_hash": context["corrective_handoff_content_hash"],
        "namespaces": copy.deepcopy(context["store_namespaces"]),
        "head_namespace": context["head_namespace"],
        "record_encoding": context["record_encoding"],
        "publication_rule": context["publication_rule"],
    })
    snapshot = addressed({
        "schema": "TOM-LEARNER-PROMOTION-SNAPSHOT-0.5.2",
        "profile": context["profile"],
        "base_world_hash": context["base_world_hash"],
        "base_handoff_hash": context["base_handoff_hash"],
        "corrective_handoff_hash": context["corrective_handoff_content_hash"],
        "accepted_definitions": {},
        "sessions": [],
        "accepted_sessions": [],
        "rejected_sessions": [],
    })
    genesis_transaction = addressed({
        "schema": "TOM-LEARNER-PROMOTION-GENESIS-TRANSACTION-0.5.2",
        "profile": context["profile"],
        "sequence": 0,
        "parent_commit_hash": None,
        "base_world_hash": context["base_world_hash"],
        "base_handoff_hash": context["base_handoff_hash"],
        "corrective_handoff_hash": context["corrective_handoff_content_hash"],
        "seed_sha256": context["canonical_seed_sha256"],
        "snapshot_hash": snapshot["content_hash"],
        "authority_program_hash": promotion_program["content_hash"],
    })
    head = addressed({
        "schema": "TOM-LEARNER-PROMOTION-COMMIT-0.5.2",
        "profile": context["profile"],
        "sequence": 0,
        "parent_commit_hash": None,
        "transaction_hash": genesis_transaction["content_hash"],
        "snapshot_hash": snapshot["content_hash"],
        "authority_program_hash": promotion_program["content_hash"],
    })
    genesis_writes = [_write("objects", x) for x in shared_objects] + [
        _write("snapshots", snapshot),
        _write("transactions", genesis_transaction),
        _write("commits", head),
    ]
    genesis_required = shared_hashes + [
        snapshot["content_hash"],
        genesis_transaction["content_hash"],
        head["content_hash"],
    ]
    publications = [addressed({
        "schema": "TOMAGI-IMMUTABLE-PUBLICATION-1.0",
        "profile": context["profile"],
        "sequence": 0,
        "expected_head": None,
        "replacement_head": head["content_hash"],
        "required_hashes": genesis_required,
        "writes": genesis_writes,
    })]

    seen_sessions: set[str] = set()
    for row_index, row_value in enumerate(rows):
        row = verify_addressed(row_value, f"learner result row {row_index}")
        dataset_id = row.get("dataset_id")
        if dataset_id not in datasets_by_id:
            raise OracleError(f"learner result row names unknown dataset {dataset_id!r}")
        if dataset_id in seen_sessions:
            raise OracleError(f"duplicate promotion session {dataset_id}")
        seen_sessions.add(dataset_id)
        dataset = datasets_by_id[dataset_id]
        if row.get("dataset_content_hash") != dataset["content_hash"]:
            raise OracleError("result row dataset hash differs from literal source")

        split_policy = verify_addressed(dataset["split_policy"], "split policy")
        hypothesis_family = verify_addressed(dataset["hypothesis_family"], "hypothesis family")
        acceptance_policy = verify_addressed(dataset["acceptance_policy"], "acceptance policy")
        observations = [
            verify_addressed(observation, f"observation {index}")
            for index, observation in enumerate(dataset["observations"])
        ]
        accepted = row.get("accepted")
        if not isinstance(accepted, bool):
            raise OracleError("accepted must be boolean")
        relation_value = row.get("relation_definition")
        if accepted:
            if not isinstance(relation_value, Mapping):
                raise OracleError("accepted row has no relation definition")
            authority_object = verify_addressed(relation_value, "accepted relation")
            rejection_lineage = None
        else:
            if relation_value is not None:
                raise OracleError("rejected row emitted a relation definition")
            rejection_lineage = addressed({
                "schema": "TOM-LEARNER-REJECTION-LINEAGE-0.5.2",
                "profile": context["profile"],
                "dataset_id": dataset_id,
                "dataset_content_hash": dataset["content_hash"],
                "result_row_hash": row["content_hash"],
                "reasons": copy.deepcopy(row["acceptance_reasons"]),
                "expected_parent_commit_hash": head["content_hash"],
                "learner_result_hash": learner_execution["content_hash"],
                "authority_program_hash": promotion_program["content_hash"],
            })
            authority_object = rejection_lineage

        decision = addressed({
            "schema": "TOM-LEARNER-PROMOTION-DECISION-0.5.2",
            "profile": context["profile"],
            "dataset_id": dataset_id,
            "dataset_content_hash": dataset["content_hash"],
            "result_row_hash": row["content_hash"],
            "accepted": accepted,
            "reasons": copy.deepcopy(row["acceptance_reasons"]),
            "published_definition_hash": authority_object["content_hash"] if accepted else None,
            "rejection_lineage_hash": None if accepted else authority_object["content_hash"],
            "expected_parent_commit_hash": head["content_hash"],
            "learner_program_hash": learner_program["content_hash"],
            "learner_result_hash": learner_execution["content_hash"],
            "authority_program_hash": promotion_program["content_hash"],
        })
        dataset_objects = [dataset, split_policy, hypothesis_family, acceptance_policy, *observations]
        pre_certificate_objects = [*dataset_objects, row, decision, authority_object]
        pre_certificate_hashes = _unique(
            [*shared_hashes, *[item["content_hash"] for item in pre_certificate_objects]],
            "supporting evidence hashes",
        )
        certificate = addressed({
            "schema": "TOM-LEARNER-PROMOTION-CERTIFICATE-0.5.2",
            "profile": context["profile"],
            "sequence": len(publications),
            "dataset_id": dataset_id,
            "dataset_content_hash": dataset["content_hash"],
            "expected_parent_commit_hash": head["content_hash"],
            "result_row_hash": row["content_hash"],
            "decision_hash": decision["content_hash"],
            "accepted": accepted,
            "published_definition_hash": authority_object["content_hash"] if accepted else None,
            "rejection_lineage_hash": None if accepted else authority_object["content_hash"],
            "supporting_evidence_hashes": pre_certificate_hashes,
            "authority_rule": context["authority_statement"],
        })
        evidence_objects = [*pre_certificate_objects, certificate]
        evidence_hashes = [*pre_certificate_hashes, certificate["content_hash"]]

        accepted_definitions = copy.deepcopy(snapshot["accepted_definitions"])
        accepted_sessions = copy.deepcopy(snapshot["accepted_sessions"])
        rejected_sessions = copy.deepcopy(snapshot["rejected_sessions"])
        if accepted:
            accepted_definitions[dataset_id] = authority_object["content_hash"]
            accepted_sessions.append(certificate["content_hash"])
        else:
            rejected_sessions.append(authority_object["content_hash"])
        new_snapshot = addressed({
            "schema": "TOM-LEARNER-PROMOTION-SNAPSHOT-0.5.2",
            "profile": context["profile"],
            "base_world_hash": context["base_world_hash"],
            "base_handoff_hash": context["base_handoff_hash"],
            "corrective_handoff_hash": context["corrective_handoff_content_hash"],
            "accepted_definitions": accepted_definitions,
            "sessions": [*snapshot["sessions"], dataset_id],
            "accepted_sessions": accepted_sessions,
            "rejected_sessions": rejected_sessions,
        })
        transaction = addressed({
            "schema": "TOM-LEARNER-PROMOTION-TRANSACTION-0.5.2",
            "profile": context["profile"],
            "sequence": len(publications),
            "expected_parent_commit_hash": head["content_hash"],
            "parent_commit_hash": head["content_hash"],
            "parent_snapshot_hash": snapshot["content_hash"],
            "base_world_hash": context["base_world_hash"],
            "base_handoff_hash": context["base_handoff_hash"],
            "corrective_handoff_hash": context["corrective_handoff_content_hash"],
            "observation_set_id": dataset_id,
            "observation_set_hash": dataset["content_hash"],
            "learner_program_hash": learner_program["content_hash"],
            "learner_result_hash": learner_execution["content_hash"],
            "result_row_hash": row["content_hash"],
            "acceptance_decision_hash": decision["content_hash"],
            "promotion_certificate_hash": certificate["content_hash"],
            "evidence_record_hashes": evidence_hashes,
            "accepted": accepted,
            "published_definition_hash": authority_object["content_hash"] if accepted else None,
            "rejection_lineage_hash": None if accepted else authority_object["content_hash"],
            "new_snapshot_hash": new_snapshot["content_hash"],
            "authority_program_hash": promotion_program["content_hash"],
            "authority_rule": context["authority_statement"],
        })
        new_head = addressed({
            "schema": "TOM-LEARNER-PROMOTION-COMMIT-0.5.2",
            "profile": context["profile"],
            "sequence": len(publications),
            "parent_commit_hash": head["content_hash"],
            "transaction_hash": transaction["content_hash"],
            "snapshot_hash": new_snapshot["content_hash"],
            "authority_program_hash": promotion_program["content_hash"],
        })
        writes = [_write("objects", item) for item in evidence_objects] + [
            _write("snapshots", new_snapshot),
            _write("transactions", transaction),
            _write("commits", new_head),
        ]
        required_hashes = _unique(
            [*evidence_hashes, new_snapshot["content_hash"], transaction["content_hash"], new_head["content_hash"]],
            "publication required hashes",
        )
        publication = addressed({
            "schema": "TOMAGI-IMMUTABLE-PUBLICATION-1.0",
            "profile": context["profile"],
            "sequence": len(publications),
            "expected_head": head["content_hash"],
            "replacement_head": new_head["content_hash"],
            "required_hashes": required_hashes,
            "writes": writes,
        })
        publications.append(publication)
        snapshot = new_snapshot
        head = new_head

    plan = addressed({
        "schema": "TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.0",
        "profile": context["profile"],
        "store_descriptor": descriptor,
        "publications": publications,
        "terminal_head": head["content_hash"],
    })
    return addressed({
        "schema": "TOM-LEARNER-PROMOTION-AUTHORITY-RESULT-0.5.2",
        "profile": context["profile"],
        "authority_program_hash": promotion_program["content_hash"],
        "learner_program_hash": learner_program["content_hash"],
        "learner_result_hash": learner_execution["content_hash"],
        "learner_value_hash": learner_value["content_hash"],
        "context_hash": context["content_hash"],
        "corrective_handoff_hash": corrective_handoff["content_hash"],
        "token_registry_hash": token_registry["content_hash"],
        "dataset_count": len(datasets),
        "accepted_count": learner_value["accepted_count"],
        "rejected_count": learner_value["rejected_count"],
        "publication_count": len(publications),
        "terminal_head": head["content_hash"],
        "terminal_snapshot_hash": snapshot["content_hash"],
        "publication_plan": plan,
        "claim_boundary": "exact finite affine promotion/evidence transaction authority only; no broader learner family or AGI claim",
    })


__all__ = [
    "OracleError",
    "address",
    "addressed",
    "build_promotion_result",
    "canonical_bytes",
    "verify_addressed",
]
