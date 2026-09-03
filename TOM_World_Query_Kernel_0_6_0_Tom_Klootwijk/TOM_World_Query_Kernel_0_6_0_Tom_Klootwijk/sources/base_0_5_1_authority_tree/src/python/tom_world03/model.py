"""Typed 0.3 world records: affine trajectories, supports, compatibility, relations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .canonical import require_hash, verify_hash
from .expression import validate_expression
from .interval import ClosedInterval
from .rational import Q


@dataclass(frozen=True, slots=True)
class AffineField:
    initial: Q
    rate: Q

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "AffineField":
        return cls(Q.from_value(record.get("initial", 0)), Q.from_value(record.get("rate", 0)))


@dataclass(frozen=True, slots=True)
class AffineTrajectory:
    id: str
    domain: ClosedInterval
    fields: Mapping[str, AffineField]
    source_program: str | None = None
    content_hash: str | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "AffineTrajectory":
        require_hash(record, label="trajectory")
        if record.get("kind") != "affine-rational-trajectory":
            raise ValueError("trajectory kind must be affine-rational-trajectory")
        fields_record = record.get("fields")
        if not isinstance(fields_record, Mapping) or not fields_record:
            raise ValueError("trajectory requires a nonempty fields object")
        fields = {str(name): AffineField.from_record(value) for name, value in fields_record.items()}
        return cls(
            id=str(record["id"]),
            domain=ClosedInterval.from_value(record["domain"]),
            fields=fields,
            source_program=None if record.get("source_program") is None else str(record["source_program"]),
            content_hash=str(record["content_hash"]),
        )

    def require_time(self, time: Q) -> None:
        if not self.domain.contains(time):
            raise ValueError(f"time {time} is outside trajectory domain {self.domain}")

    def state_at(self, time: Q) -> dict[str, Q]:
        time = Q.from_value(time)
        self.require_time(time)
        return {name: field.initial + field.rate * time for name, field in self.fields.items()}

    def field_rate(self, name: str) -> Q:
        try:
            return self.fields[name].rate
        except KeyError as exc:
            raise ValueError(f"trajectory has no field {name}") from exc

    def field_affine(self, name: str) -> tuple[Q, Q]:
        try:
            field = self.fields[name]
        except KeyError as exc:
            raise ValueError(f"trajectory has no field {name}") from exc
        return field.rate, field.initial

    def field_interval(self, name: str, time: ClosedInterval) -> ClosedInterval:
        intersection = self.domain.intersection(time)
        if intersection is None or intersection != time:
            raise ValueError("requested interval is outside trajectory domain")
        field = self.fields.get(name)
        if field is None:
            raise ValueError(f"trajectory has no field {name}")
        return ClosedInterval.hull([
            field.initial + field.rate * time.lower,
            field.initial + field.rate * time.upper,
        ])

    def state_interval(self, time: ClosedInterval) -> dict[str, ClosedInterval]:
        return {name: self.field_interval(name, time) for name in self.fields}


@dataclass(frozen=True, slots=True)
class Support:
    id: str
    bounds: Mapping[str, ClosedInterval]
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Support":
        require_hash(record, label="support")
        if record.get("kind") != "interval-support":
            raise ValueError("support kind must be interval-support")
        bounds_record = record.get("bounds", {})
        if not isinstance(bounds_record, Mapping):
            raise ValueError("support bounds must be an object")
        return cls(str(record["id"]), {
            str(name): ClosedInterval.from_value(value)
            for name, value in bounds_record.items()
        }, str(record["content_hash"]))

    def accepts_point(self, state: Mapping[str, Q]) -> bool:
        return all(name in state and bound.contains(state[name]) for name, bound in self.bounds.items())

    def contains_interval(self, state: Mapping[str, ClosedInterval]) -> bool:
        return all(name in state and state[name].subset_of(bound) for name, bound in self.bounds.items())


@dataclass(frozen=True, slots=True)
class Compatibility:
    id: str
    equals: Mapping[str, Q]
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Compatibility":
        require_hash(record, label="compatibility")
        if record.get("kind") != "field-equality-compatibility":
            raise ValueError("compatibility kind must be field-equality-compatibility")
        equals = record.get("equals", {})
        if not isinstance(equals, Mapping):
            raise ValueError("compatibility equals must be an object")
        return cls(str(record["id"]), {str(k): Q.from_value(v) for k, v in equals.items()},
                   str(record["content_hash"]))

    def accepts(self, state: Mapping[str, Q]) -> bool:
        return all(state.get(name) == expected for name, expected in self.equals.items())


@dataclass(frozen=True, slots=True)
class TransitionOp:
    field: str
    mode: str
    value: Q

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "TransitionOp":
        field = str(record.get("field", ""))
        mode = str(record.get("mode", ""))
        if not field:
            raise ValueError("transition operation requires field")
        if mode not in {"set", "add", "xor"}:
            raise ValueError(f"unsupported transition mode {mode}")
        value = Q.from_value(record.get("value", 0))
        if mode == "xor" and not value.is_integer():
            raise ValueError("xor transition value must be an integer")
        return cls(field, mode, value)

    def to_record(self) -> dict[str, Any]:
        return {"field": self.field, "mode": self.mode, "value": self.value.to_record()}


@dataclass(frozen=True, slots=True)
class Relation:
    id: str
    priority: int
    expression: Mapping[str, Any]
    support_id: str
    compatibility_id: str
    active_time: ClosedInterval
    event_id: str
    transition: tuple[TransitionOp, ...]
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Relation":
        require_hash(record, label="relation")
        if record.get("kind") != "continuous-zero-relation":
            raise ValueError("relation kind must be continuous-zero-relation")
        expression = record.get("expression")
        if not isinstance(expression, Mapping):
            raise ValueError("relation expression must be an object")
        validate_expression(expression)
        transition_record = record.get("transition", [])
        if not isinstance(transition_record, list):
            raise ValueError("relation transition must be an array")
        return cls(
            id=str(record["id"]),
            priority=int(record.get("priority", 0)),
            expression=expression,
            support_id=str(record["support_id"]),
            compatibility_id=str(record["compatibility_id"]),
            active_time=ClosedInterval.from_value(record["active_time"]),
            event_id=str(record["event_id"]),
            transition=tuple(TransitionOp.from_record(item) for item in transition_record),
            content_hash=str(record["content_hash"]),
        )


@dataclass(frozen=True, slots=True)
class IntervalWorld:
    schema: str
    seed_sha256: str
    trajectory: AffineTrajectory
    supports: Mapping[str, Support]
    compatibilities: Mapping[str, Compatibility]
    relations: tuple[Relation, ...]
    solver: Mapping[str, Any]
    content_hash: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "IntervalWorld":
        require_hash(record, label="interval world")
        if record.get("schema") != "TOM-WORLD-INTERVAL-EVENTS-0.3":
            raise ValueError("unsupported interval world schema")
        trajectory = AffineTrajectory.from_record(record["trajectory"])
        supports_list = record.get("supports", [])
        compat_list = record.get("compatibilities", [])
        relations_list = record.get("relations", [])
        if not all(isinstance(x, list) for x in (supports_list, compat_list, relations_list)):
            raise ValueError("supports, compatibilities, and relations must be arrays")
        supports = {obj.id: obj for obj in map(Support.from_record, supports_list)}
        compatibilities = {obj.id: obj for obj in map(Compatibility.from_record, compat_list)}
        relations = tuple(map(Relation.from_record, relations_list))
        if len(supports) != len(supports_list):
            raise ValueError("duplicate support id")
        if len(compatibilities) != len(compat_list):
            raise ValueError("duplicate compatibility id")
        if len({r.id for r in relations}) != len(relations):
            raise ValueError("duplicate relation id")
        for relation in relations:
            if relation.support_id not in supports:
                raise ValueError(f"relation {relation.id} references unknown support")
            if relation.compatibility_id not in compatibilities:
                raise ValueError(f"relation {relation.id} references unknown compatibility")
        solver = record.get("solver", {})
        if not isinstance(solver, Mapping):
            raise ValueError("solver profile must be an object")
        return cls(
            schema=str(record["schema"]),
            seed_sha256=str(record["seed_sha256"]),
            trajectory=trajectory,
            supports=supports,
            compatibilities=compatibilities,
            relations=relations,
            solver=dict(solver),
            content_hash=str(record["content_hash"]),
        )
