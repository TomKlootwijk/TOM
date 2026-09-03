"""Command-line interface for TOM Learner 0.1 / WQK 0.5."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

from tom_world03.canonical import canonical_bytes

from .baseline import trusted_affine_learning_baseline
from .handoff import verify_corrective_handoff, verify_literal_handoff
from .io import load_observation_set
from .learner import learn_observation_set
from .store import LearnerStore


def _emit(value: Mapping[str, Any] | list[Any], output: str | None = None) -> None:
    data = canonical_bytes(value) + b"\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tom-learner05",
        description=(
            "Reference affine oracle/evidence-store tools and corrective seeded-authority verification"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_handoff = sub.add_parser("verify-handoff", help="verify every 0.4.2 authoritative literal file")
    p_handoff.add_argument("root", nargs="?", default=".")
    p_handoff.add_argument("--handoff")
    p_handoff.add_argument("--output")

    p_corrective_handoff = sub.add_parser(
        "verify-corrective-handoff",
        help="verify the 0.4.2 base plus the explicit 0.5.1 corrective overlay",
    )
    p_corrective_handoff.add_argument("root", nargs="?", default=".")
    p_corrective_handoff.add_argument("--corrective")
    p_corrective_handoff.add_argument("--output")

    p_validate = sub.add_parser("validate-dataset", help="verify and typecheck one observation set")
    p_validate.add_argument("dataset")
    p_validate.add_argument("--output")

    p_split = sub.add_parser("split", help="produce the deterministic ID-only train/validation/holdout split")
    p_split.add_argument("dataset")
    p_split.add_argument("--output")

    p_learn = sub.add_parser(
        "learn", help="run the non-authoritative host reference for one exact affine hypothesis"
    )
    p_learn.add_argument("dataset")
    p_learn.add_argument("--output")
    p_learn.add_argument("--records-dir")

    p_baseline = sub.add_parser("baseline", help="run the independent fractions.Fraction baseline")
    p_baseline.add_argument("dataset")
    p_baseline.add_argument("--output")

    p_init = sub.add_parser("init-store", help="initialize an empty parent-bound learner overlay store")
    p_init.add_argument("store")
    p_init.add_argument("--seed", default="TOM_seed_genome_2026-09-01.txt")
    p_init.add_argument("--replace", action="store_true")
    p_init.add_argument("--output")

    p_promote = sub.add_parser("promote", help="learn and commit one accepted or rejected session")
    p_promote.add_argument("store")
    p_promote.add_argument("dataset")
    p_promote.add_argument("--expected-parent", required=True)
    p_promote.add_argument("--output")

    p_audit = sub.add_parser("audit", help="audit all immutable learner evidence and commit ancestry")
    p_audit.add_argument("store")
    p_audit.add_argument("--allow-orphans", action="store_true")
    p_audit.add_argument("--output")

    p_reconstruct = sub.add_parser("reconstruct", help="reconstruct the authoritative learner overlay")
    p_reconstruct.add_argument("store")
    p_reconstruct.add_argument("--output")

    args = parser.parse_args(argv)

    if args.command == "verify-handoff":
        record = verify_literal_handoff(args.root, args.handoff)
        _emit(record, args.output)
        return 0 if record["valid"] else 1

    if args.command == "verify-corrective-handoff":
        record = verify_corrective_handoff(args.root, args.corrective)
        _emit(record, args.output)
        return 0 if record["valid"] else 1

    if args.command == "validate-dataset":
        raw, dataset = load_observation_set(args.dataset)
        record = {
            "schema": "TOM-LEARNER-DATASET-VALIDATION-0.1",
            "status": "valid",
            "id": dataset.id,
            "content_hash": dataset.content_hash,
            "observation_count": len(dataset.observations),
            "literal_bytes": len(canonical_bytes(raw)) + 1,
            "base_world_hash": dataset.base_world_hash,
            "base_handoff_hash": dataset.base_handoff_hash,
        }
        _emit(record, args.output)
        return 0

    if args.command in {"split", "learn", "baseline", "promote"}:
        raw, dataset = load_observation_set(args.dataset)

    if args.command == "split":
        from .split import deterministic_split
        _emit(deterministic_split(dataset), args.output)
        return 0

    if args.command == "learn":
        run = learn_observation_set(dataset)
        if args.records_dir:
            directory = Path(args.records_dir)
            directory.mkdir(parents=True, exist_ok=True)
            for index, record in enumerate(run.all_records()):
                schema = str(record.get("schema", "record")).lower().replace("tom-", "").replace("-", "_")
                path = directory / f"{index:04d}_{schema}_{record['content_hash'][7:19]}.json"
                path.write_bytes(canonical_bytes(record) + b"\n")
        _emit(run.summary(), args.output)
        return 0 if run.accepted else 3

    if args.command == "baseline":
        _emit(trusted_affine_learning_baseline(raw), args.output)
        return 0

    if args.command == "init-store":
        target = Path(args.store)
        if target.exists() and args.replace:
            shutil.rmtree(target)
        store = LearnerStore.initialize(target, Path(args.seed).read_bytes())
        record = {
            "schema": "TOM-LEARNER-STORE-INITIALIZATION-0.1",
            "store": str(target),
            "head": store.head(),
            "descriptor": store.descriptor(),
        }
        _emit(record, args.output)
        return 0

    if args.command == "promote":
        store = LearnerStore(args.store)
        run = learn_observation_set(dataset)
        commit = store.commit_learning(run, expected_parent=args.expected_parent)
        record = {
            "schema": "TOM-LEARNER-PROMOTION-RESULT-0.1",
            "accepted": run.accepted,
            "summary": run.summary(),
            "commit": commit,
            "new_head": store.head(),
        }
        _emit(record, args.output)
        return 0

    if args.command == "audit":
        record = LearnerStore(args.store).audit(require_no_orphans=not args.allow_orphans)
        _emit(record, args.output)
        return 0 if record["valid"] else 1

    if args.command == "reconstruct":
        _emit(LearnerStore(args.store).reconstruct(), args.output)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
