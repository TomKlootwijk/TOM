from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

from tom_world03.canonical import attach_hash, canonical_bytes, verify_hash
from tom_world03.interval import ClosedInterval
from tom_world03.io import load_world
from tom_world03.model import IntervalWorld, Relation, TransitionOp
from tom_world03.rational import Q
from tom_world03.solver import certify_crossing, events_certificate, next_event_set
from tom_world03.transitions import TransitionConflict, apply_event_set, merge_transition_ops

VAL = ROOT / "validation/world03"
VAL.mkdir(parents=True, exist_ok=True)
WORLD_PATH = ROOT / "examples/world03/interval_event_world.json"
SEED_HASH = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"

GENERATED_BOUNDARIES = (
    "examples/world03/affine_reference.tmg",
    "validation/world03/affine_reference.python.trace.json",
    "validation/world03/affine_reference.c.trace.json",
    "validation/world03/certified_crossing_x5.json",
    "validation/world03/events_0_10.json",
    "validation/world03/next_event_set.json",
    "validation/world03/simultaneous_transition.json",
    "validation/world03/trusted_baseline_comparison.json",
    "validation/world03/tomagi_trajectory_baseline.json",
    "validation/world03/simultaneous_conflict_rejection.json",
    "validation/world03/fixture_report.json",
    "examples/world03/world03_release_artifact.tmg",
    "examples/world03/world03_release_artifact.tmg.compile.json",
    "validation/world03/TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.materialized.md",
    "validation/world03/world03_release_artifact.python.trace.json",
    "validation/world03/world03_release_artifact.c.trace.json",
    "validation/world03/world03_release_artifact.emit_records.json",
    "validation/world03/world03_release_artifact.proof.json",
)


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 420) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / "src/python")
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def test_count(text: str) -> int:
    match = re.search(r"Ran (\d+) tests", text)
    if not match:
        raise RuntimeError("could not parse unittest count")
    return int(match.group(1))


