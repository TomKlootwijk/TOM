from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))
VAL = ROOT / "validation/world04r"
VAL.mkdir(parents=True, exist_ok=True)

from tom_world03.canonical import attach_hash, canonical_bytes, verify_hash
from tom_world03.interval import ClosedInterval
from tom_world03.rational import Q
from tom_world04r.baseline import trusted_piecewise_baseline
from tom_world04r.engine import run_continuation
from tom_world04r.index import build_interval_index, query_interval_index
from tom_world04r.io import load_world, write_canonical
from tom_world04r.journal import ContinuationStore
from tom_world04r.model import (
    CANONICAL_SEED_SHA256,
    CORRECTED_INTERVAL_SHA256,
    CORRECTED_V03_ZIP_SHA256,
    REJECTED_PRECORRECTION_INTERVAL_SHA256,
    ContinuationRelation,
    ContinuationWorld,
)
from tom_world04r.solver import UnresolvedContinuation, next_event_set
from tom_world04r.transition import ContinuationConflict, apply_event_set
from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load
from tomagi.core import run

WORLD_PATH = ROOT / "examples/world04r/piecewise_world.json"
STORE_PATH = ROOT / "examples/world04r/continuation_store"
PIN_PATH = ROOT / "sources/CORRECTED_V0_3_BASELINE_PIN.json"

GENERATED_FILES = (
    "examples/world04r/piecewise_reference.tmg",
    "validation/world04r/initial_event_set.json",
    "validation/world04r/initial_transition.json",
    "validation/world04r/initial_segment_seal.json",
    "validation/world04r/successor_segment_1.json",
    "validation/world04r/run_indexed.json",
    "validation/world04r/run_exhaustive.json",
    "validation/world04r/run_persisted.json",
    "validation/world04r/trusted_baseline.json",
    "validation/world04r/baseline_comparison.json",
    "validation/world04r/journal_audit.json",
    "validation/world04r/journal_reconstruction.json",
    "validation/world04r/piecewise_reference.python.trace.json",
    "validation/world04r/piecewise_reference.c.trace.json",
    "validation/world04r/tomagi_piecewise_baseline.json",
    "validation/world04r/fixture_report.json",
    "examples/world04r/world04r_release_artifact.tmg",
    "examples/world04r/world04r_release_artifact.tmg.compile.json",
    "validation/world04r/TOM_WORLD_QUERY_KERNEL_0_4_REBUILT_RELEASE.materialized.md",
    "validation/world04r/world04r_release_artifact.python.trace.json",
    "validation/world04r/world04r_release_artifact.c.trace.json",
    "validation/world04r/world04r_release_artifact.emit_records.json",
    "validation/world04r/world04r_release_artifact.proof.json",
)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def run_cmd(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 420, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / "src/python")
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def tree_manifest(path: Path) -> dict[str, Any]:
    entries = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            entries.append({
                "path": item.relative_to(path).as_posix(),
                "bytes": item.stat().st_size,
                "sha256": sha_file(item),
            })
    encoded = canonical_bytes(entries)
    return {
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "entries_sha256": "sha256:" + sha_bytes(encoded),
    }


def generated_manifest(root: Path = ROOT) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for rel in GENERATED_FILES:
        path = root / rel
        result[rel] = {
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": sha_file(path) if path.is_file() else None,
        }
    store = root / "examples/world04r/continuation_store"
    result["examples/world04r/continuation_store/**"] = tree_manifest(store) if store.is_dir() else {"exists": False}
    return result


def modified_world(raw: dict[str, Any], mutate: Callable[[dict[str, Any]], None]) -> ContinuationWorld:
    record = copy.deepcopy(raw)
    mutate(record)
    relations = [ContinuationRelation.from_record(item) for item in record["relations"]]
    record["interval_index"] = build_interval_index(relations, seed_sha256=record["seed_sha256"])
    return ContinuationWorld.from_record(attach_hash(record))


