"""Query-first world semantics over content-addressed records and TOMAGI.

World & Query Kernel 0.2 adds immutable-index planning, checkpoint-aware state
replay, and deterministic batch certificates while preserving the 0.1 semantic
query results and exact-discrete event model.
"""
from __future__ import annotations

from dataclasses import replace
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

from .canonical import attach_hash, canonical_bytes, digest_bytes, verify_hash
from .expression import ExpressionBudget, evaluate_expression
from .planner import PLANNER_MODES, QueryPlanner, make_plan
from .records import make_record, validate_record
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
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("equal_zero relation must return an integer")
        return value == 0
    if mode == "less_equal_zero":
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("less_equal_zero relation must return an integer")
        return value <= 0
    if mode == "contains_zero":
        if not isinstance(value, Mapping):
            raise TypeError("contains_zero relation must return an interval object")
        lower = value.get("lower")
        upper = value.get("upper")
        if isinstance(lower, bool) or not isinstance(lower, int) or isinstance(upper, bool) or not isinstance(upper, int):
            raise TypeError("interval bounds must be integers")
        if lower > upper:
            raise ValueError("interval lower bound must not exceed upper bound")
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


def _length_prefixed(values: Sequence[Any]) -> bytes:
    output = bytearray()
    for value in values:
        data = canonical_bytes(value)
        output.extend(len(data).to_bytes(8, "little"))
        output.extend(data)
    return bytes(output)


