from __future__ import annotations

"""Validate TOM Learner 0.2 / WQK 0.6 without broadening its claims."""

import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples/learner06"
VAL = ROOT / "validation/learner06"
SEED = ROOT / "TOM_seed_genome_2026-09-01.txt"

from tom_learner06.oracle import OracleError, evaluate_dataset
from tomagi.canonical import attach_hash, canonical_bytes, content_hash, verify_hash
from tomagi.core import Opcode
from tomagi.formal import FormalBudgetExceeded, Limits, evaluate, run_program
from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load, loads
from tomagi.immutable_store import ImmutablePublicationStore, validate_plan
from tomagi.materialize import materialize_trace


def load_json(path: str | Path) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8") if not Path(path).is_absolute() else Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def rehash(record: dict[str, Any]) -> None:
    record.pop("content_hash", None)
    record["content_hash"] = content_hash(record)


def import_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_status() -> tuple[int, bool, str]:
    path = VAL / "tests.txt"
    if not path.is_file():
        return 0, False, "missing"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"Ran (\d+) tests", text)
    count = int(match.group(1)) if match else 0
    return count, text.rstrip().endswith("OK"), sha_path(path)


def build_rejection_capsule() -> dict[str, Any]:
    registry = load_json(BASE / "family_registry.json")
    prior = load_json(BASE / "prior_authority.json")
    partition = load_json(BASE / "partition_policy.json")
    repair = load_json(BASE / "repair_handoff_proof.json")
    bundle = load_json(BASE / "dataset_bundle.json")
    plan = validate_plan(load_json(VAL / "promotion_authority.direct.json")["value"]["publication_plan"])
    cases: list[dict[str, Any]] = []

    def expect(name: str, fn: Callable[[], Any], contains: str) -> None:
        try:
            fn()
        except Exception as exc:
            message = str(exc)
            cases.append({"name": name, "status": "pass" if contains in message else "fail", "error": message})
        else:
            cases.append({"name": name, "status": "fail", "error": "no rejection"})

    bad_registry = copy.deepcopy(registry)
    bad_registry["families"][0]["kind"] = "tampered"
    expect("registry hash mutation", lambda: evaluate_dataset(bundle["datasets"][0], bad_registry, prior), "content hash mismatch")

    budget = copy.deepcopy(registry)
    budget["families"][0]["search_budget"]["max_candidates"] -= 1
    rehash(budget["families"][0]); rehash(budget)
    expect("candidate search budget", lambda: evaluate_dataset(bundle["datasets"][0], budget, prior), "exceeds declared search budget")

    formal_limits = Limits(
        max_steps=4_000_000,
        max_depth=256,
        max_collection_items=20_000,
        max_value_nodes=4_000_000,
        max_canonical_bytes=16_000_000,
    )
    learner_program = load_json(BASE / "learner06_family_authority.formal.json")

    def learner_inputs(
        selected_registry: dict[str, Any] = registry,
        selected_datasets: list[dict[str, Any]] | None = None,
        selected_repair: dict[str, Any] = repair,
    ) -> dict[str, Any]:
        return {
            "learner06_inputs": [
                selected_registry,
                partition,
                *(selected_datasets if selected_datasets is not None else bundle["datasets"]),
                prior,
                selected_repair,
            ]
        }

    formal_budget = copy.deepcopy(registry)
    # A larger, rehashed budget used to pass because only an upper-bound check
    # existed; the literal profile now pins the declared finite search space.
    formal_budget["families"][0]["search_budget"]["max_candidates"] += 1
    rehash(formal_budget["families"][0]); rehash(formal_budget)
    expect(
        "formal registry budget authority",
        lambda: run_program(learner_program, learner_inputs(formal_budget), limits=formal_limits),
        "family registry is invalid",
    )

    unknown_operation = copy.deepcopy(registry)
    expression_family = unknown_operation["families"][3]
    expression_candidate = next(
        candidate for candidate in expression_family["candidates"]
        if candidate["tree"]["op"] not in {"x", "const"}
    )
    expression_candidate["tree"]["op"] = "undeclared-operation"
    rehash(expression_candidate); rehash(expression_family); rehash(unknown_operation)
    expect(
        "formal undeclared expression operation",
        lambda: run_program(learner_program, learner_inputs(unknown_operation), limits=formal_limits),
        "family registry is invalid",
    )

    malformed_candidate_id = copy.deepcopy(registry)
    candidate = malformed_candidate_id["families"][0]["candidates"][0]
    candidate["id"] = ["not", "a", "string"]
    rehash(candidate); rehash(malformed_candidate_id["families"][0]); rehash(malformed_candidate_id)
    expect(
        "formal candidate identifier type",
        lambda: run_program(
            learner_program, learner_inputs(malformed_candidate_id), limits=formal_limits,
        ),
        "family registry is invalid",
    )

    unresolved_datasets = copy.deepcopy(bundle["datasets"])
    unresolved = unresolved_datasets[0]
    unresolved["partitions"]["train"][0] = "observation:does-not-exist"
    unresolved["assignment_basis"]["partitions"] = copy.deepcopy(unresolved["partitions"])
    rehash(unresolved["assignment_basis"]); rehash(unresolved)
    expect(
        "formal unresolved partition membership",
        lambda: run_program(learner_program, learner_inputs(selected_datasets=unresolved_datasets), limits=formal_limits),
        "dataset contract is invalid",
    )

    malformed_supersedes = copy.deepcopy(bundle["datasets"])
    malformed_supersedes[0]["supersedes"] = 7
    rehash(malformed_supersedes[0])
    expect(
        "formal supersession authority identity",
        lambda: run_program(
            learner_program,
            learner_inputs(selected_datasets=malformed_supersedes),
            limits=formal_limits,
        ),
        "dataset contract is invalid",
    )

    failed_repair = copy.deepcopy(repair)
    failed_repair["status"] = "fail"
    rehash(failed_repair)
    expect(
        "formal failed repair proof",
        lambda: run_program(learner_program, learner_inputs(selected_repair=failed_repair), limits=formal_limits),
        "repair handoff proof is invalid",
    )

    promotion_program = load_json(BASE / "learner06_promotion_authority.formal.json")
    learner_result = load_json(BASE / "learner06_family_authority.result.json")
    context = load_json(BASE / "promotion_context.json")
    stale_context = copy.deepcopy(context)
    stale_context["expected_parent"] = "sha256:" + "00" * 32
    rehash(stale_context)
    expect(
        "formal stale promotion context parent",
        lambda: run_program(
            promotion_program,
            {"promotion06_inputs": [
                learner_result, prior, registry, partition, repair, stale_context, bundle,
            ]},
            limits=formal_limits,
        ),
        "promotion context is invalid",
    )

    bad_initial = copy.deepcopy(plan)
    bad_initial["initial_head"] = "sha256:" + "00" * 32
    rehash(bad_initial)
    expect("wrong continuation initial head", lambda: validate_plan(bad_initial), "initial_head")

    missing_base = copy.deepcopy(plan)
    missing_base["base_records"] = [w for w in missing_base["base_records"] if w["record"]["content_hash"] != plan["initial_head"]]
    rehash(missing_base)
    expect("missing parent commit base record", lambda: validate_plan(missing_base), "initial_head")

    broken_sequence = copy.deepcopy(plan)
    broken_sequence["publications"][1]["sequence"] += 1
    rehash(broken_sequence["publications"][1]); rehash(broken_sequence)
    expect("noncontiguous publication sequence", lambda: validate_plan(broken_sequence), "contiguous")

    missing_evidence = copy.deepcopy(plan)
    pub = missing_evidence["publications"][0]
    target = pub["required_hashes"][0]
    pub["writes"] = [w for w in pub["writes"] if w["record"]["content_hash"] != target]
    missing_evidence["base_records"] = [w for w in missing_evidence["base_records"] if w["record"]["content_hash"] != target]
    rehash(pub); rehash(missing_evidence)
    with tempfile.TemporaryDirectory() as td:
        expect(
            "unavailable required evidence",
            lambda: ImmutablePublicationStore.apply_plan(td, SEED.read_bytes(), missing_evidence),
            "required hashes are unavailable",
        )

    with tempfile.TemporaryDirectory() as td:
        store = ImmutablePublicationStore.initialize(td, plan["store_descriptor"], SEED.read_bytes(), base_records=plan["base_records"], initial_head=plan["initial_head"])
        first = plan["publications"][0]
        store.apply_publication(first)
        expect("stale same-head publication", lambda: store.apply_publication(first), "stale publication head")

    program = load(BASE / "learner06_family_authority.tmg")
    trace_record = load_json(VAL / "learner_authority.python.trace.json")
    forged = copy.deepcopy(trace_record["trace"])
    forged[0]["lineage"] ^= 1
    expect("forged materialization trace", lambda: materialize_trace(program, forged), "does not match deterministic replay")

    blob = bytearray((BASE / "learner06_family_authority.tmg").read_bytes())
    blob[40:44] = (1).to_bytes(4, "little")
    expect("nonzero reserved TOMAGI header", lambda: loads(bytes(blob)), "reserved TOMAGI header words")

    expect(
        "non-finite canonical JSON",
        lambda: canonical_bytes({"x": math.nan}),
        "non-finite numbers are not valid JSON",
    )

    oversized = {
        "op": "let",
        "bindings": [{"name": "discarded", "value": {"op": "list", "items": [{"op": "lit", "value": i} for i in range(16)]}}],
        "body": {"op": "lit", "value": 0},
    }
    expect(
        "intermediate formal node budget",
        lambda: evaluate(oversized, limits=Limits(max_steps=1000, max_depth=64, max_collection_items=100, max_value_nodes=10, max_canonical_bytes=10000)),
        "max_value_nodes",
    )

    # The authority must reject ambiguity without an exception or hidden winner.
    ambiguity = next(row for row in load_json(VAL / "learner_authority.direct.json")["value"]["results"] if row["dataset_id"] == "dataset:cross-family-ambiguity")
    cases.append({
        "name": "cross-family ambiguity authority rejection",
        "status": "pass" if (not ambiguity["accepted"] and ambiguity["selected_candidate"] is None and ambiguity["ambiguity_record"]["resolution"] == "reject-without-hidden-tie-break") else "fail",
        "error": ambiguity["reason"],
    })

    regression = next(row for row in load_json(VAL / "learner_authority.direct.json")["value"]["results"] if row["dataset_id"] == "dataset:supersession-regression-failure")
    cases.append({
        "name": "regression-impact promotion rejection",
        "status": "pass" if (not regression["accepted"] and regression["reason"] == "regression-impact" and not regression["regression_impact"]["all_pass"]) else "fail",
        "error": regression["reason"],
    })

    return attach_hash({
        "schema": "TOM-LEARNER-0.2-REJECTION-CAPSULE-0.6",
        "status": "pass" if all(case["status"] == "pass" for case in cases) else "fail",
        "case_count": len(cases),
        "passed": sum(case["status"] == "pass" for case in cases),
        "cases": cases,
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-clean", action="store_true")
    args = parser.parse_args()
    VAL.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, Any]] = []
    def check(name: str, passed: bool, detail: str, **data: Any) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail, **data})

    seed = SEED.read_bytes()
    check("canonical seed", len(seed) == 244 and not seed.endswith((b"\n", b"\r")) and sha_bytes(seed) == "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5", "The exact 244-byte TOM genome remains the authority root.", sha256=sha_bytes(seed))

    repair_md = ROOT / "docs/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.md"
    repair_proof = load_json("sources/codex_0_5_2_repair/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json")
    repair_ok = verify_hash(repair_proof) and repair_proof["status"] == "pass" and repair_proof["artifact"]["sha256"] == sha_path(repair_md) and repair_proof["artifact"]["bytes"] == repair_md.stat().st_size
    check("CODEX repair handoff authority", repair_ok, "The authored handoff exactly matches its TOMAGI-materialized artifact proof.", handoff_sha256=sha_path(repair_md), proof_hash=repair_proof.get("content_hash"))

    learner_proof = load_json("validation/learner06/learner_authority_proof.json")
    promotion_proof = load_json("validation/learner06/promotion_authority_proof.json")
    fixture = load_json("validation/learner06/fixture_report.json")
    oracle = load_json("validation/learner06/oracle_comparison.json")
    audit = load_json("validation/learner06/promotion_store_audit.json")
    reconstruction = load_json("validation/learner06/promotion_store_reconstruction.json")
    registry = load_json("examples/learner06/family_registry.json")

    check("finite typed family registry", verify_hash(registry) and len(registry["families"]) == 4 and sum(len(f["candidates"]) for f in registry["families"]) == 121, "Four content-addressed families expose an explicit finite 121-candidate search space.", family_registry_hash=registry["content_hash"], families=len(registry["families"]), candidates=sum(len(f["candidates"]) for f in registry["families"]))
    check("formal learner outcomes", verify_hash(fixture) and fixture["status"] == "pass" and (fixture["accepted_count"], fixture["rejected_count"], fixture["ambiguity_count"], fixture["false_promotions"]) == (9, 7, 3, 0), "Nine exact proposals are accepted, seven are rejected, three are explicit ambiguities, and no adversarial fixture is promoted.", fixture_hash=fixture["content_hash"])
    check("independent oracle", verify_hash(oracle) and oracle["all_equal"] and (oracle["accepted_count"], oracle["rejected_count"], oracle["ambiguity_count"]) == (9, 7, 3), "A separately implemented fractions.Fraction enumerator agrees on every data set.", oracle_hash=oracle["content_hash"])

    results = load_json("validation/learner06/learner_authority.direct.json")["value"]["results"]
    ambiguity_rows = [r for r in results if r["reason"] == "ambiguous-train-survivors"]
    check("deterministic ambiguity", len(ambiguity_rows) == 3 and all(r["selected_candidate"] is None and r["ambiguity_record"]["resolution"] == "reject-without-hidden-tie-break" for r in ambiguity_rows), "Distinct surviving candidates create addressed ambiguity records rather than hidden winners.", ambiguity_datasets=[r["dataset_id"] for r in ambiguity_rows])
    supersession_ok = next(r for r in results if r["dataset_id"] == "dataset:poly-affine-supersession")
    regression_reject = next(r for r in results if r["dataset_id"] == "dataset:supersession-regression-failure")
    check("supersession and regression impact", supersession_ok["accepted"] and supersession_ok["supersession_record"] is not None and supersession_ok["regression_impact"]["all_pass"] and not regression_reject["accepted"] and regression_reject["reason"] == "regression-impact", "Supersession is explicit and a proposal that changes pinned regression behavior is not promoted.")
    check("bounded-search termination", all(r["termination_certificate"]["completed"] and r["termination_certificate"]["evaluated_count"] == r["candidate_count"] for r in results), "Every data set records finite candidate enumeration and exact completion.")

    learner_chain_ok = verify_hash(learner_proof) and learner_proof["status"] == "pass" and learner_proof["independent_oracle_equal"] and learner_proof["direct_materialized_equal"] and learner_proof["tomagi_chain"]["execution"]["python_c_full_trace_equal"] and learner_proof["tomagi_chain"]["execution"]["python_c_emit_sequence_equal"]
    check("formal learner TOMAGI chain", learner_chain_ok, "The learner value is recomputed by the strict seeded compiler and equal Python/C TOMAGI execution.", proof_hash=learner_proof.get("content_hash"), cells=learner_proof.get("tomagi_chain",{}).get("program",{}).get("cells"))
    promotion_chain_ok = verify_hash(promotion_proof) and promotion_proof["status"] == "pass" and promotion_proof["direct_materialized_equal"] and promotion_proof["tomagi_chain"]["execution"]["python_c_full_trace_equal"] and promotion_proof["tomagi_chain"]["execution"]["python_c_emit_sequence_equal"]
    check("formal promotion TOMAGI chain", promotion_chain_ok, "Promotion, evidence enumeration, continuation snapshot, transaction and commit are formal and TOMAGI-materialized.", proof_hash=promotion_proof.get("content_hash"), cells=promotion_proof.get("tomagi_chain",{}).get("program",{}).get("cells"))

    plan = validate_plan(load_json("validation/learner06/promotion_authority.direct.json")["value"]["publication_plan"])
    parent = load_json("examples/learner06/prior_authority.json")["prior_terminal_head"]
    check("parent-bound 0.5.2 continuation", plan["schema"] == "TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.1" and plan["initial_head"] == parent and [p["sequence"] for p in plan["publications"]] == list(range(20,36)), "The new family decisions continue from, rather than replace, the repaired 0.5.2 terminal head.", initial_head=plan["initial_head"], terminal_head=plan["terminal_head"])
    check("immutable publication store", verify_hash(audit) and audit["valid"] and audit["errors"] == [] and verify_hash(reconstruction) and reconstruction["commit_count"] == 16 and (reconstruction["accepted_count"], reconstruction["rejected_count"]) == (9,7), "The generic same-host locked store exactly contains the formal continuation and reconstructs all outcomes.", audit_hash=audit["content_hash"], reconstruction_hash=reconstruction["content_hash"], store_tree=promotion_proof["store_tree"]["sha256"])

    imports = import_names(ROOT / "src/python/tomagi/immutable_store.py")
    check("mechanical host-service boundary", not any(name.startswith("tom_learner") or name.startswith("tom_world") for name in imports), "The immutable store imports no learner/world semantics; acceptance remains in formal authority.", imports=sorted(imports))

    rejection = build_rejection_capsule()
    write_json(VAL / "rejection_capsule.json", rejection)
    check("adversarial rejection capsule", rejection["status"] == "pass", "Hash, budget, ancestry, evidence, trace, ABI, finite-JSON, ambiguity and regression failures are rejected deterministically.", cases=rejection["case_count"], cases_passed=rejection["passed"], rejection_hash=rejection["content_hash"])

    count, tests_ok, tests_hash = test_status()
    check("complete conformance suite", tests_ok and count == 283, "The complete inherited, repair and Learner 0.2 suite ends in the exact passing timing-free summary for this release.", tests=count, tests_sha256=tests_hash)
    check("unchanged TOMAGI ABI", (HEADER_SIZE, STATE_SIZE, CELL_SIZE, len(list(Opcode))) == (128,64,48,16), "Learner 0.2 adds no opcode or binary record field.", header=HEADER_SIZE, state=STATE_SIZE, cell=CELL_SIZE, opcodes=len(list(Opcode)))

    release_proof_path = VAL / "learner06_release_artifact.proof.json"
    if release_proof_path.is_file():
        release_proof = load_json(release_proof_path)
        release_ok = (
            verify_hash(release_proof)
            and release_proof["status"] == "pass"
            and release_proof["repair_handoff_proof_hash"] == repair_proof["content_hash"]
            and release_proof["family_registry_hash"] == registry["content_hash"]
            and release_proof["learner_proof_hash"] == learner_proof["content_hash"]
            and release_proof["promotion_proof_hash"] == promotion_proof["content_hash"]
            and release_proof["artifact"]["matches_authored_document"]
            and release_proof["execution"]["python_c_full_trace_equal"]
            and release_proof["execution"]["python_c_emit_sequence_equal"]
        )
        check("release-document causal artifact", release_ok, "The release overview is literal source -> .tmg -> authenticated equal Python/C EMIT -> byte-identical Markdown.", proof_hash=release_proof.get("content_hash"), artifact_sha256=release_proof.get("artifact",{}).get("sha256"))

    handoff_proof_path = VAL / "kernel06_validation_handoff.proof.json"
    if handoff_proof_path.is_file():
        handoff_proof = load_json(handoff_proof_path)
        handoff_source = ROOT / "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.md"
        handoff_materialized = VAL / "CODEX_KERNEL_0_6_VALIDATION_HANDOFF.materialized.md"
        handoff_ok = (
            verify_hash(handoff_proof)
            and handoff_proof["status"] == "pass"
            and handoff_proof["artifact"]["matches_authored_document"]
            and handoff_proof["execution"]["python_c_full_trace_equal"]
            and handoff_proof["execution"]["python_c_emit_sequence_equal"]
            and handoff_materialized.read_bytes() == handoff_source.read_bytes()
        )
        check(
            "validation-handoff causal artifact",
            handoff_ok,
            "The delivered validation handoff is literal source -> .tmg -> authenticated equal Python/C EMIT -> byte-identical Markdown.",
            proof_hash=handoff_proof.get("content_hash"),
            artifact_sha256=handoff_proof.get("artifact", {}).get("sha256"),
        )

    core_status = "pass" if all(c["status"] == "pass" for c in checks) else "fail"
    core = attach_hash({
        "schema": "TOM-WQK-0.6-CORE-VALIDATION-1.0",
        "release": "0.6.0",
        "status": core_status,
        "checks_passed": sum(c["status"] == "pass" for c in checks),
        "checks_failed": sum(c["status"] == "fail" for c in checks),
        "checks": checks,
        "test_count": count,
        "canonical_seed_sha256": sha_bytes(seed),
        "repair_handoff_proof_hash": repair_proof["content_hash"],
        "family_registry_hash": registry["content_hash"],
        "learner_proof_hash": learner_proof["content_hash"],
        "promotion_proof_hash": promotion_proof["content_hash"],
        "terminal_head": plan["terminal_head"],
        "rejection_capsule_hash": rejection["content_hash"],
        "claim_boundary": "finite exact four-family learner with deterministic ambiguity, supersession/regression certificates and repaired 0.5.2 promotion authority; not noisy learning or AGI",
    })
    write_json(VAL / "validation_report_core.json", core)

    final_checks = list(checks)
    clean_hash = None
    if args.include_clean:
        clean = load_json("validation/learner06/clean_rebuild.json")
        clean_ok = verify_hash(clean) and clean["status"] == "pass" and clean["two_builds_equal"] and clean["all_boundaries_equal"] and clean["store_trees_equal"]
        final_checks.append({"name":"two-build clean replay","status":"pass" if clean_ok else "fail","detail":"Two generated-output-free source builds reproduce every declared boundary and store tree.","content_hash":clean.get("content_hash"),"compared_boundaries":clean.get("compared_boundaries")})
        clean_hash = clean.get("content_hash")
    status = "pass" if all(c["status"] == "pass" for c in final_checks) else "fail"
    report = attach_hash({
        "schema": "TOM-WQK-0.6-VALIDATION-1.0",
        "release": "0.6.0",
        "status": status,
        "core_validation_hash": core["content_hash"],
        "clean_rebuild_hash": clean_hash,
        "checks_passed": sum(c["status"] == "pass" for c in final_checks),
        "checks_failed": sum(c["status"] == "fail" for c in final_checks),
        "test_count": count,
        "checks": final_checks,
        "canonical_boundaries": {
            "seed": sha_bytes(seed),
            "family_registry": registry["content_hash"],
            "learner_program": learner_proof["tomagi_chain"]["program"]["sha256"],
            "learner_artifact": learner_proof["tomagi_chain"]["artifact"]["sha256"],
            "promotion_program": promotion_proof["tomagi_chain"]["program"]["sha256"],
            "promotion_artifact": promotion_proof["tomagi_chain"]["artifact"]["sha256"],
            "publication_plan": plan["content_hash"],
            "terminal_head": plan["terminal_head"],
            "promotion_store_tree": promotion_proof["store_tree"]["sha256"],
        },
        "evidence_boundary": "Python/C CPU traces executed and compared. GPU sources remain ABI mappings and were not physically dispatched for this learner release.",
        "claim_boundary": core["claim_boundary"],
    })
    write_json(VAL / "validation_report.json", report)
    lines=["# TOM World & Query Kernel 0.6 validation","",f"Status: **{status}**","",f"- Tests: **{count} passed**",f"- Checks: **{report['checks_passed']} passed, {report['checks_failed']} failed**",f"- Family registry: `{registry['content_hash']}`",f"- Learner proof: `{learner_proof['content_hash']}`",f"- Promotion proof: `{promotion_proof['content_hash']}`",f"- Terminal head: `{plan['terminal_head']}`",f"- Core validation: `{core['content_hash']}`",f"- Final validation: `{report['content_hash']}`"]
    if clean_hash: lines.append(f"- Clean replay: `{clean_hash}`")
    lines += ["","The learner and promotion decisions are formal authority. Host code performs bounded evaluation, strict validation, deterministic compilation/execution, independent comparison, immutable storage and authenticated materialization only.",""]
    (VAL / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status":status,"checks_passed":report["checks_passed"],"checks_failed":report["checks_failed"],"tests":count,"core_validation_hash":core["content_hash"],"validation_hash":report["content_hash"],"clean_rebuild_hash":clean_hash},indent=2,sort_keys=True))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
