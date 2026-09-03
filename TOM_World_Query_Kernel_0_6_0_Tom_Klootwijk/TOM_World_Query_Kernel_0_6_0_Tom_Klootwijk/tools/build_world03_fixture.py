from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world03.baseline import trusted_affine_baseline
from tom_world03.canonical import attach_hash, canonical_bytes
from tom_world03.interval import ClosedInterval
from tom_world03.io import load_world, write_canonical
from tom_world03.model import Relation, TransitionOp
from tom_world03.rational import Q
from tom_world03.solver import certify_crossing, events_certificate, next_event_set
from tom_world03.transitions import TransitionConflict, apply_event_set, merge_transition_ops

EXAMPLE = ROOT / "examples/world03"
VALIDATION = ROOT / "validation/world03"
EXAMPLE.mkdir(parents=True, exist_ok=True)
VALIDATION.mkdir(parents=True, exist_ok=True)

SEED_HASH = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def q(value: int, den: int = 1) -> dict[str, int]:
    return {"num": value, "den": den}


def interval(lower: tuple[int, int] | int, upper: tuple[int, int] | int) -> dict[str, Any]:
    def r(value: tuple[int, int] | int) -> dict[str, int]:
        return q(*value) if isinstance(value, tuple) else q(value)
    return {"lower": r(lower), "upper": r(upper)}


def const(value: int, den: int = 1) -> dict[str, Any]:
    return {"op": "const", "value": q(value, den)}


def field(name: str) -> dict[str, str]:
    return {"op": "field", "name": name}


def time_expr() -> dict[str, str]:
    return {"op": "time"}


