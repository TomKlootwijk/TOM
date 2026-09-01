from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .artifact import (
    compile_literal_artifact_file,
    make_literal_artifact_source,
    materialize_literal_artifact_file,
)
from .audit import audit_store
from .canonical import canonical_bytes
from .grammar import GrammarEngine
from .query import QueryEngine
from .store import WorldStore


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _context(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("context file must contain a JSON object")
    return value


def _engine(args: argparse.Namespace) -> QueryEngine:
    return QueryEngine(
        WorldStore(args.store),
        commit=getattr(args, "commit_hash", None),
        planner_mode=getattr(args, "planner", "indexed"),
        use_checkpoints=not getattr(args, "no_checkpoints", False),
    )


def _add_planner_arguments(parser: argparse.ArgumentParser, *, checkpoints: bool = True) -> None:
    parser.add_argument("--planner", choices=["indexed", "exhaustive"], default="indexed")
    parser.add_argument("--plan", action="store_true", help="return the deterministic plan wrapper")
    if checkpoints:
        parser.add_argument("--no-checkpoints", action="store_true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tom-world",
        description="TOM World & Query Kernel 0.2 over TOMAGI 1.0",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="initialize a 0.2 world store from the canonical TOM seed")
    p.add_argument("store")
    p.add_argument("--seed", required=True)
    p.add_argument("--overwrite", action="store_true")

    p = sub.add_parser("commit", help="commit a content-addressed world transaction")
    p.add_argument("store")
    p.add_argument("transaction")

    p = sub.add_parser("list", help="list records in an immutable world commit")
    p.add_argument("store")
    p.add_argument("--type")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("index-query", help="read one immutable secondary-index posting list")
    p.add_argument("store")
    p.add_argument("index", choices=[
        "by_type", "by_dependency", "relation_by_instance", "relation_by_support",
        "relation_by_compatibility", "event_spec_by_relation", "by_generative_address",
        "by_topology_sheet", "definition_by_hash", "by_content_hash",
    ])
    p.add_argument("key")
    p.add_argument("--commit", dest="commit_hash")
    p.add_argument("--integer-key", action="store_true")
    p.add_argument("--json-key", action="store_true")

    p = sub.add_parser("interval-index", help="return records whose declared interval overlaps [start,end]")
    p.add_argument("store")
    p.add_argument("start", type=int)
    p.add_argument("end", type=int)
    p.add_argument("--type", dest="record_type")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("rebuild-indexes", help="rebuild exact index bytes from immutable records")
    p.add_argument("store")
    p.add_argument("--commit", dest="commit_hash")
    p.add_argument("--delete-first", action="store_true")

    p = sub.add_parser("audit", help="audit corruption, immutable indexes, and full commit ancestry")
    p.add_argument("store")
    p.add_argument("--commit", dest="commit_hash")
    p.add_argument("--require-no-orphans", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--output")

    for command, help_text in (
        ("definition-at", "return an exact record by ID"),
        ("verify-definition", "verify a record and its dependencies"),
    ):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("store")
        p.add_argument("id")
        p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("state-at", help="evaluate exact TOMAGI state after N logical transitions")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("tick", type=int)
    p.add_argument("--trace", action="store_true")
    p.add_argument("--commit", dest="commit_hash")
    _add_planner_arguments(p)

    p = sub.add_parser("trace", help="return the complete TOMAGI trace for an instance")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("ticks", type=int)
    p.add_argument("--commit", dest="commit_hash")
    _add_planner_arguments(p)

    p = sub.add_parser("next-event", help="solve the earliest exact discrete zero event")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("after_tick", type=int)
    p.add_argument("--horizon", type=int, default=1024)
    p.add_argument("--relation", action="append", dest="relations")
    p.add_argument("--context")
    p.add_argument("--output")
    p.add_argument("--commit", dest="commit_hash")
    _add_planner_arguments(p)

    p = sub.add_parser("events-in-support", help="return gated events in (start,end]")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("start_tick", type=int)
    p.add_argument("end_tick", type=int)
    p.add_argument("--support")
    p.add_argument("--relation", action="append", dest="relations")
    p.add_argument("--context")
    p.add_argument("--commit", dest="commit_hash")
    _add_planner_arguments(p)

    p = sub.add_parser("compatible", help="evaluate a typed compatibility predicate")
    p.add_argument("store")
    p.add_argument("left_instance")
    p.add_argument("right_instance")
    p.add_argument("compatibility")
    p.add_argument("tick", type=int)
    p.add_argument("--context")
    p.add_argument("--commit", dest="commit_hash")
    _add_planner_arguments(p)

    p = sub.add_parser("make-checkpoint", help="write one exact replay checkpoint record")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("tick", type=int)
    p.add_argument("output")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("commit-checkpoints", help="append exact state checkpoint records")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("ticks", nargs="+", type=int)
    p.add_argument("--message", default="append exact state checkpoints")

    p = sub.add_parser("batch-query", help="execute a finite query batch in declared array order")
    p.add_argument("store")
    p.add_argument("requests")
    p.add_argument("--planner", choices=["indexed", "exhaustive"], default="indexed")
    p.add_argument("--no-checkpoints", action="store_true")
    p.add_argument("--commit", dest="commit_hash")
    p.add_argument("--output")

    p = sub.add_parser("reconstruct", help="replay an event certificate or committed lineage ID")
    p.add_argument("store")
    p.add_argument("certificate_or_id")
    p.add_argument("--commit", dest="commit_hash")
    p.add_argument("--planner", choices=["indexed", "exhaustive"], default="indexed")
    p.add_argument("--no-checkpoints", action="store_true")

    p = sub.add_parser("commit-event", help="append event and lineage records from a certificate")
    p.add_argument("store")
    p.add_argument("certificate")
    p.add_argument("--message", default="commit verified event")

    p = sub.add_parser("expand-grammar", help="expand a finite budgeted grammar")
    p.add_argument("store")
    p.add_argument("grammar")
    p.add_argument("--depth", type=int)
    p.add_argument("--bits", help="explicit bit sequence such as 10110")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("make-artifact-source", help="wrap literal bytes in executable artifact definitions")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--artifact-id", required=True)
    p.add_argument("--media-type", required=True)
    p.add_argument("--seed", required=True)

    p = sub.add_parser("compile-artifact", help="compile executable artifact definitions to .tmg")
    p.add_argument("source")
    p.add_argument("program")
    p.add_argument("--seed", required=True)

    p = sub.add_parser("materialize-artifact", help="execute .tmg and append ordered EMIT payload bytes")
    p.add_argument("program")
    p.add_argument("destination")
    p.add_argument("--trace")
    p.add_argument("--records")

    args = parser.parse_args(argv)

    if args.command == "init":
        store = WorldStore.initialize(args.store, Path(args.seed).read_bytes(), overwrite=args.overwrite)
        _print({"store": str(store.root), "seed": store.validate().as_record(), "head": store.head})
        return 0
    if args.command == "commit":
        _print(WorldStore(args.store).commit_transaction_file(args.transaction))
        return 0
    if args.command == "list":
        store = WorldStore(args.store)
        records = store.list_records(commit=args.commit_hash, record_type=args.type)
        _print([{
            "id": record["id"],
            "record_type": record["record_type"],
            "content_hash": record["content_hash"],
        } for record in records])
        return 0
    if args.command == "index-query":
        key: Any = args.key
        if args.integer_key:
            key = int(args.key, 0)
        elif args.json_key:
            key = json.loads(args.key)
        ids = WorldStore(args.store).indexed_record_ids(args.index, key, commit=args.commit_hash)
        _print({"index": args.index, "key": key, "count": len(ids), "ids": ids})
        return 0
    if args.command == "interval-index":
        ids = WorldStore(args.store).interval_record_ids(
            args.start, args.end, commit=args.commit_hash, record_type=args.record_type
        )
        _print({"interval": [args.start, args.end], "record_type": args.record_type, "count": len(ids), "ids": ids})
        return 0
    if args.command == "rebuild-indexes":
        store = WorldStore(args.store)
        if args.delete_first:
            snapshot = store.snapshot_for_commit(args.commit_hash)
            index_hash = snapshot.get("indexes_hash")
            if index_hash:
                store._index_path(str(index_hash)).unlink(missing_ok=True)
        _print(store.rebuild_indexes(commit=args.commit_hash))
        return 0
    if args.command == "audit":
        certificate = audit_store(
            WorldStore(args.store), commit=args.commit_hash,
            require_no_orphans=args.require_no_orphans, strict=args.strict,
        )
        if args.output:
            Path(args.output).write_bytes(canonical_bytes(certificate) + b"\n")
        _print(certificate)
        return 0 if certificate["valid"] else 1
    if args.command == "definition-at":
        _print(_engine(args).definition_at(args.id))
        return 0
    if args.command == "verify-definition":
        _print(_engine(args).verify_definition(args.id))
        return 0
    if args.command == "state-at":
        engine = _engine(args)
        result = engine.state_at_with_plan(args.instance, args.tick, include_trace=args.trace) if args.plan else engine.state_at(args.instance, args.tick, include_trace=args.trace)
        _print(result)
        return 0
    if args.command == "trace":
        engine = _engine(args)
        result = engine.state_at_with_plan(args.instance, args.ticks, include_trace=True) if args.plan else engine.trace(args.instance, args.ticks)
        _print(result)
        return 0
    if args.command == "next-event":
        engine = _engine(args)
        method = engine.next_event_with_plan if args.plan else engine.next_event
        result = method(
            args.instance, args.after_tick, horizon=args.horizon,
            relation_ids=args.relations, context=_context(args.context),
        )
        if args.output and result is not None:
            Path(args.output).write_bytes(canonical_bytes(result) + b"\n")
        _print(result)
        return 0
    if args.command == "events-in-support":
        engine = _engine(args)
        method = engine.events_in_support_with_plan if args.plan else engine.events_in_support
        _print(method(
            args.instance, start_tick=args.start_tick, end_tick=args.end_tick,
            support_id=args.support, relation_ids=args.relations, context=_context(args.context),
        ))
        return 0
    if args.command == "compatible":
        engine = _engine(args)
        method = engine.compatible_with_plan if args.plan else engine.compatible
        _print(method(
            args.left_instance, args.right_instance, args.compatibility,
            tick=args.tick, context=_context(args.context),
        ))
        return 0
    if args.command == "make-checkpoint":
        record = QueryEngine(WorldStore(args.store), commit=args.commit_hash, use_checkpoints=False).make_checkpoint_record(args.instance, args.tick)
        Path(args.output).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _print({"output": args.output, "id": record["id"], "content_hash": record["content_hash"]})
        return 0
    if args.command == "commit-checkpoints":
        engine = QueryEngine(WorldStore(args.store), use_checkpoints=False)
        _print(engine.commit_checkpoints(args.instance, args.ticks, message=args.message))
        return 0
    if args.command == "batch-query":
        requests = json.loads(Path(args.requests).read_text(encoding="utf-8"))
        if isinstance(requests, dict) and "requests" in requests:
            requests = requests["requests"]
        if not isinstance(requests, list):
            raise ValueError("batch request source must be an array or an object with requests array")
        result = _engine(args).batch(requests, planner_mode=args.planner)
        if args.output:
            Path(args.output).write_bytes(canonical_bytes(result) + b"\n")
        _print(result)
        return 0
    if args.command == "reconstruct":
        path = Path(args.certificate_or_id)
        value: Any = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else args.certificate_or_id
        _print(_engine(args).reconstruct(value))
        return 0
    if args.command == "commit-event":
        certificate = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
        _print(QueryEngine(WorldStore(args.store)).commit_event(certificate, message=args.message))
        return 0
    if args.command == "expand-grammar":
        bits = None if args.bits is None else [int(character) for character in args.bits]
        _print(GrammarEngine(WorldStore(args.store), commit=args.commit_hash).expand(
            args.grammar, depth=args.depth, branch_bits=bits,
        ))
        return 0
    if args.command == "make-artifact-source":
        source = make_literal_artifact_source(
            args.artifact_id, Path(args.input).read_bytes(), media_type=args.media_type,
            seed_bytes=Path(args.seed).read_bytes(), provenance={"source_path": str(args.input)},
        )
        Path(args.output).write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _print({"source": args.output, "content_hash": source["content_hash"]})
        return 0
    if args.command == "compile-artifact":
        _print(compile_literal_artifact_file(args.source, args.seed, args.program))
        return 0
    if args.command == "materialize-artifact":
        _print(materialize_literal_artifact_file(
            args.program, args.destination, trace_path=args.trace, records_path=args.records,
        ))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
