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
from .canonical import canonical_bytes
from .grammar import GrammarEngine
from .query import QueryEngine
from .store import WorldStore


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _context(path: str | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("context must be a JSON object")
    return value


def _engine(args: argparse.Namespace) -> QueryEngine:
    return QueryEngine(WorldStore(args.store), commit=getattr(args, "commit_hash", None))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tom-world",
        description="TOM World & Query Kernel 0.1 over TOMAGI 1.0",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="initialize a world store from the canonical TOM seed")
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

    for command, help_text in (
        ("definition-at", "return an exact record by ID"),
        ("verify-definition", "verify a record and its dependencies"),
    ):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("store")
        p.add_argument("id")
        p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("state-at", help="evaluate exact TOMAGI state after N transitions")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("tick", type=int)
    p.add_argument("--trace", action="store_true")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("trace", help="return the complete TOMAGI trace for an instance")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("ticks", type=int)
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("next-event", help="solve the earliest exact discrete zero event")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("after_tick", type=int)
    p.add_argument("--horizon", type=int, default=1024)
    p.add_argument("--relation", action="append", dest="relations")
    p.add_argument("--context")
    p.add_argument("--output")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("events-in-support", help="return gated events in (start,end]")
    p.add_argument("store")
    p.add_argument("instance")
    p.add_argument("start_tick", type=int)
    p.add_argument("end_tick", type=int)
    p.add_argument("--support")
    p.add_argument("--relation", action="append", dest="relations")
    p.add_argument("--context")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("compatible", help="evaluate a typed compatibility predicate")
    p.add_argument("store")
    p.add_argument("left_instance")
    p.add_argument("right_instance")
    p.add_argument("compatibility")
    p.add_argument("tick", type=int)
    p.add_argument("--context")
    p.add_argument("--commit", dest="commit_hash")

    p = sub.add_parser("reconstruct", help="replay an event certificate or committed lineage ID")
    p.add_argument("store")
    p.add_argument("certificate_or_id")
    p.add_argument("--commit", dest="commit_hash")

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
        store = WorldStore.initialize(
            args.store,
            Path(args.seed).read_bytes(),
            overwrite=args.overwrite,
        )
        _print({"store": str(store.root), "seed": store.validate().as_record(), "head": store.head})
        return 0
    if args.command == "commit":
        commit = WorldStore(args.store).commit_transaction_file(args.transaction)
        _print(commit)
        return 0
    if args.command == "list":
        records = _engine(args).store.list_records(commit=args.commit_hash, record_type=args.type)
        _print([{
            "id": record["id"],
            "record_type": record["record_type"],
            "content_hash": record["content_hash"],
        } for record in records])
        return 0
    if args.command == "definition-at":
        _print(_engine(args).definition_at(args.id))
        return 0
    if args.command == "verify-definition":
        _print(_engine(args).verify_definition(args.id))
        return 0
    if args.command == "state-at":
        _print(_engine(args).state_at(args.instance, args.tick, include_trace=args.trace))
        return 0
    if args.command == "trace":
        _print(_engine(args).trace(args.instance, args.ticks))
        return 0
    if args.command == "next-event":
        result = _engine(args).next_event(
            args.instance,
            args.after_tick,
            horizon=args.horizon,
            relation_ids=args.relations,
            context=_context(args.context),
        )
        if args.output and result is not None:
            Path(args.output).write_bytes(canonical_bytes(result) + b"\n")
        _print(result)
        return 0
    if args.command == "events-in-support":
        _print(_engine(args).events_in_support(
            args.instance,
            start_tick=args.start_tick,
            end_tick=args.end_tick,
            support_id=args.support,
            relation_ids=args.relations,
            context=_context(args.context),
        ))
        return 0
    if args.command == "compatible":
        _print(_engine(args).compatible(
            args.left_instance,
            args.right_instance,
            args.compatibility,
            tick=args.tick,
            context=_context(args.context),
        ))
        return 0
    if args.command == "reconstruct":
        path = Path(args.certificate_or_id)
        value: Any
        if path.is_file():
            value = json.loads(path.read_text(encoding="utf-8"))
        else:
            value = args.certificate_or_id
        _print(_engine(args).reconstruct(value))
        return 0
    if args.command == "commit-event":
        certificate = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
        engine = QueryEngine(WorldStore(args.store))
        _print(engine.commit_event(certificate, message=args.message))
        return 0
    if args.command == "expand-grammar":
        bits = None if args.bits is None else [int(character) for character in args.bits]
        _print(GrammarEngine(WorldStore(args.store), commit=args.commit_hash).expand(
            args.grammar,
            depth=args.depth,
            branch_bits=bits,
        ))
        return 0
    if args.command == "make-artifact-source":
        source = make_literal_artifact_source(
            args.artifact_id,
            Path(args.input).read_bytes(),
            media_type=args.media_type,
            seed_bytes=Path(args.seed).read_bytes(),
            provenance={"source_path": str(args.input)},
        )
        Path(args.output).write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _print({"source": args.output, "content_hash": source["content_hash"]})
        return 0
    if args.command == "compile-artifact":
        _print(compile_literal_artifact_file(args.source, args.seed, args.program))
        return 0
    if args.command == "materialize-artifact":
        _print(materialize_literal_artifact_file(
            args.program,
            args.destination,
            trace_path=args.trace,
            records_path=args.records,
        ))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
