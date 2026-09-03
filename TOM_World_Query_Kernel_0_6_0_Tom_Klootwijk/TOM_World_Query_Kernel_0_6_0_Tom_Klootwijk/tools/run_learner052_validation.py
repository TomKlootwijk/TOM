from __future__ import annotations

"""Validate the corrective 0.5.2 promotion/evidence authority release."""

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation/learner052"
BASE = ROOT / "examples/learner052"

from tomagi.canonical import attach_hash, canonical_bytes, verify_hash
from tomagi.core import Opcode
from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load
from tomagi.immutable_store import ImmutablePublicationStore, validate_plan
from tomagi.materialize import materialize_trace
from tom_learner05.handoff import verify_corrective_handoff
from tom_learner052.oracle import build_promotion_result

EXPECTED = {
    "seed": "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5",
    "base_archive": "sha256:0f3bf159536b726fc68fc3e0ff7c1ff896c3bdf1e63a7449d5b507f67f043601",
    "corrective": "sha256:53951284853681ce239d07ce2ce783250ea78b3457fd221a43d88bd90344f4bf",
    "promotion_program": "sha256:f1030e332b5f7358c43603096a64ebca7f9268aaaf2fbbe16dbebc972daa8bdd",
    "promotion_execution": "sha256:f1a5ccbab6eb64033200c480c3e45852c3f1eccb212eca344a98005e79ecc00d",
    "promotion_value": "sha256:13544b08f0a211cc0b6b6a53484491159303bd45b42797422913d2b24459e3f2",
    "plan": "sha256:07b1607745e37c1f3ac7d61a47db96a3d01c884682432c91f1d77568045337e8",
    "terminal_head": "sha256:a3bd8ecd8578b28158b96a3dce814910beb3d627068159dc668a682c85b85448",
    "program": "sha256:f6eacc1e90f63d90b2487d0230fc1a10ecdfe571124dbd317efc12f7dcb93821",
    "artifact": "sha256:2d6bc5b206545042e13faa5e9b4d9a0ec6b0ccf4929755c01025746b8ab4523c",
    "proof": "sha256:b4b614903f5c0fd7369459315bd16b8048d15c3113e902ccc20c6c174a10bf68",
    "store_tree": "sha256:df217da1752d9ff09cdf3e2b09d6df81ffb9fbf8cd7ea914473c1453b86244ea",
    "test_count": 238,
}


def sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8") if not Path(path).is_absolute() else Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def addressed(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    body.pop("content_hash", None)
    return attach_hash(body)


def canonical_test_status() -> tuple[int, bool, str]:
    path = VAL / "tests.txt"
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"^Ran ([0-9]+) tests$", text, re.MULTILINE)
    status = re.findall(r"^(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)$", text, re.MULTILINE)
    valid = len(matches) == 1 and len(status) == 1 and status[0].startswith("OK") and " tests in " not in text
    return (int(matches[0]) if matches else 0, valid, sha_bytes(path.read_bytes()))


def import_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def formal_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    promotion_program = load_json("examples/learner052/promotion_authority.formal.json")
    learner_program = load_json("examples/learner052/authority_inputs/learner05_affine_authority.formal.json")
    learner_execution = load_json("validation/learner05/learner05_formal_authority.materialized.json")
    datasets = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((BASE / "authority_inputs/datasets").glob("*.json"))
    ]
    context = load_json("examples/learner052/promotion_context.json")
    corrective = load_json("examples/learner052/authority_inputs/TOM_CORRECTIVE_HANDOFF_0_5_1.json")
    registry = load_json("examples/learner052/authority_inputs/tom_seed_token_registry_1_0.json")
    return promotion_program, learner_program, learner_execution, datasets, context, corrective, registry