def sub(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    return {"op": "sub", "args": [dict(a), dict(b)]}


def mul(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    return {"op": "mul", "args": [dict(a), dict(b)]}


def relation(
    ident: str,
    event_id: str,
    priority: int,
    expression: Mapping[str, Any],
    transition: list[dict[str, Any]],
    *,
    support: str = "support:main",
    compatibility: str = "compat:mode-1",
    active: tuple[int, int] = (0, 10),
    purpose: str,
) -> dict[str, Any]:
    return attach_hash({
        "id": ident,
        "kind": "continuous-zero-relation",
        "relation_interface": "SDF0@Def",
        "domain": "affine-rational-trajectory",
        "codomain": "exact-rational-residual",
        "zero_locus": purpose,
        "priority": priority,
        "expression": dict(expression),
        "support_id": support,
        "compatibility_id": compatibility,
        "active_time": interval(active[0], active[1]),
        "event_id": event_id,
        "transition": transition,
        "provenance": {
            "source": "TOM World & Query Kernel 0.3 deterministic interval fixture",
            "date": "2026-09-01",
        },
    })


def build_world_record() -> dict[str, Any]:
    trajectory = attach_hash({
        "id": "trajectory:affine-reference",
        "kind": "affine-rational-trajectory",
        "domain": interval(0, 10),
        "fields": {
            "x": {"initial": q(0), "rate": q(2)},
            "clock": {"initial": q(0), "rate": q(1)},
            "mode": {"initial": q(1), "rate": q(0)},
            "counter": {"initial": q(0), "rate": q(0)},
            "output": {"initial": q(0), "rate": q(0)},
        },
        "source_program": "examples/world03/affine_reference.tmg",
        "interpolation": "exact affine interpolation between integer TOMAGI anchors",
        "provenance": {"date": "2026-09-01", "source": "literal fixture definition"},
    })
    supports = [
        attach_hash({
            "id": "support:main",
            "kind": "interval-support",
            "bounds": {"x": interval(0, 20), "mode": interval(1, 1)},
            "meaning": "Candidate root lies in the declared finite spatial/mode support.",
        }),
        attach_hash({
            "id": "support:x-below-4",
            "kind": "interval-support",
            "bounds": {"x": interval(0, 4), "mode": interval(1, 1)},
            "meaning": "Deliberately excludes x=5 for rejection evidence.",
        }),
    ]
    compatibilities = [
        attach_hash({
            "id": "compat:mode-1",
            "kind": "field-equality-compatibility",
            "equals": {"mode": q(1)},
            "meaning": "Accept the fixture's declared mode.",
        }),
        attach_hash({
            "id": "compat:mode-2",
            "kind": "field-equality-compatibility",
            "equals": {"mode": q(2)},
            "meaning": "Deliberately incompatible with the fixture trajectory.",
        }),
    ]
    relations = [
        relation(
            "relation:time-equals-five-halves",
            "event:time-five-halves:set-output",
            10,
            sub(time_expr(), const(5, 2)),
            [{"field": "output", "mode": "set", "value": q(25)}],
            purpose="time = 5/2",
        ),
        relation(
            "relation:triple-x-equals-fifteen",
            "event:triple-x:add-two",
            10,
            sub(mul(const(3), field("x")), const(15)),
            [{"field": "counter", "mode": "add", "value": q(2)}],
            purpose="3*x - 15 = 0, equivalent to x=5",
        ),
        relation(
            "relation:x-equals-five",
            "event:x-five:add-one",
            20,
            sub(field("x"), const(5)),
            [{"field": "counter", "mode": "add", "value": q(1)}],
            purpose="x - 5 = 0",
        ),
        relation(
            "relation:x-equals-ten",
            "event:x-ten:set-output",
            5,
            sub(field("x"), const(10)),
            [{"field": "output", "mode": "set", "value": q(50)}],
            purpose="x - 10 = 0, a later event at t=5",
        ),
        relation(
            "relation:inactive-x-equals-two",
            "event:inactive",
            0,
            sub(field("x"), const(2)),
            [{"field": "counter", "mode": "add", "value": q(100)}],
            active=(4, 10),
            purpose="Root t=1 lies outside declared active interval.",
        ),
        relation(
            "relation:unsupported-x-equals-five",
            "event:unsupported",
            0,
            sub(field("x"), const(5)),
            [{"field": "counter", "mode": "add", "value": q(100)}],
            support="support:x-below-4",
            purpose="Root exists but lies outside support.",
        ),
        relation(
            "relation:incompatible-x-equals-six",
            "event:incompatible",
            0,
            sub(field("x"), const(6)),
            [{"field": "counter", "mode": "add", "value": q(100)}],
            compatibility="compat:mode-2",
            purpose="Root exists but compatibility predicate rejects it.",
        ),
    ]
    return attach_hash({
        "schema": "TOM-WORLD-INTERVAL-EVENTS-0.3",
        "profile": "TOM-WORLD-QUERY-KERNEL-0.3",
        "seed_sha256": SEED_HASH,
        "trajectory": trajectory,
        "supports": supports,
        "compatibilities": compatibilities,
        "relations": relations,
        "solver": {
            "arithmetic": "exact canonical rational closed intervals",
            "continuity_operations": ["const", "field", "time", "neg", "add", "sub", "mul"],
            "refine_steps": 24,
            "max_refine_steps": 128,
            "simultaneity": "equal exact canonical rational root time",
            "event_order": ["root_time", "priority", "relation_id", "event_id", "relation_hash"],
        },
        "provenance": {
            "date": "2026-09-01",
            "purpose": "0.3 certified interval crossing, simultaneous event-set, ordering, and baseline fixture",
        },
    })


def build_tomagi_reference() -> dict[str, Any]:
    from tomagi.core import Cell, Opcode, Program, State, run
    from tomagi.format import dump

    cell = Cell(0, 0, int(Opcode.KIN2), 0, 0, 0, 0, 0, 0, 0, 0, 0)
    initial = State(rho=0, tick=0, vrho=2, vtick=1)
    program = Program([cell], 0, 0x57303330, 10, initial, 0)
    tmg = EXAMPLE / "affine_reference.tmg"
    dump(program, tmg)
    final_state, trace = run(program, ticks=10, trace=True)
    py_record = {
        "schema": "TOM-AFFINE-REFERENCE-PYTHON-TRACE-0.3",
        "program_sha256": sha256(tmg),
        "initial_state": {name: getattr(initial, name) for name in initial.__dataclass_fields__},
        "final_state": {name: getattr(final_state, name) for name in final_state.__dataclass_fields__},
        "trace": trace,
    }
    write_canonical(VALIDATION / "affine_reference.python.trace.json", py_record)

    c_exe = ROOT / "build/tomagi-c"
    if not c_exe.exists():
        c_exe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            os.environ.get("CC", "cc"), "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c", "-o", str(c_exe),
        ], cwd=ROOT, check=True)
    c_raw = subprocess.check_output([str(c_exe), str(tmg), "--trace-json"], cwd=ROOT)
    c_record = json.loads(c_raw.decode("utf-8"))
    write_canonical(VALIDATION / "affine_reference.c.trace.json", c_record)

    # Existing C CLI shape is {state, trace}; compare against the oracle trace and
    # final state while retaining the richer Python wrapper separately.
    py_core = {"state": py_record["final_state"], "trace": trace}
    backend_equal = c_record == py_core
    anchors = [{"tick": 0, "rho": 0, "state_tick": 0}]
    for item in trace:
        anchors.append({
            "tick": int(item["step"]) + 1,
            "rho": int(item["rho"]),
            "state_tick": int(item["tick"]),
        })
    return {
        "program": str(tmg.relative_to(ROOT)),
        "program_sha256": sha256(tmg),
        "program_bytes": tmg.stat().st_size,
        "python_c_full_trace_equal": backend_equal,
        "anchors": anchors,
        "anchor_rule": "rho=2*tick and State64.tick=tick for integer ticks 0..10",
        "anchors_valid": all(a["rho"] == 2 * a["tick"] and a["state_tick"] == a["tick"] for a in anchors),
    }


