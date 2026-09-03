from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tomagi.canonical import attach_hash as attach_tomagi_hash
from tomagi.compiler import compile_document
from tomagi.core import run
from tomagi.format import dump, load
from tom_world.canonical import attach_hash, canonical_bytes, digest_bytes, digest_file
from tom_world.grammar import GrammarEngine
from tom_world.query import QueryEngine
from tom_world.records import validate_record
from tom_world.seed import verify_seed_bytes
from tom_world.store import TRANSACTION_SCHEMA, WorldStore

EXAMPLE = ROOT / "examples/world_counter"
VALIDATION = ROOT / "validation"
STORE_PATH = ROOT / "world/counter_store"
PROGRAM_SOURCE = EXAMPLE / "counter_program.source.json"
PROGRAM_JSON = EXAMPLE / "counter_program.json"
PROGRAM_TMG = EXAMPLE / "counter_program.tmg"
WORLD_SOURCE = EXAMPLE / "world_source.json"
TRANSACTION = EXAMPLE / "initial_transaction.json"
SEED_PATH = ROOT / "TOM_seed_genome_2026-09-01.txt"


def write_json(path: Path, value: object, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_bytes(canonical_bytes(value) + b"\n")


def prepare_program() -> None:
    source = json.loads(PROGRAM_SOURCE.read_text(encoding="utf-8"))
    output = dict(source)
    output["definitions"] = [
        attach_tomagi_hash({key: value for key, value in definition.items() if key != "content_hash"})
        for definition in source.get("definitions", [])
    ]
    write_json(PROGRAM_JSON, output, pretty=True)
    dump(compile_document(output), PROGRAM_TMG)


def prepare_transaction() -> dict:
    source = json.loads(WORLD_SOURCE.read_text(encoding="utf-8"))
    identity = verify_seed_bytes(SEED_PATH.read_bytes())
    records = []
    for raw in source["records"]:
        record = attach_hash({key: value for key, value in raw.items() if key != "content_hash"})
        validate_record(record)
        records.append(record)
    blobs = []
    for raw in source["blobs"]:
        path = WORLD_SOURCE.parent / raw["path"]
        blobs.append({
            "id": raw["id"],
            "path": raw["path"],
            "media_type": raw.get("media_type", "application/octet-stream"),
            "sha256": digest_file(path),
        })
    transaction = attach_hash({
        "schema": TRANSACTION_SCHEMA,
        "seed_sha256": "sha256:" + identity.sha256,
        "base_commit": None,
        "sequence": 0,
        "message": source["message"],
        "records": records,
        "blobs": blobs,
        "provenance": source["provenance"],
    })
    write_json(TRANSACTION, transaction, pretty=True)
    return transaction


def main() -> int:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    prepare_program()
    transaction = prepare_transaction()
    shutil.rmtree(STORE_PATH, ignore_errors=True)
    store = WorldStore.initialize(STORE_PATH, SEED_PATH.read_bytes())
    initial_commit = store.commit_transaction_file(TRANSACTION)
    write_json(VALIDATION / "counter_initial_commit.json", initial_commit)

    engine = QueryEngine(store)
    state_at = engine.state_at("instance:counter", 3)
    event = engine.next_event("instance:counter", 0, horizon=8)
    if event is None:
        raise RuntimeError("starter next_event did not find the declared event")
    events = engine.events_in_support(
        "instance:counter",
        start_tick=0,
        end_tick=8,
        support_id="support:counter-rho-window",
    )
    compatible = engine.compatible(
        "instance:counter", "instance:peer", "compatibility:same-topology", tick=3
    )
    incompatible = engine.compatible(
        "instance:counter", "instance:odd-peer", "compatibility:same-topology", tick=3
    )
    grammar = GrammarEngine(store).expand("grammar:bounded-binary-branch", depth=3)
    reconstruction = engine.reconstruct(event)

    write_json(VALIDATION / "state_at_3.json", state_at)
    write_json(VALIDATION / "next_event.json", event)
    write_json(VALIDATION / "events_in_support.json", events)
    write_json(VALIDATION / "compatible.json", compatible)
    write_json(VALIDATION / "incompatible.json", incompatible)
    write_json(VALIDATION / "grammar_expansion.json", grammar)
    write_json(VALIDATION / "reconstruction.json", reconstruction)

    program = load(PROGRAM_TMG)
    python_state, python_trace = run(program, ticks=8, trace=True)
    python_record = {
        "state": {name: getattr(python_state, name) for name in python_state.__dataclass_fields__},
        "trace": python_trace,
    }
    write_json(VALIDATION / "counter_python_trace.json", python_record)

    executable = ROOT / "build/tomagi-c"
    if not executable.exists():
        raise RuntimeError("build/tomagi-c is required")
    c_raw = subprocess.check_output(
        [str(executable), str(PROGRAM_TMG), "8", "--trace-json"],
        cwd=ROOT,
    )
    c_record = json.loads(c_raw.decode("utf-8"))
    write_json(VALIDATION / "counter_c_trace.json", c_record)
    backend_equal = canonical_bytes(c_record) == canonical_bytes(python_record)
    if not backend_equal:
        raise RuntimeError("counter Python and C traces differ")

    event_commit = engine.commit_event(event, message="Append verified counter rho=5 event and lineage")
    write_json(VALIDATION / "counter_event_commit.json", event_commit)
    suffix = event["content_hash"][7:23]
    updated = QueryEngine(store)
    lineage_reconstruction = updated.reconstruct("lineage:" + suffix)
    write_json(VALIDATION / "lineage_reconstruction.json", lineage_reconstruction)
    write_json(VALIDATION / "events_list.json", [
        {"id": record["id"], "content_hash": record["content_hash"]}
        for record in store.list_records(record_type="event")
    ])
    write_json(VALIDATION / "lineage_list.json", [
        {"id": record["id"], "content_hash": record["content_hash"]}
        for record in store.list_records(record_type="lineage")
    ])

    checks = {
        "seed_valid": verify_seed_bytes(SEED_PATH.read_bytes()).sha256,
        "state_at_3": state_at["state"]["rho"] == 3 and state_at["state"]["tick"] == 3,
        "next_event_tick": event["event_tick"] == 5,
        "next_event_zero": event["residual"] == 0,
        "support_passed": all(item["accepted"] for item in event["support"]),
        "compatibility_passed": all(item["accepted"] for item in event["compatibility"]),
        "events_in_support": events["event_count"] == 1,
        "pair_compatible": compatible["compatible"] is True,
        "pair_incompatible": incompatible["compatible"] is False,
        "grammar_depth_3": grammar["terminal_symbol_count"] == 29 and grammar["bits_consumed"] == 7,
        "direct_reconstruction": reconstruction["byte_equal"] is True,
        "lineage_reconstruction": lineage_reconstruction["byte_equal"] is True,
        "python_c_trace_equal": backend_equal,
        "event_record_count": len(store.list_records(record_type="event")) == 1,
        "lineage_record_count": len(store.list_records(record_type="lineage")) == 1,
    }
    if not all(value is True or isinstance(value, str) for value in checks.values()):
        raise RuntimeError(f"counter world checks failed: {checks}")
    manifest = attach_hash({
        "schema": "TOM-WORLD-COUNTER-BENCHMARK-MANIFEST-0.1",
        "seed_sha256": "sha256:" + verify_seed_bytes(SEED_PATH.read_bytes()).sha256,
        "program": {
            "source_sha256": digest_file(PROGRAM_SOURCE),
            "compiled_source_sha256": digest_file(PROGRAM_JSON),
            "tmg_sha256": digest_file(PROGRAM_TMG),
            "tmg_bytes": PROGRAM_TMG.stat().st_size,
        },
        "world": {
            "source_sha256": digest_file(WORLD_SOURCE),
            "transaction_sha256": digest_file(TRANSACTION),
            "initial_commit": initial_commit["content_hash"],
            "event_commit": event_commit["content_hash"],
            "head": store.head,
        },
        "certificates": {
            "state_at_3": state_at["content_hash"],
            "next_event": event["content_hash"],
            "events_in_support": events["content_hash"],
            "compatible": compatible["content_hash"],
            "incompatible": incompatible["content_hash"],
            "grammar": grammar["content_hash"],
            "reconstruction": reconstruction["content_hash"],
            "lineage_reconstruction": lineage_reconstruction["content_hash"],
        },
        "checks": checks,
        "status": "pass",
    })
    write_json(VALIDATION / "counter_world_manifest.json", manifest, pretty=True)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