def clean_outputs(root: Path) -> None:
    shutil.rmtree(root / "build", ignore_errors=True)
    shutil.rmtree(root / "examples/world04r/continuation_store", ignore_errors=True)
    for rel in GENERATED_FILES:
        (root / rel).unlink(missing_ok=True)
    shutil.rmtree(root / "validation/world04r", ignore_errors=True)
    (root / "validation/world04r").mkdir(parents=True, exist_ok=True)
    for directory in sorted(root.rglob("__pycache__"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory)
    for path in root.rglob("*.pyc"):
        path.unlink()


def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str, **evidence: Any) -> None:
        checks.append({
            "name": name,
            "status": "pass" if passed else "fail",
            "detail": detail,
            **evidence,
        })

    # Canonical seed and corrected-base pin.
    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    seed_ok = len(seed) == 244 and not seed.endswith((b"\n", b"\r")) and sha_bytes(seed) == CANONICAL_SEED_SHA256
    check("canonical TOM seed", seed_ok,
          "exact 244 ASCII bytes, no terminal newline, canonical SHA-256",
          bytes=len(seed), sha256=sha_bytes(seed))

    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    pinned_files: list[dict[str, Any]] = []
    pin_ok = (
        pin["base_archive"]["sha256"] == CORRECTED_V03_ZIP_SHA256
        and pin["base_archive"]["bytes"] == 22217713
        and pin["base_archive"]["zip_entries"] == 10291
        and pin["base_archive"]["zip_crc"] == "pass"
        and pin["corrected_interval_file"]["sha256"] == CORRECTED_INTERVAL_SHA256
        and pin["corrected_interval_file"]["rejected_untrusted_pre_correction_sha256"] == REJECTED_PRECORRECTION_INTERVAL_SHA256
        and pin["policy"]["prior_v0_4_used_as_source"] is False
    )
    for item in pin["critical_inherited_files"]:
        path = ROOT / item["path"]
        actual = sha_file(path) if path.is_file() else None
        equal = path.is_file() and path.stat().st_size == item["bytes"] and actual == item["sha256"]
        pin_ok &= equal
        pinned_files.append({"path": item["path"], "expected": item["sha256"], "actual": actual, "equal": equal})
    check("corrected 0.3 inheritance boundary", pin_ok,
          "archive identity and every critical inherited file match the corrected 0.3 pin",
          archive=pin["base_archive"], corrected_interval_sha256=CORRECTED_INTERVAL_SHA256,
          rejected_interval_sha256=REJECTED_PRECORRECTION_INTERVAL_SHA256, files=pinned_files)

    interval_path = ROOT / "src/python/tom_world03/interval.py"
    sign_cases = {
        "negative": ClosedInterval(Q(-2), Q(-1)).sign_class(),
        "nonpositive": ClosedInterval(Q(-1, 2), Q(0)).sign_class(),
        "zero": ClosedInterval(Q(0), Q(0)).sign_class(),
        "nonnegative": ClosedInterval(Q(0), Q(1, 2)).sign_class(),
        "positive": ClosedInterval(Q(1), Q(2)).sign_class(),
        "straddles-zero": ClosedInterval(Q(-1, 2), Q(1, 2)).sign_class(),
    }
    sign_ok = sha_file(interval_path) == CORRECTED_INTERVAL_SHA256 and all(key == value for key, value in sign_cases.items())
    check("corrected rational interval semantics", sign_ok,
          "the inherited file hash and six exact sign classes match the corrected 0.3 implementation",
          file_sha256=sha_file(interval_path), cases=sign_cases)

    # Full test suite.
    tests = run_cmd([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], check=False)
    tests_text = tests.stdout + tests.stderr
    (VAL / "tests.txt").write_text(tests_text, encoding="utf-8")
    match = re.search(r"Ran (\d+) tests", tests_text)
    test_count = int(match.group(1)) if match else 0
    tests_ok = tests.returncode == 0 and test_count >= 144 and tests_text.rstrip().endswith("OK")
    check("complete inherited and corrective test suite", tests_ok,
          f"{test_count} tests passed" if tests_ok else "test suite failed",
          count=test_count, returncode=tests.returncode)

    raw, world = load_world(WORLD_PATH)
    nested = [raw["initial_segment"], raw["interval_index"], *raw["supports"],
              *raw["compatibilities"], *raw["relations"]]
    hash_ok = verify_hash(raw) and all(verify_hash(item) for item in nested)
    check("literal world content addressing", hash_ok,
          f"world plus {len(nested)} nested authority records verify",
          world_hash=world.content_hash, nested_records=len(nested), world_sha256=sha_file(WORLD_PATH))

    schema_ok = False
    schema_error = None
    try:
        import jsonschema
        schema = json.loads((ROOT / "spec/tom_world_piecewise_continuation_0_4_1.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(raw)
        schema_ok = True
    except Exception as exc:
        schema_error = str(exc)
    check("strict 0.4.1 world schema", schema_ok,
          "literal world validates under Draft 2020-12" if schema_ok else schema_error or "schema validation failed")

    trust_ok = (
        world.corrected_v03_zip_sha256 == CORRECTED_V03_ZIP_SHA256
        and world.corrected_interval_sha256 == CORRECTED_INTERVAL_SHA256
        and raw["provenance"]["prior_v0_4_used_as_source"] is False
        and raw["provenance"]["implementation_namespace"] == "tom_world04r"
        and not (ROOT / "src/python/tom_world04").exists()
        and all("continuation_until" not in relation for relation in raw["relations"])
    )
    check("0.4 trust reset and source isolation", trust_ok,
          "fresh tom_world04r namespace, corrected-base bindings, no prior 0.4 module, no relation-authored continuation boundary")

    rebuilt_index = build_interval_index(world.relations, seed_sha256=world.seed_sha256)
    index_equal = canonical_bytes(rebuilt_index) == canonical_bytes(raw["interval_index"])
    no_false_negative = True
    bracket_results = []
    for half_step in range(20):
        lo = Q(half_step, 2)
        hi = min(Q(10), lo + Q(1, 2))
        if hi <= lo:
            continue
        bracket = ClosedInterval(lo, hi)
        ids, _ = query_interval_index(world.interval_index, bracket)
        expected = sorted(
            relation.id for relation in world.relations
            if relation.active_time.intersection(bracket) is not None
        )
        equal = ids == expected
        no_false_negative &= equal
        bracket_results.append({"bracket": bracket.to_record(), "indexed": len(ids), "expected": len(expected), "equal": equal})
    check("immutable interval index", index_equal and no_false_negative,
          "index rebuilds byte-identically and exact overlap queries have no false negatives across 20 half-step brackets",
          index_hash=world.interval_index["content_hash"], brackets=bracket_results)

    indexed = run_continuation(world, planner="indexed")
    exhaustive = run_continuation(world, planner="exhaustive")
    baseline = trusted_piecewise_baseline(raw)
    reconstruction = ContinuationStore(STORE_PATH).reconstruct()
    semantic_hash = indexed.record["semantic_chain_sha256"]
    semantic_equal = (
        semantic_hash == exhaustive.record["semantic_chain_sha256"]
        == baseline["semantic_chain_sha256"]
        == reconstruction["semantic_chain_sha256"]
    )
    check("four-way continuation semantic equality", semantic_equal,
          "indexed, exhaustive, independent Fraction baseline, and journal reconstruction have one semantic-chain hash",
          semantic_chain_sha256=semantic_hash)

    events = indexed.record["semantic_chain"]["event_sets"]
    event_times = [Q.from_value(item["event_time"]).to_text() for item in events]
    boundaries_ok = event_times == ["2", "5", "7", "9"]
    for segment, bundle in zip(indexed.open_segments, indexed.bundles):
        time = Q.from_value(bundle.event_set["event_time"])
        boundaries_ok &= (
            Q.from_value(bundle.seal["end_time"]) == time
            and bundle.successor.start == time
            and bundle.successor.horizon == Q(10)
            and bundle.successor.source_event_set_hash == bundle.event_set["content_hash"]
            and bundle.successor.source_transition_hash == bundle.transition["content_hash"]
        )
    boundaries_ok &= all(segment.horizon == Q(10) for segment in indexed.open_segments)
    check("solver-derived noncompounding boundaries", boundaries_ok,
          "event roots 2,5,7,9 seal realized prefixes; every successor remains open to horizon 10",
          event_times=event_times,
          segment_starts=[segment.start.to_text() for segment in indexed.open_segments],
          segment_horizons=[segment.horizon.to_text() for segment in indexed.open_segments])

    final = {key: Q.from_value(value).to_text() for key, value in indexed.record["semantic_chain"]["final_state"].items()}
    final_ok = final == {"clock": "10", "counter": "34", "mode": "5", "output": "90", "x": "3"}
    check("canonical piecewise result", final_ok and len(events) == 4 and len(indexed.open_segments) == 5,
          "four simultaneous event sets create five realized segments and the exact terminal state",
          final_state=final, event_sets=len(events), segments=len(indexed.open_segments))

    candidate_ok = indexed.record["total_candidate_relations"] < exhaustive.record["total_candidate_relations"]
    check("indexed candidate reduction at equal semantics", candidate_ok and semantic_equal,
          "indexed candidate work is lower while semantic bytes remain equal",
          indexed=indexed.record["total_candidate_relations"],
          exhaustive=exhaustive.record["total_candidate_relations"])

    event_cert_ok = True
    source_hashes = []
    for bundle in indexed.bundles:
        for crossing in bundle.event_set["events"]:
            source = crossing["source_certificate"]
            ok = (
                source.get("schema") == "TOM-CERTIFIED-CROSSING-0.3"
                and verify_hash(source)
                and crossing["source_certificate_hash"] == source["content_hash"]
                and crossing["exact_root_time"] == bundle.event_set["event_time"]
            )
            event_cert_ok &= ok
            source_hashes.append(source["content_hash"])
    check("corrected 0.3 crossing provenance", event_cert_ok,
          "every accepted 0.4.1 crossing embeds and hashes an accepted exact corrected-0.3 source certificate",
          certificates=source_hashes)

    audit = ContinuationStore(STORE_PATH).audit()
    journal_ok = (
        audit["valid"] and audit["commit_count"] == 6 and audit["event_commit_count"] == 4
        and audit["transaction_count"] == 6 and audit["object_count"] == 19
        and reconstruction["semantic_chain_sha256"] == semantic_hash
    )
    check("append-only journal audit and reconstruction", journal_ok,
          "genesis + four events + finalization verify with no orphan; reconstruction equals direct execution",
          audit=audit, reconstruction_hash=reconstruction["content_hash"])

    # Corruption/missing/orphan probes against independent store copies.
    corruption_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="tom-world04r-corruption-") as td:
        base = Path(td)
        # World object byte mutation.
        target = base / "world"
        shutil.copytree(STORE_PATH, target)
        store = ContinuationStore(target)
        world_hash = store.descriptor()["world_hash"]
        path = target / "objects" / f"{world_hash[7:]}.json"
        data = bytearray(path.read_bytes()); data[30] ^= 1; path.write_bytes(data)
        result = store.audit(); corruption_results.append({"case": "world-byte-mutation", "detected": not result["valid"], "errors": result["errors"]})

        # Missing initial segment.
        target = base / "missing"
        shutil.copytree(STORE_PATH, target)
        store = ContinuationStore(target)
        chain = store._chain(); genesis = store._get("transactions", chain[0]["transaction_hash"])
        (target / "objects" / f"{genesis['initial_segment_hash'][7:]}.json").unlink()
        result = store.audit(); corruption_results.append({"case": "missing-initial-segment", "detected": not result["valid"], "errors": result["errors"]})

        # Orphan strict/permissive policy.
        target = base / "orphan"
        shutil.copytree(STORE_PATH, target)
        orphan = attach_hash({"schema": "TOM-VALIDATION-ORPHAN", "value": 1})
        (target / "objects" / f"{orphan['content_hash'][7:]}.json").write_bytes(canonical_bytes(orphan) + b"\n")
        store = ContinuationStore(target)
        strict = store.audit(require_no_orphans=True); permissive = store.audit(require_no_orphans=False)
        corruption_results.append({
            "case": "orphan-policy",
            "detected": not strict["valid"] and permissive["valid"] and bool(permissive["warnings"]),
            "strict_errors": strict["errors"], "permissive_warnings": permissive["warnings"],
        })
    corruption_ok = all(item["detected"] for item in corruption_results)
    check("journal corruption and orphan probes", corruption_ok,
          "world mutation, missing initial segment, and strict/permissive orphan behavior are detected",
          cases=corruption_results)

    # Deterministic rejection capsule.
    rejection_cases: list[dict[str, Any]] = []

    def expect(name: str, callback: Callable[[], Any], expected: str) -> None:
        try:
            callback()
        except Exception as exc:
            message = str(exc)
            rejection_cases.append({
                "name": name,
                "status": "pass" if expected in message else "fail",
                "expected_substring": expected,
                "error": message,
            })
        else:
            rejection_cases.append({"name": name, "status": "fail", "expected_substring": expected, "error": "no exception"})

    def world_with_continuation_until() -> ContinuationWorld:
        record = copy.deepcopy(raw)
        relation = record["relations"][0]
        relation["continuation_until"] = {"num": 2, "den": 1}
        record["relations"][0] = attach_hash(relation)
        return ContinuationWorld.from_record(attach_hash(record))

    expect("forbidden relation-authored boundary", world_with_continuation_until, "continuation_until is forbidden")

    def bad_base() -> ContinuationWorld:
        record = copy.deepcopy(raw); record["corrected_v03_baseline"]["archive_sha256"] = "0" * 64
        return ContinuationWorld.from_record(attach_hash(record))
    expect("wrong corrected-base archive", bad_base, "corrected 0.3 archive")

    def bad_interval() -> ContinuationWorld:
        record = copy.deepcopy(raw); record["corrected_v03_baseline"]["interval_py_sha256"] = "0" * 64
        return ContinuationWorld.from_record(attach_hash(record))
    expect("wrong corrected interval", bad_interval, "corrected 0.3 interval")

    def nonaffine() -> Any:
        def mutate(record: dict[str, Any]) -> None:
            relation = record["relations"][0]
            relation["expression"] = {"op": "mul", "args": [{"op": "field", "name": "x"}, {"op": "field", "name": "x"}]}
            record["relations"][0] = attach_hash(relation)
        changed = modified_world(raw, mutate)
        return next_event_set(changed, changed.initial_segment)
    expect("nonaffine continuation", nonaffine, "not affine")

    def zero_relation() -> Any:
        def mutate(record: dict[str, Any]) -> None:
            relation = record["relations"][0]
            relation["expression"] = {"op": "const", "value": {"num": 0, "den": 1}}
            record["relations"][0] = attach_hash(relation)
        changed = modified_world(raw, mutate)
        return next_event_set(changed, changed.initial_segment)
    expect("identically zero continuation", zero_relation, "identically zero")

    def conflict() -> Any:
        def mutate(record: dict[str, Any]) -> None:
            relation = record["relations"][1]
            for operation in relation["transition"]:
                if operation["field"] == "output":
                    operation["value"] = {"num": 21, "den": 1}
            record["relations"][1] = attach_hash(relation)
        changed = modified_world(raw, mutate)
        event = next_event_set(changed, changed.initial_segment)
        return apply_event_set(changed, changed.initial_segment, event)
    expect("simultaneous set conflict", conflict, "set conflict")

    expect("event-set budget exhausted", lambda: run_continuation(world, max_event_sets=3), "budget exhausted")

    def tampered_event() -> Any:
        event = next_event_set(world, world.initial_segment)
        event["event_time"] = {"num": 3, "den": 1}
        return apply_event_set(world, world.initial_segment, event)
    expect("tampered event certificate", tampered_event, "content hash mismatch")

    def bad_index() -> ContinuationWorld:
        record = copy.deepcopy(raw)
        record["interval_index"]["entries"][0]["upper"] = {"num": 9, "den": 1}
        record["interval_index"] = attach_hash(record["interval_index"])
        return ContinuationWorld.from_record(attach_hash(record))
    expect("non-reproducible interval index", bad_index, "does not match")

    event = next_event_set(world, world.initial_segment)
    first_bundle = apply_event_set(world, world.initial_segment, event)
    expect("once-only event refire", lambda: apply_event_set(world, first_bundle.successor, event), "different open segment")
    expect("append after finalization", lambda: ContinuationStore(STORE_PATH).commit_event(first_bundle), "finalized")

    rejection_ok = all(item["status"] == "pass" for item in rejection_cases)
    rejection_record = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.4.1-REJECTION-CAPSULE",
        "cases": rejection_cases,
        "all_pass": rejection_ok,
    })
    write_canonical(VAL / "rejection_capsule.json", rejection_record)
    check("deterministic rejection capsule", rejection_ok,
          f"all {len(rejection_cases)} correction, unresolved, conflict, budget, tamper, index, refire, and finalization cases reject",
          cases=rejection_cases)

    # Frozen ABI and backend path.
    program = load(ROOT / "examples/world04r/piecewise_reference.tmg")
    state, trace = run(program, trace=True)
    py_record = {"state": {name: getattr(state, name) for name in state.__dataclass_fields__}, "trace": trace}
    c_record = json.loads((VAL / "piecewise_reference.c.trace.json").read_text())
    tomagi_record = json.loads((VAL / "tomagi_piecewise_baseline.json").read_text())
    tomagi_ok = (
        (HEADER_SIZE, STATE_SIZE, CELL_SIZE) == (128, 64, 48)
        and py_record == c_record
        and tomagi_record["anchors_valid"]
        and tomagi_record["python_c_full_trace_equal"]
    )
    check("frozen TOMAGI ABI and Python/C anchor", tomagi_ok,
          "128/64/48-byte ABI unchanged; eleven integer anchors and complete traces agree",
          header=HEADER_SIZE, state=STATE_SIZE, cell=CELL_SIZE,
          program_sha256=tomagi_record["program_sha256"], anchors=tomagi_record["anchors"])

    release_proof = json.loads((VAL / "world04r_release_artifact.proof.json").read_text())
    release_ok = (
        release_proof["status"] == "pass"
        and release_proof["corrected_v03_archive_sha256"] == CORRECTED_V03_ZIP_SHA256
        and release_proof["corrected_interval_sha256"] == CORRECTED_INTERVAL_SHA256
        and release_proof["prior_v0_4_used_as_source"] is False
        and release_proof["execution"]["python_c_full_trace_equal"]
        and release_proof["artifact"]["matches_authored_document"]
    )
    check("corrective release document causal chain", release_ok,
          "literal seeded definitions compile to .tmg and equal Python/C EMIT traces materialize byte-identical Markdown",
          proof=release_proof)

    # In-place deterministic rebuild.
    before = generated_manifest()
    run_cmd([sys.executable, "tools/build_world04r_fixture.py"])
    run_cmd([sys.executable, "tools/build_world04r_release_artifact.py"])
    after = generated_manifest()
    in_place_ok = before == after
    check("in-place deterministic rebuild", in_place_ok,
          f"all {len(GENERATED_FILES)} files plus the continuation-store tree are unchanged",
          boundaries=len(GENERATED_FILES) + 1)

    # Clean generated-output-free replay.
    clean_comparisons: dict[str, Any] = {}
    clean_log = ""
    with tempfile.TemporaryDirectory(prefix="tom-world04r-clean-") as td:
        clean_root = Path(td) / ROOT.name
        clean_root.mkdir(parents=True)
        # Build the clean replay from the literal corrective source capsule only.
        # Inherited 0.1/0.2 benchmark stores contain more than ten thousand files
        # and are irrelevant to the 0.4 trust reset; their correctness is covered
        # by the full outer 144-test run.  The capsule retains every corrected-0.3
        # file pinned by CORRECTED_V0_3_BASELINE_PIN.json plus all compiler/runtime
        # sources needed to regenerate the 0.4.1 boundaries.
        for name in (
            "AGENTS.md", "VERSION", "pyproject.toml",
            "TOM_seed_genome_2026-09-01.txt",
            "TOM_WORLD_QUERY_KERNEL_0_4_REBUILT_RELEASE.md",
        ):
            shutil.copy2(ROOT / name, clean_root / name)
        for directory in ("src", "spec", "tools", "tests", "sources"):
            shutil.copytree(
                ROOT / directory,
                clean_root / directory,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        (clean_root / "examples/world04r").mkdir(parents=True)
        for name in (
            "piecewise_world.json",
            "piecewise_reference.json",
            "world04r_release_artifact.literal.json",
        ):
            shutil.copy2(ROOT / "examples/world04r" / name, clean_root / "examples/world04r" / name)
        (clean_root / "examples/world03").mkdir(parents=True)
        shutil.copy2(
            ROOT / "examples/world03/interval_event_world.json",
            clean_root / "examples/world03/interval_event_world.json",
        )
        clean_outputs(clean_root)
        (clean_root / "build").mkdir(parents=True, exist_ok=True)
        build = run_cmd([
            "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic",
            "-Isrc/c", "src/c/tomagi.c", "src/c/tomagi_cli.c", "-o", "build/tomagi-c",
        ], cwd=clean_root, check=False)
        if build.returncode == 0:
            fixture_proc = run_cmd([sys.executable, "tools/build_world04r_fixture.py"], cwd=clean_root, check=False)
            artifact_proc = run_cmd([sys.executable, "tools/build_world04r_release_artifact.py"], cwd=clean_root, check=False)
            tests_proc = run_cmd([
                sys.executable, "-m", "unittest", "discover", "-s", "tests",
                "-p", "test_world04r_corrective_rebuild.py", "-v",
            ], cwd=clean_root, check=False)
        else:
            fixture_proc = artifact_proc = tests_proc = build
        clean_log = (
            "--- C BUILD ---\n" + build.stdout + build.stderr
            + "\n--- FIXTURE ---\n" + fixture_proc.stdout + fixture_proc.stderr
            + "\n--- RELEASE ARTIFACT ---\n" + artifact_proc.stdout + artifact_proc.stderr
            + "\n--- TESTS ---\n" + tests_proc.stdout + tests_proc.stderr
        )
        clean_ok = all(proc.returncode == 0 for proc in (build, fixture_proc, artifact_proc, tests_proc))
        outer = generated_manifest(ROOT)
        inner = generated_manifest(clean_root)
        for key in outer:
            equal = outer[key] == inner.get(key)
            clean_ok &= equal
            clean_comparisons[key] = {"outer": outer[key], "clean": inner.get(key), "equal": equal}
    (VAL / "clean_rebuild.log").write_text(clean_log, encoding="utf-8")
    clean_record = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.4.1-CLEAN-REBUILD",
        "status": "pass" if clean_ok else "fail",
        "generated_output_free": True,
        "literal_sources_retained": [
            "examples/world04r/piecewise_world.json",
            "examples/world04r/piecewise_reference.json",
            "examples/world04r/world04r_release_artifact.literal.json",
        ],
        "compared_boundaries": len(clean_comparisons),
        "all_equal": clean_ok,
        "boundaries": clean_comparisons,
    })
    write_canonical(VAL / "clean_rebuild.json", clean_record)
    check("generated-output-free clean replay", clean_ok,
          f"clean copy rebuilt and matched {len(clean_comparisons)} file/tree boundaries",
          certificate_hash=clean_record["content_hash"], compared=len(clean_comparisons))

    failed = [item for item in checks if item["status"] == "fail"]
    report = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.4.1-VALIDATION-REPORT",
        "release": "0.4.1-corrective-rebuild",
        "profile": world.profile,
        "status": "pass" if not failed else "fail",
        "canonical_seed_sha256": CANONICAL_SEED_SHA256,
        "corrected_v03_archive_sha256": CORRECTED_V03_ZIP_SHA256,
        "corrected_interval_sha256": CORRECTED_INTERVAL_SHA256,
        "rejected_precorrection_interval_sha256": REJECTED_PRECORRECTION_INTERVAL_SHA256,
        "prior_v0_4_used_as_source": False,
        "test_count": test_count,
        "check_count": len(checks),
        "failure_count": len(failed),
        "semantic_chain_sha256": semantic_hash,
        "world_content_hash": world.content_hash,
        "world_file_sha256": "sha256:" + sha_file(WORLD_PATH),
        "checks": checks,
        "evidence_boundary": (
            "Exact finite piecewise-affine rational continuation; Python/C TOMAGI traces executed. "
            "No claim of arbitrary nonlinear dynamics, physical GPU dispatch, autonomous learning, or AGI."
        ),
    })
    write_canonical(VAL / "validation_report.json", report)

    lines = [
        "# TOM World & Query Kernel 0.4.1 corrective validation",
        "",
        f"Status: **{report['status']}**",
        "",
        "This validation excludes the superseded 0.4.0 line. It begins at the pinned corrected 0.3 archive and verifies every inherited critical source hash.",
        "",
        f"- Corrected 0.3 archive: `{CORRECTED_V03_ZIP_SHA256}`",
        f"- Corrected interval implementation: `{CORRECTED_INTERVAL_SHA256}`",
        f"- Tests: `{test_count}` passed",
        f"- Validation checks: `{len(checks) - len(failed)}` passed, `{len(failed)}` failed",
        f"- Semantic chain: `{semantic_hash}`",
        f"- Clean replay boundaries: `{len(clean_comparisons)}` equal",
        f"- Validation content hash: `{report['content_hash']}`",
        "",
        "The realized segment ends are solver-produced exact event times. No authoritative relation contains `continuation_until`.",
        "",
    ]
    (VAL / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "tests": test_count,
        "checks": len(checks),
        "failures": len(failed),
        "semantic_chain_sha256": semantic_hash,
        "validation_content_hash": report["content_hash"],
        "clean_boundaries": len(clean_comparisons),
    }, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
