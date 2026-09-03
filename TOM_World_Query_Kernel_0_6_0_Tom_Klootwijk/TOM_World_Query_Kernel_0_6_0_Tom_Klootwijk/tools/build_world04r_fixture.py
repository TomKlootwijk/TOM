from __future__ import annotations

"""Build generic 0.4.1 evidence from frozen literal world/program sources.

Domain relations, transitions, decoys, and reference cells live in the literal
JSON files under ``examples/world04r``.  This builder performs only generic,
domain-neutral work: validation, index reconstruction, compilation, execution,
trace capture, query evaluation, baseline comparison, and persistence.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world03.canonical import attach_hash, canonical_bytes, verify_hash
from tom_world03.rational import Q
from tom_world04r.baseline import trusted_piecewise_baseline
from tom_world04r.engine import run_continuation
from tom_world04r.index import build_interval_index
from tom_world04r.io import load_world, write_canonical
from tom_world04r.journal import ContinuationStore
from tom_world04r.model import CORRECTED_INTERVAL_SHA256, CORRECTED_V03_ZIP_SHA256
from tom_world04r.solver import next_event_set
from tom_world04r.transition import apply_event_set
from tomagi.compiler import compile_file
from tomagi.core import Opcode, run
from tomagi.format import load

EXAMPLE = ROOT / "examples/world04r"
VALIDATION = ROOT / "validation/world04r"
STORE = EXAMPLE / "continuation_store"
WORLD_SOURCE = EXAMPLE / "piecewise_world.json"
PROGRAM_SOURCE = EXAMPLE / "piecewise_reference.json"
PROGRAM = EXAMPLE / "piecewise_reference.tmg"
VALIDATION.mkdir(parents=True, exist_ok=True)

EXPECTED_WORLD_CONTENT_HASH = "sha256:c25c99eeeb728f50b52a06e89b9f669470ccb294fd8f0cc6e4ccb87bde9ff2d9"
EXPECTED_WORLD_FILE_SHA256 = "6a402f447bab608a5ca130bf84e64616f0c0601fd380aba11034ff33812bd9a4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_tomagi_reference() -> dict:
    source_record = json.loads(PROGRAM_SOURCE.read_text(encoding="utf-8"))
    if not isinstance(source_record, dict) or source_record.get("tomagi_version") != "1.0.0":
        raise ValueError("piecewise_reference.json is not a literal TOMAGI 1.0 source")
    compile_file(PROGRAM_SOURCE, PROGRAM)
    program = load(PROGRAM)
    final_state, trace = run(program, trace=True)
    py_record = {
        "state": {name: getattr(final_state, name) for name in final_state.__dataclass_fields__},
        "trace": trace,
    }
    write_canonical(VALIDATION / "piecewise_reference.python.trace.json", py_record)
    c_exe = ROOT / "build/tomagi-c"
    if not c_exe.exists():
        c_exe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c", "-o", str(c_exe),
        ], cwd=ROOT, check=True)
    c_record = json.loads(subprocess.check_output([str(c_exe), str(PROGRAM), "--trace-json"], text=True))
    write_canonical(VALIDATION / "piecewise_reference.c.trace.json", c_record)

    anchors = [{"time": 0, "rho": 0}]
    for item in trace:
        if item["opcode"] == int(Opcode.KIN2):
            anchors.append({"time": item["tick"], "rho": item["rho"]})
    expected_rho = [0, 2, 4, 8, 12, 16, 10, 4, 5, 6, 6]
    anchors_valid = (
        [item["time"] for item in anchors] == list(range(11))
        and [item["rho"] for item in anchors] == expected_rho
    )
    result = attach_hash({
        "schema": "TOM-TOMAGI-PIECEWISE-ANCHOR-0.4.1",
        "program_source": PROGRAM_SOURCE.relative_to(ROOT).as_posix(),
        "program_source_sha256": "sha256:" + sha(PROGRAM_SOURCE),
        "program": PROGRAM.relative_to(ROOT).as_posix(),
        "program_sha256": "sha256:" + sha(PROGRAM),
        "encoding": "rho = 2*x; tick = time",
        "anchors": anchors,
        "anchors_valid": anchors_valid,
        "python_c_full_trace_equal": py_record == c_record,
    })
    write_canonical(VALIDATION / "tomagi_piecewise_baseline.json", result)
    return result


def main() -> None:
    raw, world = load_world(WORLD_SOURCE)
    if world.content_hash != EXPECTED_WORLD_CONTENT_HASH or sha(WORLD_SOURCE) != EXPECTED_WORLD_FILE_SHA256:
        raise ValueError("literal 0.4.1 world source identity changed without a profile revision")
    nested = [raw["initial_segment"], raw["interval_index"], *raw["supports"],
              *raw["compatibilities"], *raw["relations"]]
    if not verify_hash(raw) or not all(verify_hash(item) for item in nested):
        raise ValueError("literal world or nested authority hash mismatch")
    rebuilt_index = build_interval_index(world.relations, seed_sha256=world.seed_sha256)
    if canonical_bytes(rebuilt_index) != canonical_bytes(raw["interval_index"]):
        raise ValueError("literal world interval index does not rebuild byte-identically")

    initial_event = next_event_set(world, world.initial_segment, planner="indexed")
    first_bundle = apply_event_set(world, world.initial_segment, initial_event)
    indexed = run_continuation(world, planner="indexed")
    exhaustive = run_continuation(world, planner="exhaustive")
    baseline = trusted_piecewise_baseline(raw)

    if STORE.exists():
        shutil.rmtree(STORE)
    store = ContinuationStore.initialize(
        STORE,
        (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes(),
        raw,
        world,
    )
    persisted = run_continuation(world, planner="indexed", store=store)
    audit = store.audit()
    reconstruction = store.reconstruct()

    write_canonical(VALIDATION / "initial_event_set.json", initial_event)
    write_canonical(VALIDATION / "initial_transition.json", first_bundle.transition)
    write_canonical(VALIDATION / "initial_segment_seal.json", first_bundle.seal)
    write_canonical(VALIDATION / "successor_segment_1.json", first_bundle.successor_record)
    write_canonical(VALIDATION / "run_indexed.json", indexed.record)
    write_canonical(VALIDATION / "run_exhaustive.json", exhaustive.record)
    write_canonical(VALIDATION / "run_persisted.json", persisted.record)
    write_canonical(VALIDATION / "trusted_baseline.json", baseline)
    write_canonical(VALIDATION / "journal_audit.json", audit)
    write_canonical(VALIDATION / "journal_reconstruction.json", reconstruction)

    comparison = attach_hash({
        "schema": "TOM-PIECEWISE-BASELINE-COMPARISON-0.4.1",
        "world_hash": world.content_hash,
        "indexed_exhaustive_equal": indexed.record["semantic_chain_sha256"] == exhaustive.record["semantic_chain_sha256"],
        "indexed_baseline_equal": indexed.record["semantic_chain_sha256"] == baseline["semantic_chain_sha256"],
        "persisted_equal": indexed.record["semantic_chain_sha256"] == persisted.record["semantic_chain_sha256"],
        "journal_reconstruction_equal": indexed.record["semantic_chain_sha256"] == reconstruction["semantic_chain_sha256"],
        "semantic_chain_sha256": indexed.record["semantic_chain_sha256"],
        "indexed_candidate_relations": indexed.record["total_candidate_relations"],
        "exhaustive_candidate_relations": exhaustive.record["total_candidate_relations"],
    })
    write_canonical(VALIDATION / "baseline_comparison.json", comparison)

    tomagi = build_tomagi_reference()
    fixture = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.4.1-FIXTURE-REPORT",
        "release": "0.4.1",
        "base_archive_sha256": CORRECTED_V03_ZIP_SHA256,
        "corrected_interval_sha256": CORRECTED_INTERVAL_SHA256,
        "world": {
            "path": WORLD_SOURCE.relative_to(ROOT).as_posix(),
            "bytes": WORLD_SOURCE.stat().st_size,
            "sha256": "sha256:" + sha(WORLD_SOURCE),
            "content_hash": world.content_hash,
            "relations": len(world.relations),
            "source_kind": "frozen literal content-addressed world",
        },
        "initial_event": {
            "time": initial_event["event_time"],
            "event_count": initial_event["event_count"],
            "relation_order": initial_event["relation_order"],
        },
        "semantic_chain_sha256": indexed.record["semantic_chain_sha256"],
        "event_sets": indexed.record["event_set_count"],
        "segments": indexed.record["realized_segment_count"],
        "final_state": indexed.record["semantic_chain"]["final_state"],
        "indexed_exhaustive_equal": comparison["indexed_exhaustive_equal"],
        "independent_baseline_equal": comparison["indexed_baseline_equal"],
        "journal_reconstruction_equal": comparison["journal_reconstruction_equal"],
        "indexed_candidate_relations": comparison["indexed_candidate_relations"],
        "exhaustive_candidate_relations": comparison["exhaustive_candidate_relations"],
        "journal_valid": audit["valid"],
        "journal_commits": audit["commit_count"],
        "journal_transactions": audit["transaction_count"],
        "journal_objects": audit["object_count"],
        "tomagi_anchors_valid": tomagi["anchors_valid"],
        "python_c_tomagi_trace_equal": tomagi["python_c_full_trace_equal"],
    })
    write_canonical(VALIDATION / "fixture_report.json", fixture)
    print(json.dumps(fixture, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
