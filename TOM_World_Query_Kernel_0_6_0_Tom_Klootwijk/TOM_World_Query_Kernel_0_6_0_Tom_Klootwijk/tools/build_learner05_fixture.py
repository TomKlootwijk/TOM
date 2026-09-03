from __future__ import annotations

"""Build the literal TOM Learner 0.1 benchmark and append-only overlay store.

All case semantics originate in ``examples/learner05/benchmark_plan.json``.
This tool provides generic deterministic expansion, exact learning, independent
baseline comparison, parent-bound promotion, and evidence serialization.
"""

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]

from tom_world03.canonical import attach_hash, canonical_bytes, require_hash
from tom_world03.rational import Q
from tom_learner05.affine import candidate_coefficients
from tom_learner05.baseline import trusted_affine_learning_baseline
from tom_learner05.handoff import verify_corrective_handoff
from tom_learner05.learner import learn_observation_set
from tom_learner05.model import ObservationSet
from tom_learner05.split import deterministic_split
from tom_learner05.store import LearnerStore

PLAN = ROOT / "examples/learner05/benchmark_plan.json"
DATASETS = ROOT / "examples/learner05/datasets"
STORE = ROOT / "examples/learner05/learner_store"
VALIDATION = ROOT / "validation/learner05"
SEED = ROOT / "TOM_seed_genome_2026-09-01.txt"


def _q(value: Any) -> Q:
    return Q.from_value(value)


