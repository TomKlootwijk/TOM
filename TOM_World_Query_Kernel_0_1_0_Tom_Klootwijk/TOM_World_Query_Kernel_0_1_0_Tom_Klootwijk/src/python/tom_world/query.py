"""Query-first world semantics over content-addressed records and TOMAGI."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from tomagi.core import (
    PHI_STATES,
    THETA_STATES,
    TIME_STATES,
    State,
    Program,
    STATUS_HALT,
    i32,
    mix32,
    norm_mod,
    run,
    step,
    u32,
)
from tomagi.format import loads

from .canonical import attach_hash, canonical_bytes, verify_hash
from .expression import ExpressionBudget, evaluate_expression
from .records import make_record
from .store import TRANSACTION_SCHEMA, WorldStore

_STATE_FIELDS = tuple(State.__dataclass_fields__)
_SIGNED_FIELDS = frozenset({
    "rho", "theta", "tick", "phi", "vrho", "vtheta", "vtick", "vphi", "residual",
})


def state_dict(state: State) -> dict[str, int]:
    return {name: getattr(state, name) for name in _STATE_FIELDS}


def state_from_mapping(value: Mapping[str, Any], *, base: State | None = None) -> State:
    fields = state_dict(base or State())
    unknown = sorted(set(value) - set(fields))
    if unknown:
        raise ValueError("unknown State64 fields: " + ", ".join(unknown))
    for name, raw in value.items():
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise TypeError(f"State64 field {name} must be an integer")
        fields[name] = i32(raw) if name in _SIGNED_FIELDS else u32(raw)
    return State(**fields)


def _record_sources(
    state: State,
    *,
    pre_state: State | None = None,
    context: Mapping[str, Any] | None = None,
    left: State | None = None,
    right: State | None = None,
    event: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "state": state_dict(state),
        "pre_state": state_dict(pre_state or state),
        "context": dict(context or {}),
    }
    if left is not None:
        result["left"] = state_dict(left)
    if right is not None:
        result["right"] = state_dict(right)
    if event is not None:
        result["event"] = dict(event)
    return result


def _zero_test(value: Any, mode: str) -> bool:
    if mode == "equal_zero":
        return isinstance(value, int) and not isinstance(value, bool) and value == 0
    if mode == "less_equal_zero":
        return isinstance(value, int) and not isinstance(value, bool) and value <= 0
    if mode == "contains_zero":
        if not isinstance(value, Mapping):
            raise TypeError("contains_zero relation must return an interval object")
        lower = value.get("lower")
        upper = value.get("upper")
        if isinstance(lower, bool) or not isinstance(lower, int) or isinstance(upper, bool) or not isinstance(upper, int):
            raise TypeError("interval bounds must be integers")
        return lower <= 0 <= upper
    raise ValueError(f"unsupported zero test {mode}")


def _triggered(previous: Any, current: Any, mode: str, zero_mode: str) -> bool:
    previous_zero = _zero_test(previous, zero_mode)
    current_zero = _zero_test(current, zero_mode)
    if mode == "zero":
        return current_zero
    if mode == "enter_zero":
        return current_zero and not previous_zero
    if mode == "enter_nonpositive":
        if not isinstance(previous, int) or isinstance(previous, bool) or not isinstance(current, int) or isinstance(current, bool):
            raise TypeError("enter_nonpositive requires integer residuals")
        return previous > 0 and current <= 0
    if mode == "crossing":
        if current_zero:
            return True
        if isinstance(previous, int) and not isinstance(previous, bool) and isinstance(current, int) and not isinstance(current, bool):
            return (previous < 0 < current) or (current < 0 < previous)
        return current_zero and not previous_zero
    raise ValueError(f"unsupported trigger mode {mode}")


def _direction(previous: Any, current: Any) -> str:
    if isinstance(previous, int) and not isinstance(previous, bool) and isinstance(current, int) and not isinstance(current, bool):
        if previous > 0 and current == 0:
            return "positive_to_zero"
        if previous < 0 and current == 0:
            return "negative_to_zero"
        if previous < 0 < current:
            return "negative_to_positive"
        if previous > 0 > current:
            return "positive_to_negative"
        if current > previous:
            return "increasing"
        if current < previous:
            return "decreasing"
        return "stationary"
    return "interval_or_symbolic"


def _guard_margin(previous: Any, current: Any) -> int | dict[str, int] | None:
    if isinstance(previous, int) and not isinstance(previous, bool) and isinstance(current, int) and not isinstance(current, bool):
        if current == 0:
            return abs(previous)
        return min(abs(previous), abs(current))
    if isinstance(current, Mapping) and isinstance(current.get("lower"), int) and isinstance(current.get("upper"), int):
        return {"lower": int(current["lower"]), "upper": int(current["upper"])}
    return None


class QueryEngine:
    """Native TOM-SRS queries for one immutable world commit.

    Version 0.1 implements exact discrete state evaluation and finite-horizon
    event scanning.  It does not claim a continuous root solver.
    """

    def __init__(
        self,
        store: WorldStore,
        *,
        commit: str | None = None,
        max_query_steps: int = 100_000,
        max_expression_nodes: int = 10_000,
        max_expression_depth: int = 64,
    ) -> None:
        store.validate()
        self.store = store
        self.commit = commit or store.head
        if self.commit is None:
            raise ValueError("query engine requires a committed world")
        self.commit_record = store.read_commit(self.commit)
        self.snapshot = store.read_snapshot(str(self.commit_record["snapshot_hash"]))
        self.max_query_steps = max_query_steps
        self.max_expression_nodes = max_expression_nodes
        self.max_expression_depth = max_expression_depth
        self._program_cache: dict[str, Program] = {}

    def _expression_budget(self) -> ExpressionBudget:
        return ExpressionBudget(self.max_expression_nodes, self.max_expression_depth)

    def definition_at(self, ident: str) -> dict[str, Any]:
        """Return an exact record from this commit's snapshot."""

        return self.store.read_record(ident, commit=self.commit)

    def verify_definition(self, ident: str) -> dict[str, Any]:
        result = self.store.verify_record(ident, commit=self.commit)
        if result.get("valid"):
            record = self.store.read_record(ident, commit=self.commit)
            result["is_definition"] = record["record_type"] == "definition"
            result["commit"] = self.commit
        return result

    def _instance(self, instance_id: str) -> dict[str, Any]:
        record = self.store.read_record(instance_id, commit=self.commit)
        if record["record_type"] != "instance":
            raise TypeError(f"{instance_id} is not an instance")
        return record

    def _program_for_instance(self, instance_id: str) -> tuple[Program, dict[str, Any]]:
        instance = self._instance(instance_id)
        blob_id = str(instance["payload"]["program_blob_id"])
        blob_index = self.snapshot["blobs"]
        if blob_id not in blob_index:
            raise ValueError(f"instance {instance_id} program blob is absent from snapshot: {blob_id}")
        blob_hash = str(blob_index[blob_id])
        if blob_hash not in self._program_cache:
            self._program_cache[blob_hash] = loads(self.store.read_blob(blob_hash))
        program = self._program_cache[blob_hash]
        override = instance["payload"].get("initial_state")
        if isinstance(override, Mapping):
            program = Program(
                cells=program.cells,
                entry=program.entry,
                seed=program.seed,
                default_ticks=program.default_ticks,
                initial_state=state_from_mapping(override, base=program.initial_state),
                flags=program.flags,
            )
        return program, instance

    def state_at(self, instance_id: str, tick: int, *, include_trace: bool = False) -> dict[str, Any]:
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("state_at tick must be a nonnegative integer")
        if tick > self.max_query_steps:
            raise ValueError(f"state_at tick exceeds query budget: {tick} > {self.max_query_steps}")
        program, instance = self._program_for_instance(instance_id)
        state, trace = run(program, ticks=tick, trace=True)
        result = {
            "schema": "TOM-STATE-AT-CERTIFICATE-0.1",
            "commit": self.commit,
            "instance_id": instance_id,
            "instance_hash": instance["content_hash"],
            "requested_tick": tick,
            "executed_steps": len(trace),
            "state": state_dict(state),
            "status": "exact_discrete_replay",
        }
        if include_trace:
            result["trace"] = trace
            result["executed_steps"] = len(trace)
        return attach_hash(result)

    def trace(self, instance_id: str, ticks: int) -> dict[str, Any]:
        return self.state_at(instance_id, ticks, include_trace=True)

    def _context(self, instance: Mapping[str, Any], context: Mapping[str, Any] | None) -> dict[str, Any]:
        base = instance["payload"].get("context", {})
        if not isinstance(base, Mapping):
            raise ValueError("instance context must be an object")
        merged = dict(base)
        if context:
            merged.update(context)
        return merged

    def _relation_records(self, instance_id: str, relation_ids: Sequence[str] | None) -> list[dict[str, Any]]:
        if relation_ids is None:
            relations = [
                record for record in self.store.list_records(commit=self.commit, record_type="relation")
                if record["payload"]["instance_id"] == instance_id
            ]
        else:
            relations = []
            for ident in relation_ids:
                record = self.store.read_record(ident, commit=self.commit)
                if record["record_type"] != "relation":
                    raise TypeError(f"{ident} is not a relation")
                if record["payload"]["instance_id"] != instance_id:
                    raise ValueError(f"relation {ident} targets a different instance")
                relations.append(record)
        relations.sort(key=lambda record: (int(record["payload"].get("priority", 0)), record["id"]))
        return relations

    def _predicate_decisions(
        self,
        ids: Iterable[str],
        expected_type: str,
        *,
        state: State,
        pre_state: State,
        context: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        decisions = []
        sources = _record_sources(state, pre_state=pre_state, context=context)
        for ident in ids:
            record = self.store.read_record(ident, commit=self.commit)
            if record["record_type"] != expected_type:
                raise TypeError(f"{ident} is not a {expected_type} record")
            value = evaluate_expression(record["payload"]["expression"], sources, budget=self._expression_budget())
            if not isinstance(value, bool):
                raise TypeError(f"{expected_type} {ident} expression did not return bool")
            decisions.append({
                "id": ident,
                "hash": record["content_hash"],
                "accepted": value,
            })
        return decisions

    def _evaluate_relation(
        self,
        record: Mapping[str, Any],
        *,
        state: State,
        pre_state: State,
        context: Mapping[str, Any],
    ) -> tuple[Any, Any, list[dict[str, Any]], list[dict[str, Any]]]:
        payload = record["payload"]
        previous_sources = _record_sources(pre_state, pre_state=pre_state, context=context)
        current_sources = _record_sources(state, pre_state=pre_state, context=context)
        previous = evaluate_expression(payload["expression"], previous_sources, budget=self._expression_budget())
        current = evaluate_expression(payload["expression"], current_sources, budget=self._expression_budget())
        supports = self._predicate_decisions(
            payload.get("support_ids", []), "support", state=state, pre_state=pre_state, context=context
        )
        compatibilities = self._predicate_decisions(
            payload.get("compatibility_ids", []), "compatibility", state=state, pre_state=pre_state, context=context
        )
        return previous, current, supports, compatibilities

    def _apply_transition(
        self,
        transition_id: str | None,
        state: State,
        *,
        pre_state: State,
        context: Mapping[str, Any],
        event_context: Mapping[str, Any],
    ) -> tuple[State, str | None]:
        if transition_id is None:
            return replace(state), None
        record = self.store.read_record(transition_id, commit=self.commit)
        if record["record_type"] != "transition":
            raise TypeError(f"{transition_id} is not a transition")
        result = replace(state)
        sources = _record_sources(result, pre_state=pre_state, context=context, event=event_context)
        for operation in ("set", "add", "xor"):
            fields = record["payload"].get(operation, {})
            for name in sorted(fields):
                if name not in _STATE_FIELDS:
                    raise ValueError(f"transition {transition_id} names unknown State64 field {name}")
                value = evaluate_expression(fields[name], sources, budget=self._expression_budget())
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError(f"transition {transition_id}.{operation}.{name} must evaluate to integer")
                current = getattr(result, name)
                if operation == "set":
                    updated = value
                elif operation == "add":
                    updated = current + value
                else:
                    updated = current ^ value
                setattr(result, name, i32(updated) if name in _SIGNED_FIELDS else u32(updated))
                sources["state"] = state_dict(result)
        if record["payload"].get("normalize_periodic", True):
            result.theta = norm_mod(result.theta, THETA_STATES)
            result.tick = norm_mod(result.tick, TIME_STATES)
            result.phi = norm_mod(result.phi, PHI_STATES)
            result.orientation &= 1
            result.branch &= 1
        salt = record["payload"].get("lineage_salt")
        if salt is not None:
            if isinstance(salt, bool) or not isinstance(salt, int):
                raise TypeError("transition lineage_salt must be an integer")
            relation_word = int(str(event_context["relation_hash"])[7:15], 16)
            result.lineage = mix32(result.lineage ^ u32(salt) ^ u32(event_context["event_tick"]) ^ relation_word)
        return result, str(record["content_hash"])

    def _event_certificate(
        self,
        *,
        instance: Mapping[str, Any],
        relation: Mapping[str, Any],
        after_tick: int,
        horizon: int,
        event_tick: int,
        pre_state: State,
        state: State,
        previous_residual: Any,
        residual: Any,
        support_decisions: list[dict[str, Any]],
        compatibility_decisions: list[dict[str, Any]],
        context: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = relation["payload"]
        event_spec_id = payload.get("event_spec_id")
        event_spec = None
        transition_id = None
        route = None
        confidence: Any = {"kind": "not_declared"}
        if event_spec_id is not None:
            event_spec = self.store.read_record(str(event_spec_id), commit=self.commit)
            if event_spec["record_type"] != "event_spec":
                raise TypeError(f"{event_spec_id} is not an event_spec")
            transition_id = event_spec["payload"].get("transition_id")
            route = event_spec["payload"].get("route")
            confidence = event_spec["payload"].get("confidence", confidence)
        event_context = {
            "event_tick": event_tick,
            "relation_id": relation["id"],
            "relation_hash": relation["content_hash"],
            "residual": residual,
            "previous_residual": previous_residual,
        }
        post_state, transition_hash = self._apply_transition(
            str(transition_id) if transition_id is not None else None,
            state,
            pre_state=pre_state,
            context=context,
            event_context=event_context,
        )
        certificate = {
            "schema": "TOM-EVENT-CERTIFICATE-0.1",
            "source_commit": self.commit,
            "query": {
                "instance_id": instance["id"],
                "after_tick": after_tick,
                "horizon": horizon,
                "relation_ids": [relation["id"]],
            },
            "instance_hash": instance["content_hash"],
            "event_tick": event_tick,
            "relation_id": relation["id"],
            "relation_hash": relation["content_hash"],
            "event_spec_id": event_spec_id,
            "event_spec_hash": event_spec["content_hash"] if event_spec else None,
            "transition_id": transition_id,
            "transition_hash": transition_hash,
            "previous_residual": previous_residual,
            "residual": residual,
            "zero_test": payload.get("zero_test", "equal_zero"),
            "trigger": payload.get("trigger", "enter_zero"),
            "direction": _direction(previous_residual, residual),
            "guard_margin": _guard_margin(previous_residual, residual),
            "support": support_decisions,
            "compatibility": compatibility_decisions,
            "solver_status": "exact_discrete_scan",
            "confidence": confidence,
            "route": route,
            "pre_state": state_dict(pre_state),
            "event_state": state_dict(state),
            "post_state": state_dict(post_state),
            "context": dict(context),
        }
        return attach_hash(certificate)

    def _scan_events(
        self,
        instance_id: str,
        *,
        after_tick: int,
        horizon: int,
        relation_ids: Sequence[str] | None,
        context: Mapping[str, Any] | None,
        stop_after_first: bool,
    ) -> list[dict[str, Any]]:
        if isinstance(after_tick, bool) or not isinstance(after_tick, int) or after_tick < 0:
            raise ValueError("after_tick must be a nonnegative integer")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            raise ValueError("horizon must be a positive integer")
        if after_tick + horizon > self.max_query_steps:
            raise ValueError(
                f"event scan exceeds query budget: {after_tick + horizon} > {self.max_query_steps}"
            )
        program, instance = self._program_for_instance(instance_id)
        relations = self._relation_records(instance_id, relation_ids)
        if not relations:
            return []
        merged_context = self._context(instance, context)
        state, _ = run(program, ticks=after_tick, trace=False)
        logical_tick = after_tick
        events: list[dict[str, Any]] = []
        for _ in range(horizon):
            pre_state = replace(state)
            if not (state.status & STATUS_HALT):
                step(program, state)
            logical_tick += 1
            candidates: list[dict[str, Any]] = []
            for relation in relations:
                previous, residual, supports, compatibilities = self._evaluate_relation(
                    relation,
                    state=state,
                    pre_state=pre_state,
                    context=merged_context,
                )
                support_ok = all(decision["accepted"] for decision in supports)
                compatibility_ok = all(decision["accepted"] for decision in compatibilities)
                payload = relation["payload"]
                if support_ok and compatibility_ok and _triggered(
                    previous,
                    residual,
                    str(payload.get("trigger", "enter_zero")),
                    str(payload.get("zero_test", "equal_zero")),
                ):
                    candidates.append(self._event_certificate(
                        instance=instance,
                        relation=relation,
                        after_tick=after_tick,
                        horizon=horizon,
                        event_tick=logical_tick,
                        pre_state=pre_state,
                        state=state,
                        previous_residual=previous,
                        residual=residual,
                        support_decisions=supports,
                        compatibility_decisions=compatibilities,
                        context=merged_context,
                    ))
            if candidates:
                candidates.sort(key=lambda certificate: (
                    int(self.store.read_record(certificate["relation_id"], commit=self.commit)["payload"].get("priority", 0)),
                    certificate["relation_id"],
                ))
                events.extend(candidates)
                if stop_after_first:
                    return [candidates[0]]
        return events

    def next_event(
        self,
        instance_id: str,
        after_tick: int,
        *,
        horizon: int = 1024,
        relation_ids: Sequence[str] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        events = self._scan_events(
            instance_id,
            after_tick=after_tick,
            horizon=horizon,
            relation_ids=relation_ids,
            context=context,
            stop_after_first=True,
        )
        return events[0] if events else None

    def events_in_support(
        self,
        instance_id: str,
        *,
        start_tick: int,
        end_tick: int,
        support_id: str | None = None,
        relation_ids: Sequence[str] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return events in ``(start_tick, end_tick]`` whose declared gates pass."""

        if end_tick <= start_tick:
            raise ValueError("end_tick must be greater than start_tick")
        selected_relations = relation_ids
        if support_id is not None:
            support_record = self.store.read_record(support_id, commit=self.commit)
            if support_record["record_type"] != "support":
                raise TypeError(f"{support_id} is not a support record")
            all_relations = self._relation_records(instance_id, relation_ids)
            selected_relations = [
                record["id"] for record in all_relations
                if support_id in record["payload"].get("support_ids", [])
            ]
        events = self._scan_events(
            instance_id,
            after_tick=start_tick,
            horizon=end_tick - start_tick,
            relation_ids=selected_relations,
            context=context,
            stop_after_first=False,
        )
        return attach_hash({
            "schema": "TOM-EVENTS-IN-SUPPORT-CERTIFICATE-0.1",
            "commit": self.commit,
            "instance_id": instance_id,
            "support_id": support_id,
            "interval": {"start_exclusive": start_tick, "end_inclusive": end_tick},
            "event_count": len(events),
            "events": events,
        })

    def compatible(
        self,
        left_instance_id: str,
        right_instance_id: str,
        compatibility_id: str,
        *,
        tick: int,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self.store.read_record(compatibility_id, commit=self.commit)
        if record["record_type"] != "compatibility":
            raise TypeError(f"{compatibility_id} is not a compatibility record")
        left_program, _ = self._program_for_instance(left_instance_id)
        right_program, _ = self._program_for_instance(right_instance_id)
        left, _ = run(left_program, ticks=tick, trace=False)
        right, _ = run(right_program, ticks=tick, trace=False)
        sources = _record_sources(left, left=left, right=right, context=context)
        value = evaluate_expression(record["payload"]["expression"], sources, budget=self._expression_budget())
        if not isinstance(value, bool):
            raise TypeError("compatibility expression must return bool")
        return attach_hash({
            "schema": "TOM-COMPATIBILITY-CERTIFICATE-0.1",
            "commit": self.commit,
            "compatibility_id": compatibility_id,
            "compatibility_hash": record["content_hash"],
            "left_instance_id": left_instance_id,
            "right_instance_id": right_instance_id,
            "tick": tick,
            "left_state": state_dict(left),
            "right_state": state_dict(right),
            "compatible": value,
            "context": dict(context or {}),
        })

    def reconstruct(self, certificate_or_lineage: Mapping[str, Any] | str) -> dict[str, Any]:
        if isinstance(certificate_or_lineage, str):
            record = self.store.read_record(certificate_or_lineage, commit=self.commit)
            if record["record_type"] not in {"event", "lineage"}:
                raise TypeError("reconstruct ID must refer to an event or lineage record")
            certificate = record["payload"].get("certificate")
            if not isinstance(certificate, Mapping):
                raise ValueError("event/lineage record has no embedded certificate")
        else:
            certificate = certificate_or_lineage
        if certificate.get("schema") != "TOM-EVENT-CERTIFICATE-0.1" or not verify_hash(certificate):
            raise ValueError("event certificate is invalid")
        source_commit = str(certificate["source_commit"])
        query = certificate["query"]
        engine = QueryEngine(
            self.store,
            commit=source_commit,
            max_query_steps=self.max_query_steps,
            max_expression_nodes=self.max_expression_nodes,
            max_expression_depth=self.max_expression_depth,
        )
        recomputed = engine.next_event(
            str(query["instance_id"]),
            int(query["after_tick"]),
            horizon=int(query["horizon"]),
            relation_ids=list(query["relation_ids"]),
            context=certificate.get("context", {}),
        )
        equal = recomputed is not None and canonical_bytes(recomputed) == canonical_bytes(certificate)
        return attach_hash({
            "schema": "TOM-RECONSTRUCTION-CERTIFICATE-0.1",
            "requested_certificate_hash": certificate["content_hash"],
            "source_commit": source_commit,
            "recomputed_certificate_hash": recomputed["content_hash"] if recomputed else None,
            "byte_equal": equal,
            "status": "reconstructed" if equal else "mismatch",
        })

    def event_records(self, certificate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if certificate.get("schema") != "TOM-EVENT-CERTIFICATE-0.1" or not verify_hash(certificate):
            raise ValueError("event certificate is invalid")
        suffix = str(certificate["content_hash"])[7:23]
        dependencies = [
            str(certificate["query"]["instance_id"]),
            str(certificate["relation_id"]),
        ]
        for field in ("event_spec_id", "transition_id"):
            value = certificate.get(field)
            if isinstance(value, str):
                dependencies.append(value)
        event_id = f"event:{suffix}"
        event_record = make_record(
            "event",
            event_id,
            {
                "certificate": dict(certificate),
                "event_tick": certificate["event_tick"],
                "relation_id": certificate["relation_id"],
                "route": certificate.get("route"),
            },
            dependencies=dependencies,
            provenance={"source_commit": certificate["source_commit"]},
        )
        lineage_id = f"lineage:{suffix}"
        lineage_record = make_record(
            "lineage",
            lineage_id,
            {
                "certificate": dict(certificate),
                "event_id": event_id,
                "parent_state_lineage": certificate["event_state"]["lineage"],
                "post_state_lineage": certificate["post_state"]["lineage"],
                "definition_hashes": {
                    "relation": certificate["relation_hash"],
                    "event_spec": certificate.get("event_spec_hash"),
                    "transition": certificate.get("transition_hash"),
                },
            },
            dependencies=[event_id],
            provenance={"source_commit": certificate["source_commit"]},
        )
        return event_record, lineage_record

    def commit_event(self, certificate: Mapping[str, Any], *, message: str = "commit verified event") -> dict[str, Any]:
        if certificate.get("source_commit") != self.store.head:
            raise ValueError("event certificate source commit must equal current HEAD")
        event_record, lineage_record = self.event_records(certificate)
        sequence = int(self.commit_record["sequence"]) + 1
        transaction = attach_hash({
            "schema": TRANSACTION_SCHEMA,
            "seed_sha256": self.commit_record["seed_sha256"],
            "base_commit": self.store.head,
            "sequence": sequence,
            "message": message,
            "records": [event_record, lineage_record],
            "blobs": [],
            "provenance": {"query_certificate": certificate["content_hash"]},
        })
        return self.store.commit_transaction(transaction)
