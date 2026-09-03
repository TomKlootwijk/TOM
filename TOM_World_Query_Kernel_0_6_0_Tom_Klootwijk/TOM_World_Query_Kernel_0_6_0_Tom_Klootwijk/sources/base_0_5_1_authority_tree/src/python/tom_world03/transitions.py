"""Deterministic simultaneous-event transition merge and conflict rejection."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from .canonical import attach_hash
from .model import IntervalWorld, Relation, TransitionOp
from .rational import Q


class TransitionConflict(ValueError):
    pass


def _qrecord_map(state: Mapping[str, Q]) -> dict[str, dict[str, int]]:
    return {name: value.to_record() for name, value in sorted(state.items())}


def merge_transition_ops(relations: list[Relation]) -> tuple[list[dict[str, Any]], dict[str, tuple[str, Q]]]:
    grouped: dict[str, list[tuple[Relation, TransitionOp]]] = defaultdict(list)
    for relation in relations:
        for operation in relation.transition:
            grouped[operation.field].append((relation, operation))

    merged: dict[str, tuple[str, Q]] = {}
    audit: list[dict[str, Any]] = []
    for field in sorted(grouped):
        items = grouped[field]
        modes = {operation.mode for _, operation in items}
        if len(modes) != 1:
            raise TransitionConflict(
                f"simultaneous transition conflict on {field}: mixed modes {sorted(modes)}"
            )
        mode = next(iter(modes))
        values = [operation.value for _, operation in items]
        if mode == "set":
            if any(value != values[0] for value in values[1:]):
                raise TransitionConflict(f"simultaneous set conflict on {field}")
            value = values[0]
        elif mode == "add":
            value = sum(values, Q(0))
        elif mode == "xor":
            accumulator = 0
            for item in values:
                accumulator ^= item.as_integer()
            value = Q(accumulator)
        else:  # pragma: no cover - validated upstream.
            raise AssertionError(mode)
        merged[field] = (mode, value)
        audit.append({
            "field": field,
            "mode": mode,
            "merged_value": value.to_record(),
            "contributors": [
                {
                    "relation_id": relation.id,
                    "event_id": relation.event_id,
                    "priority": relation.priority,
                    "value": operation.value.to_record(),
                }
                for relation, operation in items
            ],
        })
    return audit, merged


def apply_event_set(world: IntervalWorld, event_set: Mapping[str, Any]) -> dict[str, Any]:
    if event_set.get("schema") != "TOM-NEXT-EVENT-SET-0.3" or event_set.get("status") != "accepted":
        raise ValueError("apply_event_set requires an accepted TOM-NEXT-EVENT-SET-0.3 certificate")
    event_time = Q.from_value(event_set["event_time"])
    by_id = {relation.id: relation for relation in world.relations}
    relation_ids = [str(value) for value in event_set.get("relation_order", [])]
    try:
        relations = [by_id[ident] for ident in relation_ids]
    except KeyError as exc:
        raise ValueError(f"event set references unknown relation {exc.args[0]}") from exc

    pre_state = world.trajectory.state_at(event_time)
    audit, merged = merge_transition_ops(relations)
    post_state = dict(pre_state)
    for field, (mode, value) in merged.items():
        current = post_state.get(field, Q(0))
        if mode == "set":
            post_state[field] = value
        elif mode == "add":
            post_state[field] = current + value
        elif mode == "xor":
            post_state[field] = Q(current.as_integer() ^ value.as_integer())
        else:  # pragma: no cover
            raise AssertionError(mode)

    return attach_hash({
        "schema": "TOM-SIMULTANEOUS-TRANSITION-0.3",
        "world_hash": world.content_hash,
        "event_set_hash": event_set.get("content_hash"),
        "event_time": event_time.to_record(),
        "event_order": list(event_set.get("event_order", [])),
        "merge_policy": {
            "set": "all simultaneous values must be equal",
            "add": "exact rational sum",
            "xor": "integer xor",
            "mixed_modes": "reject",
            "application_basis": "all operations read the common pre-event state",
        },
        "pre_state": _qrecord_map(pre_state),
        "merged_operations": audit,
        "post_state": _qrecord_map(post_state),
    })