def _merge_work(*values: Mapping[str, Any]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for work in values:
        for key, raw in work.items():
            if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
                raise ValueError(f"work counter {key} must be a nonnegative integer")
            totals[str(key)] = totals.get(str(key), 0) + raw
    return totals


def _batch_work(results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Sum each request's complete top-level plan once.

    Plans intentionally retain their nested evidence.  Recursively walking that
    evidence double-counts the same work in both parent and child plans.
    """

    works: list[Mapping[str, Any]] = []
    for result in results:
        plan = result.get("plan")
        if not isinstance(plan, Mapping) or not isinstance(plan.get("work"), Mapping):
            raise ValueError("batch result plan must declare work counters")
        works.append(plan["work"])
    return _merge_work(*works)


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _optional_context(value: Any, name: str = "context") -> Mapping[str, Any] | None:
    if value is not None and not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object or null")
    return value


def _optional_id_sequence(value: Any, name: str = "relation_ids") -> Sequence[str] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be an array of nonempty strings or null")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{name} must be an array of nonempty strings or null")
    return value


def _checkpoint_state_certificate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Recreate the state-certificate envelope bound by a checkpoint payload."""

    tick = payload["tick"]
    return attach_hash({
        "schema": "TOM-STATE-AT-CERTIFICATE-0.2",
        "commit": payload["source_commit"],
        "instance_id": payload["instance_id"],
        "instance_hash": payload["instance_hash"],
        "requested_tick": tick,
        "executed_steps": payload.get("executed_steps", tick),
        "state": dict(payload["state"]),
        "status": "exact_discrete_replay",
    })


def verify_checkpoint_record(
    store: WorldStore,
    record: Mapping[str, Any],
    *,
    target_instance_id: str | None = None,
    max_query_steps: int | None = None,
    max_expression_nodes: int = 10_000,
    max_expression_depth: int = 64,
) -> dict[str, Any]:
    """Prove a checkpoint record by replaying from its source-commit root.

    This accepts a record mapping so commit validation can prove a staged
    checkpoint before publishing it.  Checkpoint use is explicitly disabled in
    the proving engine, which prevents a checkpoint from recursively vouching
    for itself or another checkpoint.
    """

    validate_record(record)
    if record["record_type"] != "checkpoint":
        raise TypeError(f"{record['id']} is not a checkpoint record")
    payload = record["payload"]
    instance_id = str(payload["instance_id"])
    if target_instance_id is not None and instance_id != target_instance_id:
        raise ValueError(
            f"checkpoint {record['id']} targets {instance_id}, not {target_instance_id}"
        )
    tick = int(payload["tick"])
    step_budget = tick if max_query_steps is None else max_query_steps
    root_engine = QueryEngine(
        store,
        commit=str(payload["source_commit"]),
        max_query_steps=step_budget,
        max_expression_nodes=max_expression_nodes,
        max_expression_depth=max_expression_depth,
        planner_mode="exhaustive",
        use_checkpoints=False,
    )
    _, instance, blob_hash = root_engine._program_for_instance(instance_id)
    if payload["instance_hash"] != instance["content_hash"]:
        raise ValueError(
            f"checkpoint {record['id']} instance hash does not match its source commit"
        )
    if payload["program_blob_hash"] != blob_hash:
        raise ValueError(
            f"checkpoint {record['id']} program blob hash does not match its source commit"
        )

    expected = root_engine.state_at(instance_id, tick)
    declared = _checkpoint_state_certificate(payload)
    errors: list[str] = []
    if payload["state_certificate_hash"] != declared["content_hash"]:
        errors.append("state_certificate_hash does not bind the declared checkpoint state")
    if payload["state_certificate_hash"] != expected["content_hash"]:
        errors.append("state_certificate_hash does not match exact root replay")
    if canonical_bytes(payload["state"]) != canonical_bytes(expected["state"]):
        errors.append("state is not byte-equal to exact root replay")
    if payload.get("executed_steps", tick) != expected["executed_steps"]:
        errors.append("executed_steps does not match exact root replay")
    if errors:
        raise ValueError(f"checkpoint {record['id']} semantic verification failed: " + "; ".join(errors))

    return attach_hash({
        "schema": "TOM-CHECKPOINT-VERIFICATION-CERTIFICATE-0.2",
        "checkpoint_id": record["id"],
        "checkpoint_hash": record["content_hash"],
        "source_commit": payload["source_commit"],
        "instance_id": instance_id,
        "instance_hash": instance["content_hash"],
        "program_blob_hash": blob_hash,
        "tick": tick,
        "root_replay_steps": expected["executed_steps"],
        "state_certificate_hash": expected["content_hash"],
        "byte_equal": True,
        "status": "verified_exact_root_replay",
    })


class QueryEngine:
    """Native exact-discrete TOM-SRS queries for one immutable world commit."""

    def __init__(
        self,
        store: WorldStore,
        *,
        commit: str | None = None,
        max_query_steps: int = 100_000,
        max_expression_nodes: int = 10_000,
        max_expression_depth: int = 64,
        planner_mode: str = "indexed",
        use_checkpoints: bool = True,
    ) -> None:
        store.validate()
        if planner_mode not in PLANNER_MODES:
            raise ValueError(f"planner_mode must be one of {sorted(PLANNER_MODES)}")
        if isinstance(max_query_steps, bool) or not isinstance(max_query_steps, int) or max_query_steps < 0:
            raise ValueError("max_query_steps must be a nonnegative integer")
        if isinstance(max_expression_nodes, bool) or not isinstance(max_expression_nodes, int) or max_expression_nodes < 1:
            raise ValueError("max_expression_nodes must be a positive integer")
        if isinstance(max_expression_depth, bool) or not isinstance(max_expression_depth, int) or max_expression_depth < 0:
            raise ValueError("max_expression_depth must be a nonnegative integer")
        if not isinstance(use_checkpoints, bool):
            raise ValueError("use_checkpoints must be boolean")
        self.store = store
        self.commit = commit or store.head
        if self.commit is None:
            raise ValueError("query engine requires a committed world")
        self.commit_record = store.read_commit(self.commit)
        self.snapshot = store.read_snapshot(str(self.commit_record["snapshot_hash"]))
        self.max_query_steps = max_query_steps
        self.max_expression_nodes = max_expression_nodes
        self.max_expression_depth = max_expression_depth
        self.planner_mode = planner_mode
        self.use_checkpoints = use_checkpoints
        self._program_cache: dict[str, Program] = {}

    def _planner(self, mode: str | None = None) -> QueryPlanner:
        return QueryPlanner(self.store, commit=self.commit, mode=mode or self.planner_mode)

    def _expression_budget(self) -> ExpressionBudget:
        return ExpressionBudget(self.max_expression_nodes, self.max_expression_depth)

    def definition_at(self, ident: str) -> dict[str, Any]:
        return self.store.read_record(_nonempty_string(ident, "id"), commit=self.commit)

    def verify_definition(self, ident: str) -> dict[str, Any]:
        result = self.store.verify_record(ident, commit=self.commit)
        if result.get("valid"):
            record = self.store.read_record(ident, commit=self.commit)
            result["is_definition"] = record["record_type"] == "definition"
            result["commit"] = self.commit
        return result

    def _instance(self, instance_id: str) -> dict[str, Any]:
        _nonempty_string(instance_id, "instance_id")
        record = self.store.read_record(instance_id, commit=self.commit)
        if record["record_type"] != "instance":
            raise TypeError(f"{instance_id} is not an instance")
        return record

    def _program_for_instance(self, instance_id: str) -> tuple[Program, dict[str, Any], str]:
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
        return program, instance, blob_hash

    def _checkpoint_start(
        self,
        instance_id: str,
        target_tick: int,
        *,
        planner_mode: str | None = None,
        allow_checkpoint: bool = True,
    ) -> tuple[State | None, int, int, dict[str, Any]]:
        mode = planner_mode or self.planner_mode
        if not self.use_checkpoints or not allow_checkpoint:
            plan = make_plan(
                commit=self.commit,
                snapshot_hash=str(self.snapshot["content_hash"]),
                indexes_hash=str(self.snapshot.get("indexes_hash")) if self.snapshot.get("indexes_hash") else None,
                mode=mode,
                operation="select_checkpoint",
                stages=[{
                    "name": "checkpoint_policy",
                    "mechanism": "disabled" if not self.use_checkpoints else "disabled_for_full_trace",
                    "input_count": 0,
                    "output_count": 0,
                    "detail": {"target_tick": target_tick},
                }],
                selected_ids=[],
                work={"record_reads": 0, "index_lookups": 0},
            )
            return None, 0, 0, plan

        selected, plan = self._planner(mode).checkpoint_ids(instance_id, target_tick)
        if not selected:
            return None, 0, 0, plan
        record = self.store.read_record(selected[0], commit=self.commit)
        if record["record_type"] != "checkpoint":
            raise TypeError(f"planned checkpoint {selected[0]} is not a checkpoint record")
        program, instance, blob_hash = self._program_for_instance(instance_id)
        del program
        payload = record["payload"]
        if payload["instance_hash"] != instance["content_hash"]:
            raise ValueError(f"checkpoint {record['id']} instance hash does not match current snapshot")
        if payload["program_blob_hash"] != blob_hash:
            raise ValueError(f"checkpoint {record['id']} program blob hash does not match current snapshot")
        source_commit = str(payload["source_commit"])
        if not self.store.is_ancestor(source_commit, self.commit):
            raise ValueError(f"checkpoint {record['id']} source commit is not in query commit ancestry")
        declared_certificate = _checkpoint_state_certificate(payload)
        if payload["state_certificate_hash"] != declared_certificate["content_hash"]:
            raise ValueError(
                f"checkpoint {record['id']} state certificate hash does not bind its declared state"
            )
        tick = int(payload["tick"])
        if tick > target_tick:
            raise ValueError("planner selected a checkpoint after the target tick")
        executed_steps = int(payload.get("executed_steps", tick))
        return state_from_mapping(payload["state"]), tick, executed_steps, plan

    def verify_checkpoint(
        self,
        checkpoint_id: str,
        *,
        target_instance_id: str | None = None,
    ) -> dict[str, Any]:
        """Prove a committed checkpoint by an exact, non-checkpoint root replay."""

        record = self.store.read_record(checkpoint_id, commit=self.commit)
        if record["record_type"] != "checkpoint":
            raise TypeError(f"{checkpoint_id} is not a checkpoint record")
        source_commit = str(record["payload"]["source_commit"])
        if not self.store.is_ancestor(source_commit, self.commit):
            raise ValueError(
                f"checkpoint {checkpoint_id} source commit is not in query commit ancestry"
            )
        return verify_checkpoint_record(
            self.store,
            record,
            target_instance_id=target_instance_id,
            max_query_steps=self.max_query_steps,
            max_expression_nodes=self.max_expression_nodes,
            max_expression_depth=self.max_expression_depth,
        )

    def _replay_state(
        self,
        instance_id: str,
        target_tick: int,
        *,
        include_trace: bool,
        planner_mode: str | None = None,
    ) -> tuple[State, list[dict[str, int]], dict[str, Any], dict[str, Any]]:
        if isinstance(target_tick, bool) or not isinstance(target_tick, int) or target_tick < 0:
            raise ValueError("target tick must be a nonnegative integer")
        if target_tick > self.max_query_steps:
            raise ValueError(f"target tick exceeds query budget: {target_tick} > {self.max_query_steps}")
        mode = planner_mode or self.planner_mode
        program, instance, _ = self._program_for_instance(instance_id)
        checkpoint_state, checkpoint_tick, checkpoint_executed, checkpoint_plan = self._checkpoint_start(
            instance_id, target_tick, planner_mode=mode, allow_checkpoint=not include_trace
        )
        remaining = target_tick - checkpoint_tick
        # Passing the selected root state explicitly preserves an instance's
        # override of every State64 word, including ``cell``.  TOMAGI's bare
        # run(program) entry behavior otherwise overwrites that one word.
        replay_start = checkpoint_state if checkpoint_state is not None else program.initial_state
        state, trace = run(program, ticks=remaining, state=replay_start, trace=True)
        for item in trace:
            item["step"] = checkpoint_tick + int(item["step"])
        actual_replayed_steps = len(trace)
        executed_steps = checkpoint_executed + actual_replayed_steps
        if not include_trace:
            trace = []
        replay_plan = attach_hash({
            "schema": "TOM-STATE-REPLAY-PLAN-0.2",
            "commit": self.commit,
            "instance_id": instance_id,
            "instance_hash": instance["content_hash"],
            "target_tick": target_tick,
            "checkpoint_tick": checkpoint_tick,
            "checkpoint_id": checkpoint_plan["selected_ids"][0] if checkpoint_plan["selected_ids"] else None,
            "checkpoint_selection": checkpoint_plan,
            "logical_steps": target_tick,
            "replayed_steps": actual_replayed_steps,
            "executed_steps": executed_steps,
            "saved_replay_steps": checkpoint_executed,
            "work": _merge_work(
                checkpoint_plan["work"],
                {
                    "tomagi_steps": actual_replayed_steps,
                    "checkpoint_record_reads": 1 if checkpoint_plan["selected_ids"] else 0,
                },
            ),
        })
        return state, trace, replay_plan, instance

    def _state_at_with_plan(
        self,
        instance_id: str,
        tick: int,
        *,
        include_trace: bool = False,
        planner_mode: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(include_trace, bool):
            raise ValueError("include_trace must be boolean")
        state, trace, plan, instance = self._replay_state(
            instance_id, tick, include_trace=include_trace, planner_mode=planner_mode
        )
        result: dict[str, Any] = {
            "schema": "TOM-STATE-AT-CERTIFICATE-0.2",
            "commit": self.commit,
            "instance_id": instance_id,
            "instance_hash": instance["content_hash"],
            "requested_tick": tick,
            "executed_steps": int(plan["executed_steps"]),
            "state": state_dict(state),
            "status": "exact_discrete_replay",
        }
        if include_trace:
            result["trace"] = trace
        return attach_hash(result), plan

    def state_at(self, instance_id: str, tick: int, *, include_trace: bool = False) -> dict[str, Any]:
        result, _ = self._state_at_with_plan(instance_id, tick, include_trace=include_trace)
        return result

    def state_at_with_plan(
        self,
        instance_id: str,
        tick: int,
        *,
        include_trace: bool = False,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        result, plan = self._state_at_with_plan(
            instance_id, tick, include_trace=include_trace, planner_mode=planner_mode
        )
        return attach_hash({
            "schema": "TOM-PLANNED-QUERY-CERTIFICATE-0.2",
            "query_kind": "state_at",
            "commit": self.commit,
            "result": result,
            "plan": plan,
        })

    def trace(self, instance_id: str, ticks: int) -> dict[str, Any]:
        return self.state_at(instance_id, ticks, include_trace=True)

    def _context(self, instance: Mapping[str, Any], context: Mapping[str, Any] | None) -> dict[str, Any]:
        base = instance["payload"].get("context", {})
        if not isinstance(base, Mapping):
            raise ValueError("instance context must be an object")
        _optional_context(context)
        merged = dict(base)
        if context is not None:
            merged.update(context)
        return merged

    def _relation_records(
        self,
        instance_id: str,
        relation_ids: Sequence[str] | None,
        *,
        support_id: str | None = None,
        interval: tuple[int, int] | None = None,
        topology_sheet: int | None = None,
        planner_mode: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        ids, plan = self._planner(planner_mode).relation_ids(
            instance_id,
            explicit_ids=relation_ids,
            support_id=support_id,
            interval=interval,
            topology_sheet=topology_sheet,
        )
        if relation_ids is not None:
            requested = {str(value) for value in relation_ids}
            missing = sorted(requested - set(ids))
            for ident in missing:
                try:
                    record = self.store.read_record(ident, commit=self.commit)
                except KeyError as exc:
                    raise KeyError(ident) from exc
                if record["record_type"] != "relation":
                    raise TypeError(f"{ident} is not a relation")
                if record["payload"]["instance_id"] != instance_id:
                    raise ValueError(f"relation {ident} targets a different instance")
                # A valid explicit relation can be absent only because a declared
                # support/interval/sheet filter removed it; that is not an error.
        relations = [self.store.read_record(ident, commit=self.commit) for ident in ids]
        relations.sort(key=lambda record: (int(record["payload"].get("priority", 0)), record["id"]))
        return relations, plan

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
        query_kind: str,
        query_relation_ids: Sequence[str],
        support_id: str | None,
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
        return attach_hash({
            "schema": "TOM-EVENT-CERTIFICATE-0.1",
            "source_commit": self.commit,
            "query": {
                "query_kind": query_kind,
                "instance_id": instance["id"],
                "after_tick": after_tick,
                "horizon": horizon,
                "relation_ids": list(query_relation_ids),
                "support_id": support_id,
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
        })

    @staticmethod
    def _active_at(relation: Mapping[str, Any], logical_tick: int) -> bool:
        interval = relation["payload"].get("active_interval", relation["payload"].get("time_interval"))
        if not isinstance(interval, Mapping):
            return True
        return int(interval["start"]) <= logical_tick <= int(interval["end"])

    def _scan_events(
        self,
        instance_id: str,
        *,
        after_tick: int,
        horizon: int,
        relation_ids: Sequence[str] | None,
        context: Mapping[str, Any] | None,
        stop_after_first: bool,
        support_id: str | None = None,
        topology_sheet: int | None = None,
        planner_mode: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if isinstance(after_tick, bool) or not isinstance(after_tick, int) or after_tick < 0:
            raise ValueError("after_tick must be a nonnegative integer")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            raise ValueError("horizon must be a positive integer")
        _nonempty_string(instance_id, "instance_id")
        relation_ids = _optional_id_sequence(relation_ids)
        _optional_context(context)
        if support_id is not None:
            _nonempty_string(support_id, "support_id")
        if topology_sheet is not None and (
            isinstance(topology_sheet, bool)
            or not isinstance(topology_sheet, int)
            or not 0 <= topology_sheet <= 0xFFFFFFFF
        ):
            raise ValueError("topology_sheet must be a u32 integer or null")
        if after_tick + horizon > self.max_query_steps:
            raise ValueError(
                f"event scan exceeds query budget: {after_tick + horizon} > {self.max_query_steps}"
            )
        mode = planner_mode or self.planner_mode
        program, instance, _ = self._program_for_instance(instance_id)
        relations, relation_plan = self._relation_records(
            instance_id,
            relation_ids,
            support_id=support_id,
            interval=(after_tick + 1, after_tick + horizon),
            topology_sheet=topology_sheet,
            planner_mode=mode,
        )
        state, _, replay_plan, _ = self._replay_state(
            instance_id, after_tick, include_trace=False, planner_mode=mode
        )
        merged_context = self._context(instance, context)
        query_kind = "next_event" if stop_after_first else "events_in_support"
        query_relation_ids = [str(relation["id"]) for relation in relations]
        logical_tick = after_tick
        events: list[dict[str, Any]] = []
        relation_evaluations = 0
        predicate_evaluations = 0
        inactive_interval_skips = 0
        ticks_scanned = 0
        tomagi_steps_scanned = 0
        for _ in range(horizon):
            pre_state = replace(state)
            if not (state.status & STATUS_HALT):
                step(program, state)
                tomagi_steps_scanned += 1
            logical_tick += 1
            ticks_scanned += 1
            candidates: list[dict[str, Any]] = []
            for relation in relations:
                if not self._active_at(relation, logical_tick):
                    inactive_interval_skips += 1
                    continue
                previous, residual, supports, compatibilities = self._evaluate_relation(
                    relation,
                    state=state,
                    pre_state=pre_state,
                    context=merged_context,
                )
                relation_evaluations += 1
                predicate_evaluations += len(supports) + len(compatibilities)
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
                        query_kind=query_kind,
                        query_relation_ids=query_relation_ids,
                        support_id=support_id,
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
                if stop_after_first:
                    candidates = [candidates[0]]
                for candidate in candidates:
                    query = dict(candidate["query"])
                    query["result_index"] = len(events)
                    candidate = dict(candidate)
                    candidate["query"] = query
                    events.append(attach_hash(candidate))
                if stop_after_first:
                    break
        scan_plan = attach_hash({
            "schema": "TOM-EVENT-SCAN-PLAN-0.2",
            "commit": self.commit,
            "instance_id": instance_id,
            "mode": mode,
            "after_tick": after_tick,
            "horizon": horizon,
            "stop_after_first": stop_after_first,
            "relation_selection": relation_plan,
            "state_replay": replay_plan,
            "selected_relation_count": len(relations),
            "ticks_scanned": ticks_scanned,
            "tomagi_steps_scanned": tomagi_steps_scanned,
            "relation_evaluations": relation_evaluations,
            "predicate_evaluations": predicate_evaluations,
            "inactive_interval_skips": inactive_interval_skips,
            "events_found": len(events),
            "work": _merge_work(
                relation_plan["work"],
                replay_plan["work"],
                {
                    "tomagi_steps": tomagi_steps_scanned,
                    "relation_evaluations": relation_evaluations,
                    "predicate_evaluations": predicate_evaluations,
                },
            ),
        })
        return events, scan_plan

    def next_event(
        self,
        instance_id: str,
        after_tick: int,
        *,
        horizon: int = 1024,
        relation_ids: Sequence[str] | None = None,
        context: Mapping[str, Any] | None = None,
        planner_mode: str | None = None,
    ) -> dict[str, Any] | None:
        events, _ = self._scan_events(
            instance_id,
            after_tick=after_tick,
            horizon=horizon,
            relation_ids=relation_ids,
            context=context,
            stop_after_first=True,
            planner_mode=planner_mode,
        )
        return events[0] if events else None

    def next_event_with_plan(
        self,
        instance_id: str,
        after_tick: int,
        *,
        horizon: int = 1024,
        relation_ids: Sequence[str] | None = None,
        context: Mapping[str, Any] | None = None,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        events, plan = self._scan_events(
            instance_id,
            after_tick=after_tick,
            horizon=horizon,
            relation_ids=relation_ids,
            context=context,
            stop_after_first=True,
            planner_mode=planner_mode,
        )
        return attach_hash({
            "schema": "TOM-PLANNED-QUERY-CERTIFICATE-0.2",
            "query_kind": "next_event",
            "commit": self.commit,
            "result": events[0] if events else None,
            "plan": plan,
        })

    def events_in_support(
        self,
        instance_id: str,
        *,
        start_tick: int,
        end_tick: int,
        support_id: str | None = None,
        relation_ids: Sequence[str] | None = None,
        context: Mapping[str, Any] | None = None,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        result, _ = self._events_in_support_with_plan(
            instance_id,
            start_tick=start_tick,
            end_tick=end_tick,
            support_id=support_id,
            relation_ids=relation_ids,
            context=context,
            planner_mode=planner_mode,
        )
        return result

    def _events_in_support_with_plan(
        self,
        instance_id: str,
        *,
        start_tick: int,
        end_tick: int,
        support_id: str | None,
        relation_ids: Sequence[str] | None,
        context: Mapping[str, Any] | None,
        planner_mode: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if isinstance(start_tick, bool) or not isinstance(start_tick, int) or start_tick < 0:
            raise ValueError("start_tick must be a nonnegative integer")
        if isinstance(end_tick, bool) or not isinstance(end_tick, int) or end_tick < 0:
            raise ValueError("end_tick must be a nonnegative integer")
        if end_tick <= start_tick:
            raise ValueError("end_tick must be greater than start_tick")
        if support_id is not None:
            _nonempty_string(support_id, "support_id")
            support_record = self.store.read_record(support_id, commit=self.commit)
            if support_record["record_type"] != "support":
                raise TypeError(f"{support_id} is not a support record")
        events, plan = self._scan_events(
            instance_id,
            after_tick=start_tick,
            horizon=end_tick - start_tick,
            relation_ids=relation_ids,
            context=context,
            stop_after_first=False,
            support_id=support_id,
            planner_mode=planner_mode,
        )
        return attach_hash({
            "schema": "TOM-EVENTS-IN-SUPPORT-CERTIFICATE-0.2",
            "commit": self.commit,
            "instance_id": instance_id,
            "support_id": support_id,
            "interval": {"start_exclusive": start_tick, "end_inclusive": end_tick},
            "event_count": len(events),
            "events": events,
        }), plan

    def events_in_support_with_plan(
        self,
        instance_id: str,
        *,
        start_tick: int,
        end_tick: int,
        support_id: str | None = None,
        relation_ids: Sequence[str] | None = None,
        context: Mapping[str, Any] | None = None,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        result, plan = self._events_in_support_with_plan(
            instance_id,
            start_tick=start_tick,
            end_tick=end_tick,
            support_id=support_id,
            relation_ids=relation_ids,
            context=context,
            planner_mode=planner_mode,
        )
        return attach_hash({
            "schema": "TOM-PLANNED-QUERY-CERTIFICATE-0.2",
            "query_kind": "events_in_support",
            "commit": self.commit,
            "result": result,
            "plan": plan,
        })

    def _compatible_with_plan(
        self,
        left_instance_id: str,
        right_instance_id: str,
        compatibility_id: str,
        *,
        tick: int,
        context: Mapping[str, Any] | None,
        planner_mode: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        _nonempty_string(left_instance_id, "left_instance_id")
        _nonempty_string(right_instance_id, "right_instance_id")
        _nonempty_string(compatibility_id, "compatibility_id")
        _optional_context(context)
        record = self.store.read_record(compatibility_id, commit=self.commit)
        if record["record_type"] != "compatibility":
            raise TypeError(f"{compatibility_id} is not a compatibility record")
        left, _, left_plan, _ = self._replay_state(
            left_instance_id, tick, include_trace=False, planner_mode=planner_mode
        )
        right, _, right_plan, _ = self._replay_state(
            right_instance_id, tick, include_trace=False, planner_mode=planner_mode
        )
        sources = _record_sources(left, left=left, right=right, context=context)
        value = evaluate_expression(record["payload"]["expression"], sources, budget=self._expression_budget())
        if not isinstance(value, bool):
            raise TypeError("compatibility expression must return bool")
        result = attach_hash({
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
            "context": dict(context) if context is not None else {},
        })
        plan = attach_hash({
            "schema": "TOM-COMPATIBILITY-QUERY-PLAN-0.2",
            "commit": self.commit,
            "mode": planner_mode or self.planner_mode,
            "left_replay": left_plan,
            "right_replay": right_plan,
            "expression_nodes_limit": self.max_expression_nodes,
            "work": _merge_work(
                left_plan["work"],
                right_plan["work"],
                {"compatibility_evaluations": 1},
            ),
        })
        return result, plan

    def compatible(
        self,
        left_instance_id: str,
        right_instance_id: str,
        compatibility_id: str,
        *,
        tick: int,
        context: Mapping[str, Any] | None = None,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        result, _ = self._compatible_with_plan(
            left_instance_id, right_instance_id, compatibility_id,
            tick=tick, context=context, planner_mode=planner_mode,
        )
        return result

    def compatible_with_plan(
        self,
        left_instance_id: str,
        right_instance_id: str,
        compatibility_id: str,
        *,
        tick: int,
        context: Mapping[str, Any] | None = None,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        result, plan = self._compatible_with_plan(
            left_instance_id, right_instance_id, compatibility_id,
            tick=tick, context=context, planner_mode=planner_mode,
        )
        return attach_hash({
            "schema": "TOM-PLANNED-QUERY-CERTIFICATE-0.2",
            "query_kind": "compatible",
            "commit": self.commit,
            "result": result,
            "plan": plan,
        })

    def make_checkpoint_record(self, instance_id: str, tick: int) -> dict[str, Any]:
        """Construct a checkpoint by exact replay from the instance root state."""

        root_engine = QueryEngine(
            self.store,
            commit=self.commit,
            max_query_steps=self.max_query_steps,
            max_expression_nodes=self.max_expression_nodes,
            max_expression_depth=self.max_expression_depth,
            planner_mode="exhaustive",
            use_checkpoints=False,
        )
        certificate = root_engine.state_at(instance_id, tick)
        _, instance, blob_hash = self._program_for_instance(instance_id)
        safe_instance = instance_id.replace("/", "_")
        ident = f"checkpoint:{safe_instance}:{tick:012d}:{instance['content_hash'][7:19]}"
        return make_record(
            "checkpoint",
            ident,
            {
                "instance_id": instance_id,
                "tick": tick,
                "executed_steps": certificate["executed_steps"],
                "state": certificate["state"],
                "instance_hash": instance["content_hash"],
                "program_blob_hash": blob_hash,
                "source_commit": self.commit,
                "state_certificate_hash": certificate["content_hash"],
                "topology_sheet": certificate["state"]["sheet"],
                "generative_address": {"instance_id": instance_id, "tick": tick},
                "time_interval": {"start": tick, "end": tick},
            },
            dependencies=[instance_id],
            provenance={"method": "exact_replay_from_root", "source_commit": self.commit},
        )

    def commit_checkpoints(
        self,
        instance_id: str,
        ticks: Sequence[int],
        *,
        message: str = "append exact state checkpoints",
    ) -> dict[str, Any]:
        unique = sorted(set(ticks))
        if len(unique) != len(ticks):
            raise ValueError("checkpoint tick list must not contain duplicates")
        records = [self.make_checkpoint_record(instance_id, tick) for tick in unique]
        transaction = attach_hash({
            "schema": TRANSACTION_SCHEMA,
            "seed_sha256": self.commit_record["seed_sha256"],
            "base_commit": self.store.head,
            "sequence": int(self.commit_record["sequence"]) + 1,
            "message": message,
            "records": records,
            "blobs": [],
            "provenance": {
                "checkpoint_instance": instance_id,
                "source_commit": self.commit,
                "ticks": unique,
            },
        })
        return self.store.commit_transaction(transaction)

    def batch(
        self,
        requests: Sequence[Mapping[str, Any]],
        *,
        planner_mode: str | None = None,
    ) -> dict[str, Any]:
        """Execute a finite declared batch in array order with stable reduction."""

        if isinstance(requests, (str, bytes, bytearray)) or not isinstance(requests, Sequence):
            raise ValueError("batch requests must be an array")
        mode = planner_mode or self.planner_mode
        if mode not in PLANNER_MODES:
            raise ValueError(f"planner mode must be one of {sorted(PLANNER_MODES)}")
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        semantic_results: list[Any] = []
        for position, request in enumerate(requests):
            if not isinstance(request, Mapping):
                raise ValueError("batch requests must be objects")
            ident = request.get("id")
            operation = request.get("operation")
            parameters = request.get("parameters", {})
            if not isinstance(ident, str) or not ident:
                raise ValueError("batch request id must be a nonempty string")
            if ident in seen:
                raise ValueError(f"duplicate batch request id: {ident}")
            seen.add(ident)
            if not isinstance(operation, str):
                raise ValueError(f"batch request {ident} operation must be a string")
            if not isinstance(parameters, Mapping):
                raise ValueError(f"batch request {ident} parameters must be an object")

            def required(name: str) -> Any:
                if name not in parameters:
                    raise ValueError(f"batch request {ident} is missing parameter {name}")
                return parameters[name]

            if operation == "state_at":
                planned = self.state_at_with_plan(
                    _nonempty_string(required("instance_id"), "instance_id"), required("tick"),
                    include_trace=parameters.get("include_trace", False), planner_mode=mode,
                )
            elif operation == "next_event":
                planned = self.next_event_with_plan(
                    _nonempty_string(required("instance_id"), "instance_id"), required("after_tick"),
                    horizon=parameters.get("horizon", 1024),
                    relation_ids=parameters.get("relation_ids"),
                    context=parameters.get("context"),
                    planner_mode=mode,
                )
            elif operation == "events_in_support":
                planned = self.events_in_support_with_plan(
                    _nonempty_string(required("instance_id"), "instance_id"),
                    start_tick=required("start_tick"),
                    end_tick=required("end_tick"),
                    support_id=parameters.get("support_id"),
                    relation_ids=parameters.get("relation_ids"),
                    context=parameters.get("context"),
                    planner_mode=mode,
                )
            elif operation == "compatible":
                planned = self.compatible_with_plan(
                    _nonempty_string(required("left_instance_id"), "left_instance_id"),
                    _nonempty_string(required("right_instance_id"), "right_instance_id"),
                    _nonempty_string(required("compatibility_id"), "compatibility_id"),
                    tick=required("tick"),
                    context=parameters.get("context"),
                    planner_mode=mode,
                )
            elif operation == "definition_at":
                definition_id = _nonempty_string(required("id"), "id")
                semantic = self.definition_at(definition_id)
                trivial_plan = make_plan(
                    commit=self.commit,
                    snapshot_hash=str(self.snapshot["content_hash"]),
                    indexes_hash=str(self.snapshot.get("indexes_hash")) if self.snapshot.get("indexes_hash") else None,
                    mode=mode,
                    operation="definition_at",
                    stages=[{
                        "name": "primary_id_map",
                        "mechanism": "snapshot:records",
                        "input_count": len(self.snapshot["records"]),
                        "output_count": 1,
                        "detail": {"id": definition_id},
                    }],
                    selected_ids=[definition_id],
                    work={"record_reads": 1},
                )
                planned = attach_hash({
                    "schema": "TOM-PLANNED-QUERY-CERTIFICATE-0.2",
                    "query_kind": "definition_at",
                    "commit": self.commit,
                    "result": semantic,
                    "plan": trivial_plan,
                })
            else:
                raise ValueError(f"unsupported batch operation {operation}")

            semantic = planned["result"]
            semantic_results.append(semantic)
            results.append({
                "position": position,
                "id": ident,
                "operation": operation,
                "result": semantic,
                "result_hash": semantic.get("content_hash") if isinstance(semantic, Mapping) else digest_bytes(canonical_bytes(semantic)),
                "plan": planned["plan"],
                "planned_certificate_hash": planned["content_hash"],
            })

        reduction_input = _length_prefixed(semantic_results)
        work = _batch_work(results)
        return attach_hash({
            "schema": "TOM-BATCH-QUERY-CERTIFICATE-0.2",
            "version": "0.2.0",
            "commit": self.commit,
            "planner_mode": mode,
            "request_count": len(results),
            "reduction_order": "declared_array_order",
            "request_ids": [item["id"] for item in results],
            "semantic_reduction_hash": digest_bytes(reduction_input),
            "semantic_result_hashes": [item["result_hash"] for item in results],
            "results": results,
            "work": {key: work[key] for key in sorted(work)},
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
        if not isinstance(query, Mapping):
            raise ValueError("event certificate query is invalid")
        relation_ids = query.get("relation_ids")
        if not isinstance(relation_ids, list) or any(not isinstance(value, str) for value in relation_ids):
            raise ValueError("event certificate relation_ids are invalid")
        engine = QueryEngine(
            self.store,
            commit=source_commit,
            max_query_steps=self.max_query_steps,
            max_expression_nodes=self.max_expression_nodes,
            max_expression_depth=self.max_expression_depth,
            planner_mode=self.planner_mode,
            use_checkpoints=self.use_checkpoints,
        )
        query_kind = query.get("query_kind")
        if query_kind is None:
            # 0.1 certificates named only their originating relation and were
            # always reconstructed as a next_event query.  Project the newly
            # generated certificate back onto that legacy query envelope so
            # already committed lineages remain byte-reconstructible.
            recomputed = engine.next_event(
                str(query["instance_id"]),
                int(query["after_tick"]),
                horizon=int(query["horizon"]),
                relation_ids=relation_ids,
                context=certificate.get("context", {}),
            )
            if recomputed is not None:
                recomputed = dict(recomputed)
                recomputed["query"] = dict(query)
                recomputed = attach_hash(recomputed)
        elif query_kind == "next_event":
            result_index = query.get("result_index")
            if result_index != 0:
                recomputed = None
            else:
                recomputed = engine.next_event(
                    str(query["instance_id"]),
                    int(query["after_tick"]),
                    horizon=int(query["horizon"]),
                    relation_ids=relation_ids,
                    context=certificate.get("context", {}),
                )
        elif query_kind == "events_in_support":
            result_index = query.get("result_index")
            if isinstance(result_index, bool) or not isinstance(result_index, int) or result_index < 0:
                recomputed = None
            else:
                support_id = query.get("support_id")
                if support_id is not None and not isinstance(support_id, str):
                    raise ValueError("event certificate support_id is invalid")
                start_tick = int(query["after_tick"])
                result = engine.events_in_support(
                    str(query["instance_id"]),
                    start_tick=start_tick,
                    end_tick=start_tick + int(query["horizon"]),
                    support_id=support_id,
                    relation_ids=relation_ids,
                    context=certificate.get("context", {}),
                )
                events = result["events"]
                recomputed = events[result_index] if result_index < len(events) else None
        else:
            raise ValueError(f"event certificate query_kind is unsupported: {query_kind}")
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
                "time_interval": {"start": certificate["event_tick"], "end": certificate["event_tick"]},
                "topology_sheet": certificate["event_state"]["sheet"],
                "generative_address": {"event_certificate": certificate["content_hash"]},
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
                "generative_address": {"event_id": event_id, "lineage": certificate["post_state"]["lineage"]},
                "topology_sheet": certificate["post_state"]["sheet"],
            },
            dependencies=[event_id],
            provenance={"source_commit": certificate["source_commit"]},
        )
        return event_record, lineage_record

    def commit_event(self, certificate: Mapping[str, Any], *, message: str = "commit verified event") -> dict[str, Any]:
        if certificate.get("source_commit") != self.store.head:
            raise ValueError("event certificate source commit must equal current HEAD")
        reconstruction = self.reconstruct(certificate)
        if not reconstruction["byte_equal"]:
            raise ValueError("event certificate does not reconstruct byte-for-byte")
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
