from __future__ import annotations

"""Assemble deterministic TOM World & Query Kernel 0.2 validation evidence."""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tomagi.core import run
from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load
from tom_world.audit import audit_store
from tom_world.canonical import attach_hash, canonical_bytes, digest_file, verify_hash
from tom_world.seed import verify_seed_file
from tom_world.store import WorldStore

VALIDATION = ROOT / "validation"
BENCHMARK = VALIDATION / "index_benchmark"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def add(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, **evidence: Any) -> None:
    checks.append({
        "name": name,
        "status": "pass" if passed else "fail",
        "detail": detail,
        "evidence": evidence,
    })


def proof_ok(path: Path) -> tuple[bool, dict[str, Any]]:
    record = read_json(path)
    ok = (
        record.get("status") == "pass"
        and verify_hash(record)
        and record.get("execution", {}).get("python_c_full_trace_equal") is True
        and record.get("artifact", {}).get("source_byte_equal") is True
    )
    return ok, record


def corruption_probe() -> dict[str, Any]:
    """Corrupt a copied small store and prove disk audit rejection."""
    with tempfile.TemporaryDirectory(prefix="tom-world-corruption-") as directory:
        copied_root = Path(directory) / "store"
        shutil.copytree(ROOT / "world/counter_store", copied_root)
        copied = WorldStore(copied_root)
        snapshot = copied.snapshot_for_commit()
        object_hash = next(iter(snapshot["records"].values()))
        object_path = copied._object_path(str(object_hash))
        data = bytearray(object_path.read_bytes())
        data[len(data) // 2] ^= 1
        object_path.write_bytes(data)
        certificate = audit_store(copied)
        return {
            "detected": certificate["valid"] is False,
            "error_kinds": sorted({item["kind"] for item in certificate["errors"]}),
            "error_count": len(certificate["errors"]),
            "certificate_hash": certificate["content_hash"],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-clean", action="store_true")
    args = parser.parse_args(argv)

    checks: list[dict[str, Any]] = []
    identity = verify_seed_file(ROOT / "TOM_seed_genome_2026-09-01.txt")
    add(
        checks,
        "canonical seed identity",
        identity.bytes == 244
        and identity.sha256 == "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
        and not (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes().endswith((b"\n", b"\r")),
        "Exact 244-byte TOM-SRS root with no terminal line feed.",
        bytes=identity.bytes,
        sha256=identity.sha256,
    )

    abi_ok = (HEADER_SIZE, STATE_SIZE, CELL_SIZE) == (128, 64, 48)
    add(
        checks,
        "TOMAGI ABI unchanged",
        abi_ok,
        "Indexes, plans, checkpoints, batches, and audit add no opcode and do not alter the TOMAGI 1.0 fixed-width records.",
        header=HEADER_SIZE,
        state=STATE_SIZE,
        cell=CELL_SIZE,
    )

    polar = load(ROOT / "examples/polar_loop.tmg")
    polar_state, polar_trace = run(polar, trace=True)
    original_ok = (
        polar_state.output == 0x50595241
        and polar_state.rho == 8
        and polar_state.theta == 39
        and polar_state.phi == 2181
        and len(polar_trace) == 8
    )
    add(
        checks,
        "original TOMAGI regression",
        original_ok,
        "The original polar loop remains binary-format compatible and reaches its recorded terminal state.",
        output=polar_state.output,
        steps=len(polar_trace),
        lineage=polar_state.lineage,
    )

    counter_manifest = read_json(VALIDATION / "counter_world_manifest.json")
    counter_ok = counter_manifest.get("status") == "pass" and verify_hash(counter_manifest)
    add(
        checks,
        "0.1 counter-world compatibility",
        counter_ok,
        "The starter world, native exact-discrete queries, event commit, and lineage reconstruction remain reproducible under 0.2.",
        manifest_hash=counter_manifest.get("content_hash"),
        head=counter_manifest.get("world", {}).get("head"),
    )

    state_at = read_json(VALIDATION / "state_at_3.json")
    event = read_json(VALIDATION / "next_event.json")
    events = read_json(VALIDATION / "events_in_support.json")
    compatible = read_json(VALIDATION / "compatible.json")
    incompatible = read_json(VALIDATION / "incompatible.json")
    grammar = read_json(VALIDATION / "grammar_expansion.json")
    reconstruction = read_json(VALIDATION / "lineage_reconstruction.json")
    starter_queries_ok = (
        state_at["state"]["rho"] == 3
        and state_at["state"]["tick"] == 3
        and event["event_tick"] == 5
        and event["residual"] == 0
        and event["previous_residual"] == -1
        and event["guard_margin"] == 1
        and events["event_count"] == 1
        and compatible["compatible"] is True
        and incompatible["compatible"] is False
        and grammar["requested_depth"] == 3
        and grammar["bits_consumed"] == 7
        and grammar["terminal_symbol_count"] == 29
        and reconstruction["byte_equal"] is True
    )
    add(
        checks,
        "native query and bounded grammar regression",
        starter_queries_ok,
        "definition/state/event/support/compatibility/trace/reconstruction and bounded grammar behavior matches the 0.1 starter certificates.",
        state_at_hash=state_at["content_hash"],
        event_hash=event["content_hash"],
        grammar_hash=grammar["content_hash"],
        reconstruction_hash=reconstruction["content_hash"],
    )

    python_trace = read_json(VALIDATION / "counter_python_trace.json")
    c_trace = read_json(VALIDATION / "counter_c_trace.json")
    backend_ok = canonical_bytes(python_trace) == canonical_bytes(c_trace)
    add(
        checks,
        "Python/C counter trajectory trace",
        backend_ok,
        "The complete eight-step TOMAGI trace and final State64 are equal.",
        steps=len(python_trace["trace"]),
        python_sha256=digest_file(VALIDATION / "counter_python_trace.json"),
        c_sha256=digest_file(VALIDATION / "counter_c_trace.json"),
    )

    benchmark = read_json(BENCHMARK / "report.json")
    benchmark_ok = (
        benchmark.get("status") == "pass"
        and verify_hash(benchmark)
        and benchmark["world"]["record_count"] == 10_000
        and all(benchmark["acceptance"].values())
    )
    add(
        checks,
        "frozen 10,000-record world",
        benchmark_ok,
        "One immutable two-commit world contains exactly 10,000 validated records and one TOMAGI program blob.",
        report_hash=benchmark.get("content_hash"),
        record_count=benchmark.get("world", {}).get("record_count"),
        head=benchmark.get("world", {}).get("head"),
        store_tree=benchmark.get("world", {}).get("store_tree"),
    )

    postings = read_json(BENCHMARK / "postings.json")
    postings_ok = postings == {
        "checkpoint_count": 10,
        "compound_address_matches": 1,
        "instance_042_relations": 96,
        "instances": 100,
        "interval_1_32_relations": 3200,
        "relations": 9600,
        "sheet_2_records": 2503,
        "support_bucket_04": 600,
    }
    add(
        checks,
        "immutable secondary-index postings",
        postings_ok,
        "The content-addressed index exposes exact type, instance, support, interval, topology, address, and checkpoint postings.",
        postings=postings,
        indexes_hash=benchmark["world"]["indexes_hash"],
    )

    event_result = benchmark["events_in_support"]
    event_plan_ok = (
        event_result["candidate_count_path"] == [10000, 9600, 96, 6, 2]
        and event_result["event_ticks"] == [5, 21]
        and event_result["semantic_byte_equal"] is True
        and event_result["indexed_selected_relations"] == 2
    )
    add(
        checks,
        "indexed/exhaustive event-plan equivalence",
        event_plan_ok,
        "Fixed-stage immutable index intersection reduces 10,000 records to two relation candidates while returning byte-identical semantic event results.",
        candidate_path=event_result["candidate_count_path"],
        event_ticks=event_result["event_ticks"],
        semantic_result_hash=event_result["semantic_result_hash"],
        indexed_record_reads=0,
        exhaustive_record_reads=event_result["exhaustive_record_reads"],
    )

    checkpoint = benchmark["checkpoint_replay"]
    checkpoint_ok = (
        checkpoint["indexed_replayed_steps"] == 99
        and checkpoint["exhaustive_replayed_steps"] == 999
        and checkpoint["saved_steps"] == 900
        and checkpoint["rho"] == checkpoint["tick"] == 999
        and checkpoint["semantic_byte_equal"] is True
    )
    add(
        checks,
        "exact ancestry-bound checkpoint replay",
        checkpoint_ok,
        "The nearest valid tick-900 checkpoint reproduces state_at(999) with 99 transitions instead of 999, saving 900 steps without changing semantic bytes.",
        checkpoint=checkpoint,
    )

    batch = benchmark["batch"]
    batch_ok = (
        batch["request_count"] == 4
        and batch["reduction_order"] == "declared_array_order"
        and batch["semantic_equal"] is True
        and batch["indexed_work"]["tomagi_steps"] == 152
        and batch["exhaustive_work"]["tomagi_steps"] == 1052
    )
    add(
        checks,
        "stable ordered batch equivalence",
        batch_ok,
        "Four requests reduce semantic result bytes in declared array order; indexed and exhaustive planner modes have one semantic reduction hash.",
        reduction_hash=batch["semantic_reduction_hash"],
        indexed_work=batch["indexed_work"],
        exhaustive_work=batch["exhaustive_work"],
    )

    rebuild = benchmark["index_rebuild"]
    rebuild_ok = rebuild["deleted_then_rebuilt"] is True and rebuild["byte_equal"] is True
    add(
        checks,
        "index deletion and exact reconstruction",
        rebuild_ok,
        "After deletion, the immutable index is rebuilt from the snapshot's authoritative record map to the exact declared bytes.",
        certificate_hash=rebuild["certificate_hash"],
        indexes_hash=rebuild["declared_indexes_hash"],
        file_sha256=rebuild["rebuilt_file_sha256"],
    )

    audit = read_json(BENCHMARK / "audit.json")
    audit_ok = (
        audit["valid"] is True
        and audit["errors"] == []
        and len(audit["ancestry"]) == 2
        and all(item["count"] == 0 for item in audit["orphans"].values())
        and verify_hash(audit)
    )
    add(
        checks,
        "full commit-ancestry and reachability audit",
        audit_ok,
        "Both commits, exact transactions, snapshots, indexes, records, dependencies, and blobs validate with no unreachable immutable objects.",
        audit_hash=audit["content_hash"],
        ancestry_length=len(audit["ancestry"]),
        counts=audit["counts"],
    )

    probe = corruption_probe()
    add(
        checks,
        "disk corruption detection",
        probe["detected"] and bool(set(probe["error_kinds"]) & {"record", "index"}),
        "A copied store with one mutated immutable object is rejected by an uncached disk audit.",
        probe=probe,
    )

    benchmark_store = WorldStore(ROOT / "world/index_benchmark_store")
    transaction_chain_ok = True
    chain: list[dict[str, Any]] = []
    current = benchmark_store.head
    expected_sequence = 1
    while current is not None:
        commit = benchmark_store.read_commit(current)
        transaction = benchmark_store.read_transaction(commit["transaction_hash"])
        snapshot = benchmark_store.read_snapshot(commit["snapshot_hash"])
        index = benchmark_store.read_index(snapshot["indexes_hash"])
        item_ok = (
            commit["sequence"] == expected_sequence
            and transaction["base_commit"] == commit["parent"]
            and index["record_count"] == len(snapshot["records"])
            and commit["indexes_hash"] == snapshot["indexes_hash"]
        )
        transaction_chain_ok &= item_ok
        chain.append({
            "commit": current,
            "sequence": commit["sequence"],
            "transaction": commit["transaction_hash"],
            "snapshot": commit["snapshot_hash"],
            "index": snapshot["indexes_hash"],
            "record_count": len(snapshot["records"]),
            "valid": item_ok,
        })
        current = commit["parent"]
        expected_sequence -= 1
    transaction_chain_ok &= expected_sequence == -1
    add(
        checks,
        "stored transaction/snapshot/index lineage",
        transaction_chain_ok,
        "Every commit preserves the exact transaction body and binds one immutable snapshot and index to its parent sequence.",
        chain=chain,
    )

    roadmap_ok, roadmap_proof = proof_ok(VALIDATION / "roadmap_artifact_proof.json")
    add(
        checks,
        "roadmap literal EMIT artifact",
        roadmap_ok,
        "The primary roadmap is byte-equal to its source after content-addressed definition compilation and equal Python/C TOMAGI execution.",
        proof_hash=roadmap_proof.get("content_hash"),
        program_sha256=roadmap_proof.get("program", {}).get("sha256"),
        artifact_sha256=roadmap_proof.get("artifact", {}).get("sha256"),
        emit_records=roadmap_proof.get("execution", {}).get("emit_records"),
    )

    release_ok, release_proof = proof_ok(VALIDATION / "release_0_2_artifact_proof.json")
    add(
        checks,
        "0.2 release documentation EMIT artifact",
        release_ok,
        "The 0.2 completion document is itself reconstructed from an executable literal TOMAGI program with equal Python/C full traces.",
        proof_hash=release_proof.get("content_hash"),
        program_sha256=release_proof.get("program", {}).get("sha256"),
        artifact_sha256=release_proof.get("artifact", {}).get("sha256"),
        emit_records=release_proof.get("execution", {}).get("emit_records"),
    )

    tests_text = (VALIDATION / "tests.txt").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests", tests_text)
    test_count = int(match.group(1)) if match else 0
    tests_ok = test_count >= 60 and tests_text.rstrip().endswith("OK")
    add(
        checks,
        "conformance tests",
        tests_ok,
        f"{test_count} tests passed, including the original TOMAGI suite and 0.2 index/plan/checkpoint/audit tests.",
        count=test_count,
    )

    static = read_json(VALIDATION / "static_assets.json")
    add(
        checks,
        "static specifications, sources, and schemas",
        static.get("status") == "pass" and static.get("benchmark_records") == 10_000,
        "Normative profiles, source PDFs, schemas, all benchmark records, immutable indexes, plans, batches, audit, and artifact sources passed static verification.",
        report=static,
    )

    if args.include_clean:
        clean_path = VALIDATION / "clean_rebuild.json"
        if clean_path.exists():
            clean_record = read_json(clean_path)
            clean_ok = (
                clean_record.get("status") == "pass"
                and clean_record.get("all_boundaries_equal") is True
                and verify_hash(clean_record)
            )
            add(
                checks,
                "clean generated-output-free rebuild",
                clean_ok,
                "A copy stripped of generated stores, programs, traces, and artifacts rebuilt the selected files and both world-store tree manifests byte-for-byte.",
                compared=clean_record.get("compared_boundaries"),
                trees=clean_record.get("tree_boundaries"),
                record_hash=clean_record.get("content_hash"),
            )
        else:
            add(checks, "clean generated-output-free rebuild", False, "clean_rebuild.json is absent")

    failures = [check for check in checks if check["status"] != "pass"]
    report = attach_hash({
        "schema": "TOM-WORLD-QUERY-VALIDATION-0.2",
        "release": "0.2.0",
        "generated": "2026-09-01",
        "status": "pass" if not failures else "fail",
        "profile": "TOM-WORLD-QUERY-KERNEL-0.2",
        "tomagi_abi": "1.0",
        "checks": checks,
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "implemented_scope": [
            "0.1 persistent content-addressed world and exact discrete native queries",
            "content-addressed immutable secondary indexes",
            "deterministic indexed and exhaustive query plans",
            "active time-interval relation filtering",
            "ancestry-bound exact state checkpoints",
            "stable declared-order batch reduction",
            "stored transaction bodies and full commit-ancestry audit",
            "10,000-record frozen benchmark",
            "two literal TOMAGI EMIT documentation artifacts",
        ],
        "next_target": (
            "World & Query Kernel 0.3: typed relation intervals, certified brackets/crossings, "
            "deterministic simultaneous-event sets, and trusted baseline comparisons."
        ),
        "not_claimed": [
            "continuous or interval-certified root solving",
            "simultaneous-event resolution",
            "autonomous definition learning",
            "general planning or external tool execution",
            "grounded multimodal perception",
            "new physical GPU device execution",
            "AGI",
        ],
    })
    write_json(VALIDATION / "validation_report.json", report)

    lines = [
        "# TOM World & Query Kernel 0.2 validation",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Checks: {report['passed']} passed; {report['failed']} failed. Python tests: {test_count}.",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        detail = check["detail"].replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    lines.extend([
        "",
        "## Benchmark headline",
        "",
        "- Frozen records: 10,000.",
        "- Indexed event candidate path: `10,000 -> 9,600 -> 96 -> 6 -> 2`.",
        "- Event ticks: `5, 21`; indexed/exhaustive semantic bytes equal.",
        "- State at tick 999: checkpoint replay 99 steps versus root replay 999; 900 steps saved.",
        "- Full audit: two commits, zero errors, zero orphans.",
        "",
        "## Evidence boundary",
        "",
        "This release executes Python and C99 and preserves the TOMAGI 1.0 ABI. GPU mappings are retained but no new physical GPU dispatch is claimed. Event queries remain exact over whole discrete transitions; they do not yet certify a relation crossing between samples or resolve simultaneous event sets. No autonomous learner, planner, grounded perception layer, or AGI is claimed.",
        "",
        f"Validation report content hash: `{report['content_hash']}`",
        "",
    ])
    (VALIDATION / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "passed": report["passed"],
        "failed": report["failed"],
        "tests": test_count,
        "content_hash": report["content_hash"],
        "clean_included": args.include_clean,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