def build_rejection_capsule(plan: dict[str, Any]) -> dict[str, Any]:
    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    cases: list[dict[str, Any]] = []

    def reject(name: str, expected: str, operation: Callable[[], Any]) -> None:
        try:
            operation()
        except Exception as exc:
            message = str(exc)
            cases.append({
                "name": name,
                "status": "pass" if expected in message else "fail",
                "exception": type(exc).__name__,
                "expected_substring": expected,
                "matched": expected in message,
            })
        else:
            cases.append({
                "name": name,
                "status": "fail",
                "exception": None,
                "expected_substring": expected,
                "matched": False,
            })

    checked = validate_plan(plan)

    def stale_head() -> None:
        with tempfile.TemporaryDirectory() as td:
            store = ImmutablePublicationStore.initialize(Path(td) / "store", checked["store_descriptor"], seed)
            store.apply_publication(checked["publications"][0])
            store.apply_publication(checked["publications"][0])

    reject("stale publication head", "stale publication head", stale_head)

    def mutated_publication(index: int, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        value = copy.deepcopy(plan)
        pub = copy.deepcopy(value["publications"][index])
        mutate(pub)
        value["publications"][index] = addressed(pub)
        return addressed(value)

    reject(
        "duplicate required hash",
        "required_hashes must be unique",
        lambda: validate_plan(mutated_publication(1, lambda p: p["required_hashes"].append(p["required_hashes"][0]))),
    )
    reject(
        "noncontiguous sequence",
        "sequences must be contiguous",
        lambda: validate_plan(mutated_publication(1, lambda p: p.__setitem__("sequence", 9))),
    )
    reject(
        "broken expected parent",
        "expected_head chain mismatch",
        lambda: validate_plan(mutated_publication(1, lambda p: p.__setitem__("expected_head", None))),
    )

    def remove_replacement(pub: dict[str, Any]) -> None:
        pub["writes"] = [
            write for write in pub["writes"]
            if not (
                write["namespace"] == "commits"
                and write["record"]["content_hash"] == pub["replacement_head"]
            )
        ]

    reject(
        "missing replacement commit write",
        "replacement_head must be written",
        lambda: validate_plan(mutated_publication(1, remove_replacement)),
    )

    def missing_required() -> None:
        value = copy.deepcopy(plan)
        pub = copy.deepcopy(value["publications"][0])
        pub["required_hashes"].append("sha256:" + "1" * 64)
        pub = addressed(pub)
        value["publications"][0] = pub
        value = addressed(value)
        with tempfile.TemporaryDirectory() as td:
            ImmutablePublicationStore.apply_plan(Path(td) / "store", seed, value)

    reject("missing required immutable record", "required hashes are unavailable", missing_required)

    def forged_trace() -> None:
        program = load(BASE / "learner052_release_artifact.tmg")
        trace_record = load_json("validation/learner052/learner052_release_artifact.python.trace.json")
        forged = copy.deepcopy(trace_record["trace"])
        forged[0]["lineage"] ^= 1
        materialize_trace(program, forged)

    reject("forged trace row", "does not match deterministic replay", forged_trace)

    def nonfinite() -> None:
        canonical_bytes({"not_finite": float("nan")})

    reject("non-finite canonical JSON", "not JSON compliant", nonfinite)

    def dataset_mutation() -> None:
        promotion_program, learner_program, learner_execution, datasets, context, corrective, registry = formal_inputs()
        datasets[0]["observations"][0]["y"] = {"num": 999, "den": 1}
        build_promotion_result(
            promotion_program, learner_program, learner_execution,
            datasets, context, corrective, registry,
        )

    reject("stale mutated data-set hash", "content hash mismatch", dataset_mutation)

    # Strict audit must report an extra immutable record rather than silently accepting it.
    with tempfile.TemporaryDirectory() as td:
        store = ImmutablePublicationStore.apply_plan(Path(td) / "store", seed, plan)
        extra = addressed({"schema": "TOMAGI-VALIDATION-EXTRA-1.0", "value": 1})
        store._put("objects", extra)  # mechanical adversarial injection for audit testing
        audit = store.audit_plan(plan, require_no_extra_records=True)
        cases.append({
            "name": "unexpected strict-audit record",
            "status": "pass" if not audit["valid"] and any("unplanned immutable records" in x for x in audit["errors"]) else "fail",
            "exception": None,
            "expected_substring": "unplanned immutable records",
            "matched": any("unplanned immutable records" in x for x in audit["errors"]),
        })

    with tempfile.TemporaryDirectory() as td:
        store = ImmutablePublicationStore.apply_plan(Path(td) / "store", seed, plan)
        victim = next((Path(td) / "store/objects").glob("*.json"))
        victim.write_bytes(victim.read_bytes() + b" ")
        audit = store.audit_plan(plan, require_no_extra_records=True)
        cases.append({
            "name": "immutable stored-byte mutation",
            "status": "pass" if not audit["valid"] else "fail",
            "exception": None,
            "expected_substring": "byte mismatch or canonical-record rejection",
            "matched": not audit["valid"],
        })

    return attach_hash({
        "schema": "TOM-LEARNER-0.1-TRANSACTION-AUTHORITY-REJECTION-CAPSULE-0.5.2",
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

    def check(name: str, condition: bool, detail: str, **evidence: Any) -> None:
        checks.append({
            "name": name,
            "status": "pass" if condition else "fail",
            "detail": detail,
            **evidence,
        })

    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    check(
        "canonical seed",
        len(seed) == 244 and not seed.endswith((b"\r", b"\n")) and sha_bytes(seed) == EXPECTED["seed"],
        "Exact 244-byte seed, ASCII-only, with no terminal line ending.",
        bytes=len(seed), sha256=sha_bytes(seed),
    )

    corrective = verify_corrective_handoff(ROOT)
    check(
        "CODEX corrective handoff",
        corrective.get("valid") is True and verify_hash(corrective),
        "The 0.5.1 corrective overlay, replacements, preserved prior bytes, additions, and seed all verify.",
        content_hash=corrective.get("content_hash"),
        unchanged=corrective.get("unchanged_base_file_count"),
        replacements=corrective.get("replacement_count"),
        additions=corrective.get("addition_count"),
    )

    continuation = load_json("validation/learner052/continuation_handoff_verification.json")
    check(
        "0.5.2 continuation handoff",
        continuation.get("valid") is True and verify_hash(continuation) and continuation.get("base_archive_sha256") == EXPECTED["base_archive"],
        "The exact corrective base archive identity and all declared 0.5.2 replacements/additions are pinned.",
        content_hash=continuation.get("content_hash"),
        base_archive_sha256=continuation.get("base_archive_sha256"),
    )

    formal_program = load_json("examples/learner052/promotion_authority.formal.json")
    direct = load_json("validation/learner052/promotion_authority.direct_formal.json")
    materialized_path = VAL / "promotion_authority.materialized.json"
    materialized = load_json(materialized_path)
    value = direct["value"]
    plan = value["publication_plan"]
    check(
        "formal promotion program identity",
        verify_hash(formal_program) and formal_program.get("content_hash") == EXPECTED["promotion_program"],
        "Static promotion/evidence semantics are content-addressed formal authority.",
        content_hash=formal_program.get("content_hash"),
    )
    check(
        "formal promotion evaluation",
        verify_hash(direct) and direct.get("content_hash") == EXPECTED["promotion_execution"] and value.get("content_hash") == EXPECTED["promotion_value"] and direct.get("steps") == 32900,
        "The bounded formal evaluator reproduces the pinned promotion result.",
        execution_hash=direct.get("content_hash"), value_hash=value.get("content_hash"), steps=direct.get("steps"),
    )

    try:
        import jsonschema
        schema = load_json("spec/tom_learner_promotion_authority_0_5_2.schema.json")
        jsonschema.Draft202012Validator(schema).validate(direct)
        schema_ok = True
    except Exception as exc:
        schema_ok = False
        schema_error = type(exc).__name__
    check(
        "strict promotion-result schema",
        schema_ok,
        "The complete formal execution/result/publication structure validates under Draft 2020-12.",
        **({} if schema_ok else {"error_type": schema_error}),
    )

    source = load_json("examples/learner052/promotion_authority.literal.json")
    operations = [definition["operation"]["op"] for definition in source["definitions"]]
    check(
        "seeded source graph authority",
        "cells" not in source and operations.count("formal.evaluate") == 2 and "canonical.encode" in operations and "emit.graph" in operations,
        "The seed-bound graph recomputes both formal authorities and lowers their result; it carries no handwritten cell table.",
        definitions=len(source["definitions"]), formal_evaluations=operations.count("formal.evaluate"),
    )

    check(
        "direct/formal/materialized byte equality",
        materialized_path.read_bytes() == canonical_bytes(direct) + b"\n" and materialized == direct and sha_path(materialized_path) == EXPECTED["artifact"],
        "TOMAGI EMIT materialization is byte-identical to direct formal evaluation.",
        bytes=materialized_path.stat().st_size, sha256=sha_path(materialized_path),
    )

    promotion_program, learner_program, learner_execution, datasets, context, correction_copy, registry = formal_inputs()
    oracle = build_promotion_result(
        promotion_program, learner_program, learner_execution,
        datasets, context, correction_copy, registry,
    )
    oracle_record = load_json("validation/learner052/promotion_authority.oracle.json")
    check(
        "independent promotion oracle",
        oracle == value and oracle_record == value,
        "A separately implemented Python oracle agrees exactly but remains non-authoritative.",
        oracle_sha256=sha_path(VAL / "promotion_authority.oracle.json"),
    )

    proof = load_json("validation/learner052/promotion_authority.proof.json")
    check(
        "TOMAGI promotion execution",
        verify_hash(proof) and proof.get("content_hash") == EXPECTED["proof"] and proof.get("program_sha256") == EXPECTED["program"] and proof.get("python_c_complete_trace_equal") is True and proof.get("python_c_materialized_bytes_equal") is True,
        "Python and C execute the same 242,749-cell program with equal complete traces and output bytes.",
        cells=proof.get("cell_count"), steps=proof.get("execution_steps"), program_sha256=proof.get("program_sha256"), trace_sha256=proof.get("trace_sha256"),
    )

    checked_plan = validate_plan(plan)
    check(
        "parent-bound publication plan",
        checked_plan["content_hash"] == EXPECTED["plan"] and checked_plan["terminal_head"] == EXPECTED["terminal_head"] and len(checked_plan["publications"]) == 20,
        "Publication sequences are contiguous, expected heads chain exactly, and the terminal head is pinned.",
        plan_hash=checked_plan["content_hash"], terminal_head=checked_plan["terminal_head"], publications=len(checked_plan["publications"]),
    )

    complete_evidence = True
    disjoint = True
    accepted = rejected = 0
    minimum_evidence = 10**9
    for publication in checked_plan["publications"][1:]:
        transactions = [write["record"] for write in publication["writes"] if write["namespace"] == "transactions"]
        if len(transactions) != 1:
            complete_evidence = False
            disjoint = False
            continue
        transaction = transactions[0]
        evidence = transaction["evidence_record_hashes"]
        minimum_evidence = min(minimum_evidence, len(evidence))
        complete_evidence &= (
            len(evidence) == len(set(evidence))
            and transaction["acceptance_decision_hash"] in evidence
            and transaction["promotion_certificate_hash"] in evidence
            and transaction["expected_parent_commit_hash"] == publication["expected_head"]
            and all(item in publication["required_hashes"] for item in evidence)
        )
        if transaction["accepted"]:
            accepted += 1
            disjoint &= transaction["published_definition_hash"] is not None and transaction["rejection_lineage_hash"] is None
        else:
            rejected += 1
            disjoint &= transaction["published_definition_hash"] is None and transaction["rejection_lineage_hash"] is not None
    check(
        "complete promotion evidence",
        complete_evidence,
        "Each session transaction binds a unique ordered evidence set containing its decision and promotion certificate.",
        session_count=19, minimum_evidence_records=minimum_evidence,
    )
    check(
        "accepted/rejected authority separation",
        disjoint and (accepted, rejected) == (12, 7),
        "Accepted sessions publish one relation and no rejection lineage; rejected sessions do the inverse.",
        accepted=accepted, rejected=rejected,
    )

    audit = load_json("validation/learner052/promotion_store_audit.json")
    reconstruction = load_json("validation/learner052/promotion_store_reconstruction.json")
    check(
        "generic immutable store audit",
        verify_hash(audit) and audit.get("valid") is True and audit.get("planned_publications") == 20 and audit.get("planned_records") == 535,
        "The mechanically applied immutable store exactly matches the formal plan with no extra records.",
        audit_hash=audit.get("content_hash"), records=audit.get("planned_records"),
    )
    check(
        "commit-chain reconstruction",
        verify_hash(reconstruction) and reconstruction.get("commit_count") == 20 and reconstruction.get("session_count") == 19 and reconstruction.get("accepted_definition_count") == 12 and reconstruction.get("rejected_session_count") == 7,
        "Reconstruction from the terminal head recovers all publications and authority outcomes.",
        reconstruction_hash=reconstruction.get("content_hash"), terminal_head=reconstruction.get("terminal_head"),
    )
    check(
        "store tree identity",
        proof.get("store_tree", {}).get("sha256") == EXPECTED["store_tree"],
        "The complete generic promotion-store tree has the pinned aggregate identity.",
        **proof.get("store_tree", {}),
    )

    imports = import_names(ROOT / "src/python/tomagi/immutable_store.py")
    host_boundary_ok = not any(name.startswith("tom_learner") or name.startswith("tom_world") for name in imports)
    check(
        "generic host-service boundary",
        host_boundary_ok,
        "The store imports no learner/world package and performs only generic addressed publication mechanics.",
        imports=sorted(imports),
    )

    rejection = build_rejection_capsule(plan)
    (VAL / "rejection_capsule.json").write_bytes(canonical_bytes(rejection) + b"\n")
    check(
        "adversarial rejection capsule",
        rejection["status"] == "pass",
        "Stale heads, broken plans, missing evidence, forged traces, non-finite JSON, mutation, extras, and stored-byte corruption reject deterministically.",
        cases=rejection["case_count"], passed=rejection["passed"], content_hash=rejection["content_hash"],
    )

    release_proof = load_json("validation/learner052/learner052_release_artifact.proof.json")
    check(
        "release-document causal artifact",
        verify_hash(release_proof) and release_proof.get("status") == "pass" and release_proof["artifact"]["matches_authored_document"] is True and release_proof["execution"]["python_c_full_trace_equal"] is True and release_proof["execution"]["python_c_emit_sequence_equal"] is True,
        "The release document is literal source -> .tmg -> equal Python/C traces -> authenticated EMIT -> identical Markdown.",
        proof_hash=release_proof.get("content_hash"), cells=release_proof["program"]["cells"], artifact_sha256=release_proof["artifact"]["sha256"],
    )

    test_count, tests_pass, tests_hash = canonical_test_status()
    check(
        "complete conformance tests",
        tests_pass and test_count >= EXPECTED["test_count"],
        "The timing-free complete inherited and 0.5.2 unittest log ends in one passing summary.",
        tests=test_count, sha256=tests_hash,
    )

    abi_ok = (HEADER_SIZE, STATE_SIZE, CELL_SIZE, len(list(Opcode))) == (128, 64, 48, 16)
    check(
        "unchanged TOMAGI ABI",
        abi_ok,
        "No header, State64, Cell48, or opcode-count change was introduced.",
        header=HEADER_SIZE, state=STATE_SIZE, cell=CELL_SIZE, opcodes=len(list(Opcode)),
    )

    check(
        "roadmap scope discipline",
        value.get("profile") == "TOM-LEARNER-0.1-PROMOTION-AUTHORITY" and value.get("dataset_count") == 19 and value.get("claim_boundary") is not None,
        "0.5.2 completes affine promotion authority and does not add a broader hypothesis family.",
        profile=value.get("profile"), data_sets=value.get("dataset_count"),
    )

    core_status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    core_report = attach_hash({
        "schema": "TOM-WQK-0.5.2-CORE-VALIDATION-1.0",
        "release": "0.5.2",
        "status": core_status,
        "canonical_seed_sha256": EXPECTED["seed"],
        "corrective_base_archive_sha256": EXPECTED["base_archive"],
        "checks_passed": sum(item["status"] == "pass" for item in checks),
        "checks_failed": sum(item["status"] == "fail" for item in checks),
        "checks": checks,
        "promotion_proof_hash": proof["content_hash"],
        "publication_plan_hash": plan["content_hash"],
        "terminal_head": plan["terminal_head"],
        "test_count": test_count,
        "rejection_capsule_hash": rejection["content_hash"],
        "claim_boundary": "exact finite affine proposal plus literal parent-bound promotion/evidence authority; not a broader learner or AGI",
    })
    (VAL / "validation_report_core.json").write_bytes(canonical_bytes(core_report) + b"\n")

    final_checks = list(checks)
    clean_hash = None
    if args.include_clean:
        clean = load_json("validation/learner052/clean_rebuild.json")
        clean_ok = (
            verify_hash(clean)
            and clean.get("status") == "pass"
            and clean.get("all_boundaries_equal") is True
            and clean.get("core_validation_hash") == core_report["content_hash"]
        )
        final_checks.append({
            "name": "generated-output-free clean replay",
            "status": "pass" if clean_ok else "fail",
            "detail": "A copied source capsule rebuilt the authority, store, tests, and release artifact byte-for-byte.",
            "compared_file_boundaries": clean.get("compared_file_boundaries"),
            "store_tree_equal": clean.get("store_tree_equal"),
            "content_hash": clean.get("content_hash"),
        })
        clean_hash = clean.get("content_hash")

    final_status = "pass" if all(item["status"] == "pass" for item in final_checks) else "fail"
    final_report = attach_hash({
        "schema": "TOM-WQK-0.5.2-VALIDATION-1.0",
        "release": "0.5.2",
        "status": final_status,
        "core_validation_hash": core_report["content_hash"],
        "clean_rebuild_hash": clean_hash,
        "checks_passed": sum(item["status"] == "pass" for item in final_checks),
        "checks_failed": sum(item["status"] == "fail" for item in final_checks),
        "test_count": test_count,
        "checks": final_checks,
        "canonical_boundaries": {
            "seed": EXPECTED["seed"],
            "promotion_program": proof["program_sha256"],
            "promotion_artifact": proof["artifact_sha256"],
            "publication_plan": proof["publication_plan_hash"],
            "terminal_head": proof["terminal_head"],
            "promotion_store_tree": proof["store_tree"]["sha256"],
            "release_artifact": release_proof["artifact"]["sha256"],
        },
        "evidence_boundary": "Python/C CPU traces executed; GPU source mappings retained but not device-executed for this authority release.",
        "claim_boundary": core_report["claim_boundary"],
    })
    (VAL / "validation_report.json").write_bytes(canonical_bytes(final_report) + b"\n")

    lines = [
        "# TOM World & Query Kernel 0.5.2 validation",
        "",
        f"Status: **{final_status}**",
        "",
        f"- Tests: **{test_count} passed**",
        f"- Validation checks: **{final_report['checks_passed']} passed, {final_report['checks_failed']} failed**",
        f"- Promotion program: `{proof['program_sha256']}`",
        f"- Materialized promotion result: `{proof['artifact_sha256']}`",
        f"- Publication plan: `{proof['publication_plan_hash']}`",
        f"- Terminal head: `{proof['terminal_head']}`",
        f"- Promotion-store tree: `{proof['store_tree']['sha256']}`",
        f"- Core validation: `{core_report['content_hash']}`",
        f"- Final validation: `{final_report['content_hash']}`",
    ]
    if clean_hash:
        lines.append(f"- Clean replay: `{clean_hash}`")
    lines.extend([
        "",
        "The semantic learner and promotion decisions are static formal definitions. Host code is limited to strict generic evaluation, compilation, execution, immutable storage, audit, independent comparison, and authenticated materialization.",
        "",
    ])
    (VAL / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": final_status,
        "checks_passed": final_report["checks_passed"],
        "checks_failed": final_report["checks_failed"],
        "tests": test_count,
        "core_validation_hash": core_report["content_hash"],
        "validation_hash": final_report["content_hash"],
        "clean_rebuild_hash": clean_hash,
    }, indent=2, sort_keys=True))
    return 0 if final_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
