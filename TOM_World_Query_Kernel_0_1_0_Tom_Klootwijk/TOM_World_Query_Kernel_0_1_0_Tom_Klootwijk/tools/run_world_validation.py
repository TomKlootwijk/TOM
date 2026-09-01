from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tomagi.core import Program, State, run
from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load
from tom_world.canonical import attach_hash, canonical_bytes, digest_file, verify_hash
from tom_world.seed import verify_seed_file
from tom_world.store import WorldStore

VALIDATION = ROOT / "validation"


def write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def add(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, **evidence: Any) -> None:
    checks.append({
        "name": name,
        "status": "pass" if passed else "fail",
        "detail": detail,
        "evidence": evidence,
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-clean", action="store_true")
    args = parser.parse_args(argv)

    checks: list[dict[str, Any]] = []
    identity = verify_seed_file(ROOT / "TOM_seed_genome_2026-09-01.txt")
    add(
        checks,
        "canonical seed identity",
        identity.bytes == 244 and identity.sha256 == "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
        "Exact 244-byte TOM-SRS root with no terminal line feed.",
        bytes=identity.bytes,
        sha256=identity.sha256,
    )

    abi_ok = (HEADER_SIZE, STATE_SIZE, CELL_SIZE) == (128, 64, 48)
    add(checks, "TOMAGI ABI unchanged", abi_ok, "World/query code does not alter the TOMAGI 1.0 record sizes.",
        header=HEADER_SIZE, state=STATE_SIZE, cell=CELL_SIZE)

    polar = load(ROOT / "examples/polar_loop.tmg")
    polar_state, polar_trace = run(polar, trace=True)
    original_ok = (
        polar_state.output == 0x50595241
        and polar_state.rho == 8
        and polar_state.theta == 39
        and polar_state.phi == 2181
        and len(polar_trace) == 8
    )
    add(checks, "original TOMAGI regression", original_ok,
        "The original polar loop remains byte-format compatible and reaches its recorded terminal values.",
        output=polar_state.output, steps=len(polar_trace), lineage=polar_state.lineage)

    counter_manifest = json.loads((VALIDATION / "counter_world_manifest.json").read_text())
    counter_ok = counter_manifest.get("status") == "pass" and verify_hash(counter_manifest)
    add(checks, "counter world build", counter_ok,
        "Literal program/world sources reproduced a committed content-addressed world and all starter certificates.",
        manifest_hash=counter_manifest.get("content_hash"), head=counter_manifest.get("world", {}).get("head"))

    state_at = json.loads((VALIDATION / "state_at_3.json").read_text())
    state_ok = state_at["state"]["rho"] == 3 and state_at["state"]["tick"] == 3
    add(checks, "state_at", state_ok, "Exact replay index 3 returns rho=3 and stored tick=3.",
        certificate_hash=state_at["content_hash"])

    event = json.loads((VALIDATION / "next_event.json").read_text())
    event_ok = (
        event["event_tick"] == 5
        and event["residual"] == 0
        and event["previous_residual"] == -1
        and event["guard_margin"] == 1
        and event["post_state"]["output"] == 5
        and all(item["accepted"] for item in event["support"])
        and all(item["accepted"] for item in event["compatibility"])
        and verify_hash(event)
    )
    add(checks, "next_event", event_ok,
        "The exact discrete solver found the first gated zero event at replay index 5.",
        certificate_hash=event["content_hash"], solver=event["solver_status"])

    events = json.loads((VALIDATION / "events_in_support.json").read_text())
    add(checks, "events_in_support", events["event_count"] == 1,
        "The declared support selects one event in (0,8].", certificate_hash=events["content_hash"])

    compatible = json.loads((VALIDATION / "compatible.json").read_text())
    incompatible = json.loads((VALIDATION / "incompatible.json").read_text())
    pair_ok = compatible["compatible"] is True and incompatible["compatible"] is False
    add(checks, "compatible(q1,q2)", pair_ok,
        "The same-topology predicate has both a positive and a negative exact-state test.",
        positive=compatible["content_hash"], negative=incompatible["content_hash"])

    grammar = json.loads((VALIDATION / "grammar_expansion.json").read_text())
    grammar_ok = grammar["requested_depth"] == 3 and grammar["bits_consumed"] == 7 and grammar["terminal_symbol_count"] == 29
    add(checks, "bounded binary grammar", grammar_ok,
        "Branch-selected grammar expansion terminated inside depth, symbol, stack, and strict-bit budgets.",
        certificate_hash=grammar["content_hash"], symbols=grammar["terminal_symbol_count"])

    reconstruction = json.loads((VALIDATION / "lineage_reconstruction.json").read_text())
    add(checks, "lineage reconstruction", reconstruction["byte_equal"] is True,
        "The committed lineage replays its source commit and reproduces the event certificate bytes.",
        certificate_hash=reconstruction["content_hash"])

    store = WorldStore(ROOT / "world/counter_store")
    store.validate()
    final_commit = store.read_commit()
    store_ok = final_commit["sequence"] == 1 and len(store.list_records(record_type="event")) == 1 and len(store.list_records(record_type="lineage")) == 1
    add(checks, "persistent world transaction", store_ok,
        "The store contains immutable initial and event commits with one event and one lineage record.",
        head=store.head, sequence=final_commit["sequence"], snapshot=final_commit["snapshot_hash"])

    python_trace = json.loads((VALIDATION / "counter_python_trace.json").read_text())
    c_trace = json.loads((VALIDATION / "counter_c_trace.json").read_text())
    backend_ok = canonical_bytes(python_trace) == canonical_bytes(c_trace)
    add(checks, "Python/C trajectory trace", backend_ok,
        "The complete eight-step TOMAGI trace and final State64 are equal.",
        steps=len(python_trace["trace"]), python_sha256=digest_file(VALIDATION / "counter_python_trace.json"),
        c_sha256=digest_file(VALIDATION / "counter_c_trace.json"))

    roadmap_proof = json.loads((VALIDATION / "roadmap_artifact_proof.json").read_text())
    roadmap_ok = (
        roadmap_proof["status"] == "pass"
        and roadmap_proof["execution"]["python_c_full_trace_equal"] is True
        and roadmap_proof["artifact"]["source_byte_equal"] is True
        and verify_hash(roadmap_proof)
    )
    add(checks, "roadmap literal EMIT artifact", roadmap_ok,
        "The primary documentation is byte-equal to its source after definition compilation and Python/C EMIT execution.",
        proof_hash=roadmap_proof["content_hash"], program_sha256=roadmap_proof["program"]["sha256"],
        artifact_sha256=roadmap_proof["artifact"]["sha256"], emit_records=roadmap_proof["execution"]["emit_records"])

    tests_text = (VALIDATION / "tests.txt").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests", tests_text)
    test_count = int(match.group(1)) if match else 0
    tests_ok = test_count >= 47 and tests_text.rstrip().endswith("OK")
    add(checks, "conformance tests", tests_ok, f"{test_count} tests passed, including the original TOMAGI suite.", count=test_count)

    static = json.loads((VALIDATION / "static_assets.json").read_text())
    add(checks, "static specifications and schemas", static.get("status") == "pass",
        "Roadmap, normative profile, source PDFs, schemas, definitions, and artifact sources passed static verification.",
        report=static)

    clean_record: dict[str, Any] | None = None
    if args.include_clean:
        clean_path = VALIDATION / "clean_rebuild.json"
        if clean_path.exists():
            clean_record = json.loads(clean_path.read_text())
            clean_ok = clean_record.get("status") == "pass" and clean_record.get("all_boundaries_equal") is True
            add(checks, "clean rebuild", clean_ok,
                "A generated-output-free copy rebuilt the selected world, query, and documentation boundaries byte-for-byte.",
                compared=clean_record.get("compared_boundaries"), record_hash=clean_record.get("content_hash"))
        else:
            add(checks, "clean rebuild", False, "clean_rebuild.json is absent")

    failures = [check for check in checks if check["status"] != "pass"]
    report = attach_hash({
        "schema": "TOM-WORLD-QUERY-VALIDATION-0.1",
        "release": "0.1.0",
        "generated": "2026-09-01",
        "status": "pass" if not failures else "fail",
        "profile": "TOM-WORLD-QUERY-KERNEL-0.1",
        "tomagi_abi": "1.0",
        "checks": checks,
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "implemented_scope": [
            "content-addressed local world store",
            "exact discrete state and event queries",
            "support and compatibility gates",
            "event transition and lineage reconstruction",
            "bounded branch-selected grammar",
            "literal emitted-byte documentation artifact",
        ],
        "not_claimed": [
            "continuous certified root solving",
            "automatic learning of unknown semantics",
            "general planning or autonomous action",
            "grounded multimodal perception",
            "large-world scalability",
            "new physical GPU device execution",
            "AGI",
        ],
    })
    write_json(VALIDATION / "validation_report.json", report)

    lines = [
        "# TOM World & Query Kernel 0.1 validation",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Checks: {report['passed']} passed; {report['failed']} failed.",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['name']} | {check['status']} | {check['detail']} |")
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "This release executes Python and C99. It retains the original GPU mappings but does not claim a new physical device dispatch. The event solver is exact over whole discrete TOMAGI transitions and does not claim continuous root isolation. Observation, hypothesis, and goal records are present, but no autonomous learner or planner is claimed.",
        "",
        f"Validation report content hash: `{report['content_hash']}`",
        "",
    ])
    (VALIDATION / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "passed": report["passed"],
        "failed": report["failed"],
        "content_hash": report["content_hash"],
        "clean_included": args.include_clean,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