def main() -> None:
    # The checked-in JSON file is the authoritative literal world definition.
    # The Python constructor is only a deterministic maintenance helper and is
    # invoked explicitly with TOM_WORLD03_REFRESH_SOURCE=1.  Ordinary builds
    # never replace the literal source with hidden host-side semantics.
    world_path = EXAMPLE / "interval_event_world.json"
    if os.environ.get("TOM_WORLD03_REFRESH_SOURCE") == "1":
        world_record = build_world_record()
        world_path.write_text(json.dumps(world_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not world_path.is_file():
        raise FileNotFoundError(f"missing literal interval world source: {world_path}")
    raw, world = load_world(world_path)

    crossing_relation = next(r for r in world.relations if r.id == "relation:x-equals-five")
    crossing = certify_crossing(world, crossing_relation, ClosedInterval(Q(2), Q(3)))
    write_canonical(VALIDATION / "certified_crossing_x5.json", crossing.certificate)

    events = events_certificate(world, 0, 10)
    write_canonical(VALIDATION / "events_0_10.json", events)

    event_set = next_event_set(world, 0, 10)
    write_canonical(VALIDATION / "next_event_set.json", event_set)

    transition = apply_event_set(world, event_set)
    write_canonical(VALIDATION / "simultaneous_transition.json", transition)

    baseline = trusted_affine_baseline(raw, 0, 10)
    solver_events = [
        {
            "relation_id": event["relation_id"],
            "event_id": event["event_id"],
            "priority": event["priority"],
            "root": event["exact_root_time"],
        }
        for event in events["events"] if event["exact_root_time"] is not None
    ]
    baseline_comparison = attach_hash({
        "schema": "TOM-INTERVAL-BASELINE-COMPARISON-0.3",
        "world_hash": world.content_hash,
        "solver_event_count": len(solver_events),
        "baseline_event_count": len(baseline["events"]),
        "solver_events": solver_events,
        "baseline_events": baseline["events"],
        "equal": solver_events == baseline["events"],
        "solver_events_hash": events["content_hash"],
        "trusted_baseline_hash": baseline["content_hash"],
    })
    write_canonical(VALIDATION / "trusted_baseline_comparison.json", baseline_comparison)

    tomagi_reference = build_tomagi_reference()
    trajectory_anchor_equal = tomagi_reference["anchors_valid"] and all(
        world.trajectory.state_at(Q(anchor["tick"]))["x"] == Q(anchor["rho"])
        and world.trajectory.state_at(Q(anchor["tick"]))["clock"] == Q(anchor["state_tick"])
        for anchor in tomagi_reference["anchors"]
    )
    tomagi_comparison = attach_hash({
        "schema": "TOM-INTERVAL-TOMAGI-TRAJECTORY-COMPARISON-0.3",
        "world_hash": world.content_hash,
        **tomagi_reference,
        "affine_trajectory_matches_all_integer_tomagi_anchors": trajectory_anchor_equal,
    })
    write_canonical(VALIDATION / "tomagi_trajectory_baseline.json", tomagi_comparison)

    # Deterministic simultaneous-transition conflict evidence.  It is not part
    # of the accepted world; it proves that mixed/unequal simultaneous writes do
    # not silently acquire a last-writer-wins policy.
    conflict_relation = Relation(
        id="relation:conflict",
        priority=30,
        expression=sub(field("x"), const(5)),
        support_id="support:main",
        compatibility_id="compat:mode-1",
        active_time=ClosedInterval(Q(0), Q(10)),
        event_id="event:conflict:set-output",
        transition=(TransitionOp("output", "set", Q(99)),),
        content_hash="sha256:" + "0" * 64,
    )
    accepted_relations = [
        next(r for r in world.relations if r.id == ident)
        for ident in event_set["relation_order"]
    ]
    conflict_error = None
    try:
        merge_transition_ops([*accepted_relations, conflict_relation])
    except TransitionConflict as exc:
        conflict_error = str(exc)
    conflict_record = attach_hash({
        "schema": "TOM-SIMULTANEOUS-CONFLICT-REJECTION-0.3",
        "status": "rejected" if conflict_error else "unexpectedly-accepted",
        "error": conflict_error,
        "policy": "unequal simultaneous set values on one field reject",
    })
    write_canonical(VALIDATION / "simultaneous_conflict_rejection.json", conflict_record)

    summary = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-FIXTURE-REPORT",
        "release": "0.3.0",
        "world": {
            "path": str(world_path.relative_to(ROOT)),
            "bytes": world_path.stat().st_size,
            "sha256": sha256(world_path),
            "content_hash": world.content_hash,
            "relations": len(world.relations),
        },
        "certified_crossing": {
            "status": crossing.status,
            "exact_root": None if crossing.exact_root is None else crossing.exact_root.to_record(),
            "unique": crossing.certificate["uniqueness_certified_by_monotonic_derivative"],
            "hash": crossing.certificate["content_hash"],
        },
        "next_event_set": {
            "event_time": event_set["event_time"],
            "event_count": event_set["event_count"],
            "event_order": event_set["event_order"],
            "hash": event_set["content_hash"],
        },
        "simultaneous_transition": {
            "counter": transition["post_state"]["counter"],
            "output": transition["post_state"]["output"],
            "hash": transition["content_hash"],
        },
        "trusted_baseline_equal": baseline_comparison["equal"],
        "tomagi_integer_anchor_equal": trajectory_anchor_equal,
        "python_c_tomagi_trace_equal": tomagi_reference["python_c_full_trace_equal"],
        "conflict_rejection": conflict_error is not None,
    })
    write_canonical(VALIDATION / "fixture_report.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
