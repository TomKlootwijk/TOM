from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from tomagi.immutable_store import ImmutablePublicationStore, validate_plan


def _load(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tom-learner052",
        description="Inspect and apply TOM Learner 0.1 formal promotion plans",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate-plan", help="validate a materialized formal result or plan")
    p_validate.add_argument("source")

    p_apply = sub.add_parser("apply-plan", help="apply a validated plan to an absent/empty store")
    p_apply.add_argument("source")
    p_apply.add_argument("seed")
    p_apply.add_argument("store")
    p_apply.add_argument("--replace", action="store_true")

    p_audit = sub.add_parser("audit-store", help="audit an applied store against its plan")
    p_audit.add_argument("source")
    p_audit.add_argument("store")
    p_audit.add_argument("--allow-extra-records", action="store_true")

    args = parser.parse_args(argv)
    source = _load(args.source)
    if source.get("schema") == "TOMAGI-FORMAL-RESULT-1.0":
        plan = source["value"]["publication_plan"]
    elif source.get("schema") == "TOM-LEARNER-PROMOTION-AUTHORITY-RESULT-0.5.2":
        plan = source["publication_plan"]
    else:
        plan = source
    checked = validate_plan(plan)

    if args.command == "validate-plan":
        print(json.dumps({
            "valid": True,
            "publication_count": len(checked["publications"]),
            "terminal_head": checked["terminal_head"],
            "plan_content_hash": checked["content_hash"],
        }, indent=2, sort_keys=True))
        return 0

    if args.command == "apply-plan":
        target = Path(args.store)
        if args.replace:
            shutil.rmtree(target, ignore_errors=True)
        seed = Path(args.seed).read_bytes()
        store = ImmutablePublicationStore.apply_plan(target, seed, checked)
        audit = store.audit_plan(checked, require_no_extra_records=True)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["valid"] else 1

    if args.command == "audit-store":
        audit = ImmutablePublicationStore(args.store).audit_plan(
            checked, require_no_extra_records=not args.allow_extra_records
        )
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["valid"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