def main() -> None:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str, **evidence: Any) -> None:
        checks.append({
            "name": name,
            "status": "pass" if passed else "fail",
            "detail": detail,
            **evidence,
        })
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    # Rebuild ordinary generated boundaries from the checked-in literal sources.
    fixture = run([sys.executable, "tools/build_world03_fixture.py"])
    (VAL / "build_fixture.stdout.json").write_text(fixture.stdout, encoding="utf-8")
    release_artifact = run([sys.executable, "tools/build_world03_release_artifact.py"])
    (VAL / "release_artifact.stdout.json").write_text(release_artifact.stdout, encoding="utf-8")

    # Entire inherited suite plus 0.3 tests.
    tests = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    test_output = tests.stdout + tests.stderr
    (VAL / "full_tests.stdout.txt").write_text(test_output, encoding="utf-8")
    count = test_count(test_output)
    check("complete inherited and 0.3 test suite", "OK" in test_output, f"{count} tests passed", tests=count)

    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    check(
        "canonical seed identity",
        len(seed) == 244 and not seed.endswith(b"\n") and hashlib.sha256(seed).hexdigest() == SEED_HASH,
        "244 exact bytes, no terminal newline, canonical SHA-256",
        bytes=len(seed), sha256="sha256:" + hashlib.sha256(seed).hexdigest(),
    )

    raw, world = load_world(WORLD_PATH)
    check("literal world content address", verify_hash(raw), "top-level world content hash verifies",
          world_hash=world.content_hash, source_sha256=sha_file(WORLD_PATH))
    nested = [raw["trajectory"], *raw["supports"], *raw["compatibilities"], *raw["relations"]]
    check("nested content addresses", all(verify_hash(item) for item in nested),
          f"all {len(nested)} trajectory/support/compatibility/relation records verify",
          records=len(nested))

    schema_status = "not-installed"
    try:
        import jsonschema
    except ImportError:
        pass
    else:
        schema = json.loads((ROOT / "spec/tom_world_query_kernel_0_3.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(raw)
        schema_status = "validated"
    check("strict 0.3 world schema", schema_status == "validated",
          "world validates against the draft-2020-12 schema", schema=schema_status)

    relation = next(r for r in world.relations if r.id == "relation:x-equals-five")
    crossing = certify_crossing(world, relation, ClosedInterval(Q(2), Q(3)))
    crossing_ok = (
        crossing.accepted
        and crossing.exact_root == Q(5, 2)
        and Q.from_value(crossing.certificate["original_endpoint_residuals"]["lower"]) == Q(-1)
        and Q.from_value(crossing.certificate["original_endpoint_residuals"]["upper"]) == Q(1)
        and crossing.certificate["derivative_interval"] == ClosedInterval.point(2).to_record()
        and crossing.certificate["uniqueness_certified_by_monotonic_derivative"]
        and verify_hash(crossing.certificate)
    )
    check("certified x-5 crossing", crossing_ok,
          "[2,3] has residuals -1/+1, derivative [2,2], and exact unique root 5/2",
          certificate_hash=crossing.certificate["content_hash"])

    events = events_certificate(world, 0, 10)
    event_roots = [Q.from_value(item["exact_root_time"]).to_text() for item in events["events"]]
    check("ordered event enumeration", event_roots == ["5/2", "5/2", "5/2", "5"],
          "four accepted relation roots are deduplicated and ordered", roots=event_roots,
          certificate_hash=events["content_hash"])

    event_set = next_event_set(world, 0, 10)
    expected_relations = [
        "relation:time-equals-five-halves",
        "relation:triple-x-equals-fifteen",
        "relation:x-equals-five",
    ]
    check(
        "simultaneous event set",
        Q.from_value(event_set["event_time"]) == Q(5, 2)
        and event_set["event_count"] == 3
        and event_set["relation_order"] == expected_relations
        and verify_hash(event_set),
        "earliest exact rational root groups three events in total deterministic order",
        event_time="5/2", relation_order=event_set["relation_order"],
        certificate_hash=event_set["content_hash"],
    )

    transition = apply_event_set(world, event_set)
    check(
        "atomic simultaneous transition",
        Q.from_value(transition["post_state"]["counter"]) == Q(3)
        and Q.from_value(transition["post_state"]["output"]) == Q(25)
        and Q.from_value(transition["pre_state"]["x"]) == Q(5)
        and verify_hash(transition),
        "all operations read the common pre-state; add contributors total 3 and output set is 25",
        transition_hash=transition["content_hash"],
    )

    inactive = next(r for r in world.relations if r.id == "relation:inactive-x-equals-two")
    unsupported = next(r for r in world.relations if r.id == "relation:unsupported-x-equals-five")
    incompatible = next(r for r in world.relations if r.id == "relation:incompatible-x-equals-six")
    rejection_statuses = {
        "inactive": certify_crossing(world, inactive, ClosedInterval(Q(0), Q(2))).status,
        "unsupported": certify_crossing(world, unsupported, ClosedInterval(Q(2), Q(3))).status,
        "incompatible": certify_crossing(world, incompatible, ClosedInterval(Q(2), Q(4))).status,
    }
    check(
        "support compatibility and active-time gates",
        rejection_statuses == {
            "inactive": "outside-active-time",
            "unsupported": "outside-support",
            "incompatible": "incompatible",
        },
        "three independently typed gates reject their intended candidates",
        statuses=rejection_statuses,
    )

    baseline = json.loads((VAL / "trusted_baseline_comparison.json").read_text())
    check("independent Fraction baseline", baseline["equal"] and verify_hash(baseline),
          "independent affine linearizer returns the same accepted IDs, roots, and order",
          solver_events=baseline["solver_event_count"], baseline_events=baseline["baseline_event_count"],
          certificate_hash=baseline["content_hash"])

    tomagi = json.loads((VAL / "tomagi_trajectory_baseline.json").read_text())
    check(
        "TOMAGI trajectory anchors",
        tomagi["affine_trajectory_matches_all_integer_tomagi_anchors"]
        and tomagi["python_c_full_trace_equal"]
        and verify_hash(tomagi),
        "eleven integer anchors match x=2t/clock=t and Python/C full traces are equal",
        anchors=len(tomagi["anchors"]), program_sha256=tomagi["program_sha256"],
        certificate_hash=tomagi["content_hash"],
    )

    from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE
    check("frozen TOMAGI ABI", (HEADER_SIZE, STATE_SIZE, CELL_SIZE) == (128, 64, 48),
          "0.3 adds no opcode or record-layout change", header=HEADER_SIZE, state=STATE_SIZE, cell=CELL_SIZE)

    release_proof = json.loads((VAL / "world03_release_artifact.proof.json").read_text())
    check(
        "release document causal chain",
        release_proof["status"] == "pass"
        and release_proof["execution"]["python_c_full_trace_equal"]
        and release_proof["artifact"]["matches_authored_document"],
        "literal definitions compile to .tmg; Python/C traces and materialized Markdown bytes agree",
        proof=release_proof,
    )

    # Deterministic malformed-input and conflict capsule.
    rejection_cases: list[dict[str, Any]] = []

    def expect(name: str, callback: Callable[[], Any], text: str) -> None:
        try:
            callback()
        except Exception as exc:
            message = str(exc)
            rejection_cases.append({
                "name": name,
                "status": "pass" if text in message else "fail",
                "error": message,
                "expected_substring": text,
            })
        else:
            rejection_cases.append({"name": name, "status": "fail", "error": "no exception"})

    expect("zero denominator", lambda: Q(1, 0), "denominator")
    expect("inverted interval", lambda: ClosedInterval(Q(2), Q(1)), "below lower")
    bad_hash = copy.deepcopy(raw)
    bad_hash["solver"]["refine_steps"] += 1
    expect("world hash mutation", lambda: IntervalWorld.from_record(bad_hash), "content hash mismatch")
    expect("excessive refinement", lambda: certify_crossing(
        world, relation, ClosedInterval(Q(2), Q(3)), refine_steps=129), "outside")
    a = Relation(
        "conflict:a", 0, {"op": "const", "value": Q(0).to_record()},
        "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)), "event:a",
        (TransitionOp("output", "set", Q(1)),), "sha256:" + "a" * 64,
    )
    b = Relation(
        "conflict:b", 0, {"op": "const", "value": Q(0).to_record()},
        "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)), "event:b",
        (TransitionOp("output", "set", Q(2)),), "sha256:" + "b" * 64,
    )
    expect("unequal simultaneous sets", lambda: merge_transition_ops([a, b]), "set conflict")
    c = Relation(
        "conflict:c", 0, {"op": "const", "value": Q(0).to_record()},
        "support:main", "compat:mode-1", ClosedInterval(Q(0), Q(1)), "event:c",
        (TransitionOp("output", "add", Q(2)),), "sha256:" + "c" * 64,
    )
    expect("mixed simultaneous modes", lambda: merge_transition_ops([a, c]), "mixed modes")
    expect("fractional xor", lambda: TransitionOp.from_record({
        "field": "output", "mode": "xor", "value": Q(1, 2).to_record()}), "integer")
    malformed_event_set = copy.deepcopy(event_set)
    malformed_event_set["relation_order"] = ["missing:relation"]
    expect("unknown event-set relation", lambda: apply_event_set(world, malformed_event_set), "unknown relation")
    all_rejections = all(item["status"] == "pass" for item in rejection_cases)
    check("deterministic rejection capsule", all_rejections,
          f"all {len(rejection_cases)} malformed/conflicting cases reject as specified",
          cases=rejection_cases)
    write_json(VAL / "rejection_capsule.json", attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-REJECTION-CAPSULE",
        "cases": rejection_cases,
        "all_pass": all_rejections,
    }))

    # Re-running both builders in place must reproduce every recorded boundary.
    before = {rel: sha_file(ROOT / rel) for rel in GENERATED_BOUNDARIES}
    run([sys.executable, "tools/build_world03_fixture.py"])
    run([sys.executable, "tools/build_world03_release_artifact.py"])
    after = {rel: sha_file(ROOT / rel) for rel in GENERATED_BOUNDARIES}
    check("in-place deterministic rebuild", before == after,
          f"all {len(GENERATED_BOUNDARIES)} generated boundary hashes are unchanged",
          boundaries=len(GENERATED_BOUNDARIES))

    # Clean generated-output-free copy replay.
    clean_comparisons: dict[str, Any] = {}
    clean_log = ""
    with tempfile.TemporaryDirectory(prefix="tom-world03-clean-") as td:
        clean_root = Path(td) / ROOT.name
        shutil.copytree(
            ROOT,
            clean_root,
            ignore=shutil.ignore_patterns("build", "dist", ".pytest_cache", "__pycache__", "*.pyc", "*.pyo"),
        )
        # Keep literal sources, schemas, and inherited 0.2 evidence. Remove only
        # outputs produced by the two 0.3 build programs.
        (clean_root / "examples/world03/affine_reference.tmg").unlink(missing_ok=True)
        for name in ("world03_release_artifact.tmg", "world03_release_artifact.tmg.compile.json"):
            (clean_root / "examples/world03" / name).unlink(missing_ok=True)
        shutil.rmtree(clean_root / "validation/world03", ignore_errors=True)
        (clean_root / "validation/world03").mkdir(parents=True, exist_ok=True)
        commands = [
            [sys.executable, "tools/build_world03_fixture.py"],
            [sys.executable, "tools/build_world03_release_artifact.py"],
            [sys.executable, "-m", "unittest", "tests.test_world03_interval_events", "-v"],
        ]
        logs: list[str] = []
        for command in commands:
            result = run(command, cwd=clean_root)
            logs.append("$ " + " ".join(command) + "\n" + result.stdout + result.stderr)
        clean_log = "\n\n".join(logs)
        for rel in GENERATED_BOUNDARIES:
            outer = ROOT / rel
            rebuilt = clean_root / rel
            outer_hash = sha_file(outer)
            rebuilt_hash = sha_file(rebuilt) if rebuilt.is_file() else None
            clean_comparisons[rel] = {
                "outer_sha256": outer_hash,
                "rebuilt_sha256": rebuilt_hash,
                "equal": outer_hash == rebuilt_hash,
            }
    (VAL / "clean_rebuild.log").write_text(clean_log, encoding="utf-8")
    clean_equal = all(item["equal"] for item in clean_comparisons.values())
    clean_record = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-CLEAN-REBUILD",
        "status": "pass" if clean_equal else "fail",
        "generated_outputs_removed": True,
        "literal_world_preserved": str(WORLD_PATH.relative_to(ROOT)),
        "compared_boundaries": len(clean_comparisons),
        "all_equal": clean_equal,
        "boundaries": clean_comparisons,
    })
    write_json(VAL / "clean_rebuild.json", clean_record)
    check("clean generated-output-free replay", clean_equal,
          f"all {len(clean_comparisons)} 0.3 boundaries rebuilt byte-identically",
          clean_rebuild_hash=clean_record["content_hash"], boundaries=len(clean_comparisons))

    fixture_report = json.loads((VAL / "fixture_report.json").read_text())
    failures = [item for item in checks if item["status"] != "pass"]
    report = attach_hash({
        "schema": "TOM-WORLD-QUERY-KERNEL-0.3-VALIDATION",
        "release": "0.3.0",
        "generated": "2026-09-01",
        "status": "pass" if not failures else "fail",
        "canonical_seed_sha256": "sha256:" + SEED_HASH,
        "tomagi_abi": {"header_bytes": HEADER_SIZE, "state_bytes": STATE_SIZE, "cell_bytes": CELL_SIZE},
        "world": {
            "path": str(WORLD_PATH.relative_to(ROOT)),
            "bytes": WORLD_PATH.stat().st_size,
            "sha256": sha_file(WORLD_PATH),
            "content_hash": world.content_hash,
            "relations": len(world.relations),
        },
        "tests": count,
        "checks_passed": len(checks),
        "checks_failed": len(failures),
        "fixture_report_hash": fixture_report["content_hash"],
        "release_artifact_proof_hash": release_proof.get("artifact", {}).get("sha256"),
        "clean_rebuild_hash": clean_record["content_hash"],
        "checks": checks,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "evidence_boundary": (
            "Certified arithmetic is exact rational over affine trajectories and finite polynomial expressions. "
            "Python/C equality applies to the underlying TOMAGI anchor and seeded documentation artifact. "
            "This report does not claim a general ODE solver, autonomous learner, or AGI."
        ),
    })
    write_json(VAL / "validation_report.json", report)

    summary = [
        "# TOM World & Query Kernel 0.3 validation",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Complete tests passed: **{count}**",
        f"- Validation checks passed: **{len(checks)}**",
        f"- Validation checks failed: **{len(failures)}**",
        f"- Certified earliest event time: **5/2**",
        f"- Simultaneous events: **3**",
        f"- Clean replay boundaries: **{len(clean_comparisons)}**",
        f"- TOMAGI ABI: **{HEADER_SIZE}/{STATE_SIZE}/{CELL_SIZE} bytes**",
        "",
        "The authoritative machine-readable record is `validation/world03/validation_report.json`.",
        "",
        "The 0.3 claims are limited to exact rational affine trajectories and the finite continuous expression profile in the normative specification.",
        "",
    ]
    (VAL / "VALIDATION.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "tests": count,
        "checks_passed": len(checks),
        "checks_failed": len(failures),
        "clean_boundaries": len(clean_comparisons),
        "validation_hash": report["content_hash"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