def _hash_tree(root: Path) -> str:
    h = hashlib.sha256()
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(8, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return "sha256:" + h.hexdigest()


def _slug(dataset_id: str) -> str:
    return dataset_id.replace(":", "_").replace("/", "_")


def _policy_records(plan: Mapping[str, Any], case: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    split = attach_hash({
        "schema": "TOM-LEARNER-SPLIT-POLICY-0.1",
        **dict(plan["default_split_policy"]),
    })
    family = attach_hash({
        "schema": "TOM-AFFINE-HYPOTHESIS-FAMILY-0.1",
        **dict(plan["default_hypothesis_family"]),
    })
    acceptance_payload = dict(plan["default_acceptance_policy"])
    acceptance_payload.update(dict(case.get("policy_override", {})))
    acceptance = attach_hash({
        "schema": "TOM-LEARNER-ACCEPTANCE-POLICY-0.1",
        **acceptance_payload,
    })
    return split, family, acceptance


def _observation(dataset_id: str, index: str, t: Q, y: Q, *, note: str) -> dict[str, Any]:
    return attach_hash({
        "schema": "TOM-EXACT-OBSERVATION-0.1",
        "id": f"obs:{_slug(dataset_id)}:{index}",
        "t": t.to_record(),
        "y": y.to_record(),
        "provenance": {
            "source": "literal TOM Learner 0.1 benchmark plan",
            "dataset": dataset_id,
            "note": note,
        },
    })


def _base_observations(plan: Mapping[str, Any], case: Mapping[str, Any]) -> list[dict[str, Any]]:
    count = int(case["count"])
    start = _q(plan["time_grid"]["start"])
    step = _q(plan["time_grid"]["step"])
    kind = case["kind"]
    values: list[dict[str, Any]] = []
    for index in range(count):
        if kind == "constant-input":
            t = _q(case["t"])
            y = _q(case["y"])
        else:
            t = start + step * index
            if kind == "affine":
                a, b = _q(case["a"]), _q(case["b"])
            elif kind == "piecewise":
                section = case["left"] if t < _q(case["switch_at"]) else case["right"]
                a, b = _q(section["a"]), _q(section["b"])
            else:
                raise ValueError(f"unsupported benchmark case kind {kind}")
            y = a * t + b
        values.append(_observation(case["id"], f"{index:03d}", t, y, note=f"{kind} observation {index}"))
    return values


def _dataset_record(plan: Mapping[str, Any], case: Mapping[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    split, family, acceptance = _policy_records(plan, case)
    observations = sorted(observations, key=lambda item: item["id"])
    return attach_hash({
        "schema": "TOM-AFFINE-OBSERVATION-SET-0.1",
        "profile": "TOM-LEARNER-0.1",
        "id": case["id"],
        "seed_sha256": plan["canonical_seed_sha256"],
        "base_world_hash": plan["base_world_hash"],
        "base_handoff_hash": plan["base_handoff_hash"],
        "domain": {"input": "t", "output": "y", "numeric": "exact-rational"},
        "observations": observations,
        "split_policy": split,
        "hypothesis_family": family,
        "acceptance_policy": acceptance,
        "provenance": {
            "source_plan_hash": plan["content_hash"],
            "case_id": case["id"],
            "case_kind": case["kind"],
            "labels_are_not_used_for_split_assignment": True,
        },
    })


def _mutate(plan: Mapping[str, Any], case: Mapping[str, Any], clean: dict[str, Any]) -> dict[str, Any]:
    mutation = case.get("mutation")
    if mutation is None:
        return clean
    observations = [dict(item) for item in clean["observations"]]
    if mutation["kind"] == "split-outlier":
        dataset = ObservationSet.from_record(clean)
        split = deterministic_split(dataset)
        ids = split["splits"][mutation["target_split"]]
        target_id = ids[int(mutation["ordinal"])]
        for index, item in enumerate(observations):
            if item["id"] != target_id:
                continue
            changed = dict(item)
            changed["y"] = (_q(item["y"]) + _q(mutation["delta"])).to_record()
            changed["provenance"] = {**dict(item["provenance"]), "mutation": mutation}
            observations[index] = attach_hash(changed)
            break
        else:
            raise AssertionError("split mutation target not found")
    elif mutation["kind"] == "duplicate-contradiction":
        source = observations[int(mutation["source_ordinal"])]
        duplicate = _observation(
            case["id"], "duplicate",
            _q(source["t"]), _q(source["y"]) + _q(mutation["delta"]),
            note="literal contradictory duplicate input",
        )
        observations.append(duplicate)
    else:
        raise ValueError(f"unsupported mutation kind {mutation['kind']}")
    return _dataset_record(plan, case, observations)


def _selected_coefficients(run) -> dict[str, Any] | None:
    selected_hash = run.selection.get("selected_candidate_hash")
    if selected_hash is None:
        return None
    for candidate in run.candidates:
        if candidate["content_hash"] == selected_hash:
            a, b = candidate_coefficients(candidate)
            return {"a": a.to_record(), "b": b.to_record()}
    raise AssertionError("selection candidate absent")


def _normalize_expected(expected: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(expected)
    if out.get("accepted") and "a" in out:
        out["coefficients"] = {"a": _q(out.pop("a")).to_record(), "b": _q(out.pop("b")).to_record()}
    return out


def build() -> dict[str, Any]:
    handoff = verify_corrective_handoff(ROOT)
    if not handoff["valid"]:
        raise ValueError("corrective handoff verification failed: " + "; ".join(handoff["errors"]))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    require_hash(plan, label="learner benchmark plan")
    DATASETS.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    for path in DATASETS.glob("*.json"):
        path.unlink()
    if STORE.exists():
        shutil.rmtree(STORE)

    manifest_rows: list[dict[str, Any]] = []
    oracle_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    datasets: list[tuple[dict[str, Any], ObservationSet]] = []

    for case in plan["cases"]:
        clean = _dataset_record(plan, case, _base_observations(plan, case))
        record = _mutate(plan, case, clean)
        dataset = ObservationSet.from_record(record)
        path = DATASETS / f"{_slug(dataset.id)}.json"
        path.write_bytes(canonical_bytes(record) + b"\n")
        datasets.append((record, dataset))
        manifest_rows.append({
            "id": dataset.id,
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "content_hash": dataset.content_hash,
            "file_sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            "observations": len(dataset.observations),
        })
        oracle_rows.append({"id": dataset.id, **_normalize_expected(case["expected"])})

    benchmark_manifest = attach_hash({
        "schema": "TOM-LEARNER-BENCHMARK-MANIFEST-0.1",
        "profile": "TOM-LEARNER-0.1",
        "plan_hash": plan["content_hash"],
        "dataset_count": len(manifest_rows),
        "datasets": manifest_rows,
    })
    benchmark_oracle = attach_hash({
        "schema": "TOM-LEARNER-BENCHMARK-ORACLE-0.1",
        "profile": "TOM-LEARNER-0.1",
        "plan_hash": plan["content_hash"],
        "boundary": "read by validation only; never passed to fitting or selection",
        "cases": oracle_rows,
    })
    (ROOT / "examples/learner05/benchmark_manifest.json").write_bytes(canonical_bytes(benchmark_manifest) + b"\n")
    (ROOT / "examples/learner05/benchmark_oracle.json").write_bytes(canonical_bytes(benchmark_oracle) + b"\n")

    store = LearnerStore.initialize(STORE, SEED.read_bytes())
    accepted_count = 0
    false_promotions = 0
    recovery_errors = 0
    for (raw, dataset), oracle in zip(datasets, oracle_rows):
        run = learn_observation_set(dataset)
        baseline = trusted_affine_learning_baseline(raw)
        selected = _selected_coefficients(run)
        baseline_semantic = baseline["semantic"]
        baseline_equal = (
            run.accepted == baseline_semantic["accepted"]
            and selected == baseline_semantic["selected_coefficients"]
            and run.split_certificate["splits"] == baseline_semantic["splits"]
        )
        expected_accept = bool(oracle["accepted"])
        accepted_count += int(run.accepted)
        false_promotions += int(run.accepted and not expected_accept)
        if expected_accept and selected != oracle["coefficients"]:
            recovery_errors += 1
        result_rows.append({
            **run.summary(),
            "expected_accepted": expected_accept,
            "selected_coefficients": selected,
            "expected_coefficients": oracle.get("coefficients"),
            "baseline_equal": baseline_equal,
            "split_counts": run.split_certificate["counts"],
            "fit_input_hash": run.enumeration["fit_input_hash"],
        })
        baseline_rows.append({
            "observation_set_id": dataset.id,
            "learner_accepted": run.accepted,
            "baseline_accepted": baseline_semantic["accepted"],
            "learner_coefficients": selected,
            "baseline_coefficients": baseline_semantic["selected_coefficients"],
            "equal": baseline_equal,
            "baseline_hash": baseline["content_hash"],
        })
        parent = store.head()
        store.commit_learning(run, expected_parent=parent)

    audit = store.audit()
    reconstruction = store.reconstruct()
    if not audit["valid"]:
        raise ValueError("learner-store audit failed: " + "; ".join(audit["errors"]))

    # Leakage probes: mutate one holdout value and one validation value while
    # preserving IDs.  Train-derived coefficients and fit_input_hash must remain
    # equal; only acceptance evidence is allowed to change.
    reference_raw, reference_dataset = datasets[3]  # clean_double
    reference_run = learn_observation_set(reference_dataset)
    leakage_rows: list[dict[str, Any]] = []
    for split_name in ("validation", "holdout"):
        target_id = reference_run.split_certificate["splits"][split_name][0]
        mutated_observations = []
        for item in reference_raw["observations"]:
            if item["id"] != target_id:
                mutated_observations.append(item)
                continue
            changed = dict(item)
            changed["y"] = (_q(item["y"]) + Q(7)).to_record()
            changed["provenance"] = {**dict(item["provenance"]), "leakage_probe": split_name}
            mutated_observations.append(attach_hash(changed))
        mutated_raw = attach_hash({**reference_raw, "observations": mutated_observations})
        mutated = ObservationSet.from_record(mutated_raw)
        mutated_run = learn_observation_set(mutated)
        leakage_rows.append({
            "mutated_split": split_name,
            "target_id": target_id,
            "split_ids_equal": reference_run.split_certificate["splits"] == mutated_run.split_certificate["splits"],
            "assignment_basis_hash_equal": reference_run.split_certificate["assignment_basis_hash"] == mutated_run.split_certificate["assignment_basis_hash"],
            "fit_input_hash_equal": reference_run.enumeration["fit_input_hash"] == mutated_run.enumeration["fit_input_hash"],
            "selected_coefficients_equal": _selected_coefficients(reference_run) == _selected_coefficients(mutated_run),
            "reference_accepted": reference_run.accepted,
            "mutated_accepted": mutated_run.accepted,
        })
    leakage_certificate = attach_hash({
        "schema": "TOM-LEARNER-DATA-LEAKAGE-CERTIFICATE-0.1",
        "profile": "TOM-LEARNER-0.1",
        "reference_dataset_hash": reference_dataset.content_hash,
        "probes": leakage_rows,
        "valid": all(
            row["split_ids_equal"]
            and row["assignment_basis_hash_equal"]
            and row["fit_input_hash_equal"]
            and row["selected_coefficients_equal"]
            and row["reference_accepted"]
            and not row["mutated_accepted"]
            for row in leakage_rows
        ),
    })

    baseline_comparison = attach_hash({
        "schema": "TOM-LEARNER-INDEPENDENT-BASELINE-COMPARISON-0.1",
        "profile": "TOM-LEARNER-0.1",
        "dataset_count": len(baseline_rows),
        "all_equal": all(row["equal"] for row in baseline_rows),
        "rows": baseline_rows,
    })
    fixture_report = attach_hash({
        "schema": "TOM-LEARNER-FIXTURE-REPORT-0.1",
        "profile": "TOM-LEARNER-0.1",
        "corrective_handoff_verification_hash": handoff["content_hash"],
        "corrective_handoff_hash": handoff["corrective_handoff_hash"],
        "plan_hash": plan["content_hash"],
        "manifest_hash": benchmark_manifest["content_hash"],
        "oracle_hash": benchmark_oracle["content_hash"],
        "dataset_count": len(datasets),
        "positive_cases": sum(bool(row["expected_accepted"]) for row in result_rows),
        "negative_cases": sum(not bool(row["expected_accepted"]) for row in result_rows),
        "accepted_count": accepted_count,
        "false_promotions": false_promotions,
        "exact_recovery_errors": recovery_errors,
        "baseline_all_equal": baseline_comparison["all_equal"],
        "leakage_probes_valid": leakage_certificate["valid"],
        "store": {
            "head": store.head(),
            "tree_sha256": _hash_tree(STORE),
            "audit_hash": audit["content_hash"],
            "reconstruction_hash": reconstruction["content_hash"],
            "commit_count": audit["commit_count"],
            "object_count": audit["object_count"],
        },
        "results": result_rows,
        "status": "pass" if (
            false_promotions == 0 and recovery_errors == 0
            and baseline_comparison["all_equal"] and leakage_certificate["valid"] and audit["valid"]
            and all(row["accepted"] == row["expected_accepted"] for row in result_rows)
        ) else "fail",
    })

    (VALIDATION / "corrective_handoff_verification.json").write_bytes(canonical_bytes(handoff) + b"\n")
    (VALIDATION / "baseline_comparison.json").write_bytes(canonical_bytes(baseline_comparison) + b"\n")
    (VALIDATION / "leakage_certificate.json").write_bytes(canonical_bytes(leakage_certificate) + b"\n")
    (VALIDATION / "store_audit.json").write_bytes(canonical_bytes(audit) + b"\n")
    (VALIDATION / "store_reconstruction.json").write_bytes(canonical_bytes(reconstruction) + b"\n")
    (VALIDATION / "fixture_report.json").write_bytes(canonical_bytes(fixture_report) + b"\n")
    if fixture_report["status"] != "pass":
        raise ValueError("learner fixture did not pass")
    return fixture_report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
