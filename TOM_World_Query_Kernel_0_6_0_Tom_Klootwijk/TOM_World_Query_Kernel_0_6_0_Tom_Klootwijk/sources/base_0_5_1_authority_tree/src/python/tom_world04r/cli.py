"""Command-line interface for the corrective TOM World & Query Kernel 0.4.1."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from tom_world03.canonical import canonical_bytes
from tom_world03.rational import Q

from .baseline import trusted_piecewise_baseline
from .engine import run_continuation
from .index import build_interval_index
from .io import load_record, load_world
from .journal import ContinuationStore
from .model import OpenSegment
from .solver import next_event_set


def _write(value: Mapping[str, Any] | list[Any], destination: str | None = None) -> None:
    data = canonical_bytes(value) + b"\n"
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(json.dumps(value, indent=2, sort_keys=True))


def _segment(path: str | None, world_initial: OpenSegment) -> OpenSegment:
    if path is None:
        return world_initial
    return OpenSegment.from_record(load_record(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tom-world04r",
        description="Corrective 0.4.1 piecewise continuation kernel based only on corrected 0.3",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate a 0.4.1 world and its immutable interval index")
    p_validate.add_argument("world")

    p_index = sub.add_parser("index", help="rebuild the exact immutable interval index")
    p_index.add_argument("world")
    p_index.add_argument("--output")

    p_next = sub.add_parser("next-event", help="find the next solver-derived event set")
    p_next.add_argument("world")
    p_next.add_argument("--segment", help="optional content-addressed open segment JSON; defaults to initial segment")
    p_next.add_argument("--after")
    p_next.add_argument("--before")
    p_next.add_argument("--planner", choices=("indexed", "exhaustive"), default="indexed")
    p_next.add_argument("--refine-steps", type=int)
    p_next.add_argument("--output")

    p_run = sub.add_parser("run", help="continue a world to its declared horizon")
    p_run.add_argument("world")
    p_run.add_argument("--planner", choices=("indexed", "exhaustive"), default="indexed")
    p_run.add_argument("--max-event-sets", type=int)
    p_run.add_argument("--output")

    p_baseline = sub.add_parser("baseline", help="run the independent stdlib Fraction baseline")
    p_baseline.add_argument("world")
    p_baseline.add_argument("--output")

    p_persist = sub.add_parser("persist", help="initialize a fresh journal and persist the complete continuation")
    p_persist.add_argument("world")
    p_persist.add_argument("store")
    p_persist.add_argument("--planner", choices=("indexed", "exhaustive"), default="indexed")
    p_persist.add_argument("--replace", action="store_true")
    p_persist.add_argument("--output")

    p_audit = sub.add_parser("audit", help="audit every reachable journal object and ancestry link")
    p_audit.add_argument("store")
    p_audit.add_argument("--allow-orphans", action="store_true")
    p_audit.add_argument("--output")

    p_reconstruct = sub.add_parser("reconstruct", help="reconstruct the semantic continuation chain from a journal")
    p_reconstruct.add_argument("store")
    p_reconstruct.add_argument("--output")

    args = parser.parse_args(argv)

    if args.command == "validate":
        raw, world = load_world(args.world)
        _write({
            "schema": "TOM-WORLD-0.4.1-VALIDATION-SUMMARY",
            "status": "valid",
            "world_hash": world.content_hash,
            "world_bytes": len(canonical_bytes(raw)) + 1,
            "relations": len(world.relations),
            "horizon": world.horizon.to_record(),
            "initial_segment_hash": world.initial_segment.content_hash,
            "corrected_v03_zip_sha256": world.corrected_v03_zip_sha256,
            "corrected_interval_sha256": world.corrected_interval_sha256,
            "prior_v0_4_used_as_source": False,
        })
        return 0

    if args.command == "index":
        _, world = load_world(args.world)
        record = build_interval_index(world.relations, seed_sha256=world.seed_sha256)
        _write(record, args.output)
        return 0

    if args.command == "next-event":
        _, world = load_world(args.world)
        segment = _segment(args.segment, world.initial_segment)
        record = next_event_set(
            world,
            segment,
            after=None if args.after is None else Q.from_value(args.after),
            before=None if args.before is None else Q.from_value(args.before),
            planner=args.planner,
            refine_steps=args.refine_steps,
        )
        _write(record, args.output)
        return 0

    if args.command == "run":
        _, world = load_world(args.world)
        result = run_continuation(world, planner=args.planner, max_event_sets=args.max_event_sets)
        _write(dict(result.record), args.output)
        return 0

    if args.command == "baseline":
        raw, _ = load_world(args.world)
        _write(trusted_piecewise_baseline(raw), args.output)
        return 0

    if args.command == "persist":
        raw, world = load_world(args.world)
        store_path = Path(args.store)
        if store_path.exists() and args.replace:
            shutil.rmtree(store_path)
        store = ContinuationStore.initialize(
            store_path,
            Path(args.world).resolve().parents[2].joinpath("TOM_seed_genome_2026-09-01.txt").read_bytes()
            if Path(args.world).resolve().parents[2].joinpath("TOM_seed_genome_2026-09-01.txt").exists()
            else Path("TOM_seed_genome_2026-09-01.txt").read_bytes(),
            raw,
            world,
        )
        result = run_continuation(world, planner=args.planner, store=store)
        _write({
            "schema": "TOM-WORLD-0.4.1-PERSISTED-RUN",
            "run": dict(result.record),
            "audit": store.audit(),
            "reconstruction": store.reconstruct(),
        }, args.output)
        return 0

    if args.command == "audit":
        store = ContinuationStore(args.store)
        record = store.audit(require_no_orphans=not args.allow_orphans)
        _write(record, args.output)
        return 0 if record["valid"] else 1

    if args.command == "reconstruct":
        store = ContinuationStore(args.store)
        _write(store.reconstruct(), args.output)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
