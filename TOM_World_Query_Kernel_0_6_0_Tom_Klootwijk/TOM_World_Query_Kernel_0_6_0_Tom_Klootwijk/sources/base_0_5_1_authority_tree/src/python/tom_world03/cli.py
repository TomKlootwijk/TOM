"""Command-line interface for TOM World & Query Kernel 0.3 interval events."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .baseline import trusted_affine_baseline
from .canonical import canonical_bytes
from .interval import ClosedInterval
from .io import load_world
from .rational import Q
from .solver import certify_crossing, events_certificate, next_event_set
from .transitions import apply_event_set


def _emit(value: Any, output: str | None) -> None:
    data = canonical_bytes(value) + b"\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tom-world03", description="Certified rational interval-event queries")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate-world")
    p_validate.add_argument("world")
    p_validate.add_argument("--output")

    p_certify = sub.add_parser("certify-crossing")
    p_certify.add_argument("world")
    p_certify.add_argument("relation")
    p_certify.add_argument("lower")
    p_certify.add_argument("upper")
    p_certify.add_argument("--refine-steps", type=int)
    p_certify.add_argument("--output")

    p_events = sub.add_parser("events")
    p_events.add_argument("world")
    p_events.add_argument("start")
    p_events.add_argument("end")
    p_events.add_argument("--output")

    p_next = sub.add_parser("next-event-set")
    p_next.add_argument("world")
    p_next.add_argument("after")
    p_next.add_argument("before")
    p_next.add_argument("--include-after", action="store_true")
    p_next.add_argument("--output")

    p_apply = sub.add_parser("apply-next-event-set")
    p_apply.add_argument("world")
    p_apply.add_argument("after")
    p_apply.add_argument("before")
    p_apply.add_argument("--output")

    p_baseline = sub.add_parser("compare-baseline")
    p_baseline.add_argument("world")
    p_baseline.add_argument("start")
    p_baseline.add_argument("end")
    p_baseline.add_argument("--output")

    args = parser.parse_args(argv)
    record, world = load_world(args.world)
    if args.command == "validate-world":
        _emit({
            "schema": "TOM-WORLD-VALIDATION-0.3",
            "status": "valid",
            "world_hash": world.content_hash,
            "trajectory": world.trajectory.id,
            "relations": len(world.relations),
        }, args.output)
        return 0
    if args.command == "certify-crossing":
        relation = next((r for r in world.relations if r.id == args.relation), None)
        if relation is None:
            raise SystemExit(f"unknown relation {args.relation}")
        result = certify_crossing(
            world, relation, ClosedInterval(Q.from_value(args.lower), Q.from_value(args.upper)),
            refine_steps=args.refine_steps,
        )
        _emit(result.certificate, args.output)
        return 0
    if args.command == "events":
        _emit(events_certificate(world, args.start, args.end), args.output)
        return 0
    if args.command == "next-event-set":
        _emit(next_event_set(world, args.after, args.before, include_after=args.include_after), args.output)
        return 0
    if args.command == "apply-next-event-set":
        event_set = next_event_set(world, args.after, args.before)
        _emit(apply_event_set(world, event_set), args.output)
        return 0
    if args.command == "compare-baseline":
        baseline = trusted_affine_baseline(record, args.start, args.end)
        solver = events_certificate(world, args.start, args.end)
        solver_events = [
            {
                "relation_id": event["relation_id"],
                "event_id": event["event_id"],
                "priority": event["priority"],
                "root": event["exact_root_time"],
            }
            for event in solver["events"] if event["exact_root_time"] is not None
        ]
        result = {
            "schema": "TOM-INTERVAL-BASELINE-COMPARISON-0.3",
            "world_hash": world.content_hash,
            "equal": solver_events == baseline["events"],
            "solver_events": solver_events,
            "baseline_events": baseline["events"],
            "baseline_hash": baseline["content_hash"],
            "solver_hash": solver["content_hash"],
        }
        _emit(result, args.output)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
