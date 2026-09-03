from __future__ import annotations

import argparse
import json
from pathlib import Path

from .oracle import evaluate_all
from tomagi.immutable_store import ImmutablePublicationStore, validate_plan


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tom-learner06")
    sub = parser.add_subparsers(dest="command", required=True)

    p_oracle = sub.add_parser("oracle", help="run the independent family-registry oracle")
    p_oracle.add_argument("registry")
    p_oracle.add_argument("prior_authority")
    p_oracle.add_argument("datasets", nargs="+")

    p_validate = sub.add_parser("validate-plan")
    p_validate.add_argument("source")

    p_apply = sub.add_parser("apply-plan")
    p_apply.add_argument("source")
    p_apply.add_argument("seed")
    p_apply.add_argument("store")

    p_audit = sub.add_parser("audit-store")
    p_audit.add_argument("source")
    p_audit.add_argument("store")

    args = parser.parse_args(argv)
    if args.command == "oracle":
        result = evaluate_all([load(path) for path in args.datasets], load(args.registry), load(args.prior_authority))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    source = load(args.source)
    if source.get("schema") == "TOMAGI-FORMAL-RESULT-1.0":
        plan = source["value"]["publication_plan"]
    else:
        plan = source.get("publication_plan", source)
    checked = validate_plan(plan)
    if args.command == "validate-plan":
        print(json.dumps({"valid": True, "publications": len(checked["publications"]), "terminal_head": checked["terminal_head"]}, indent=2, sort_keys=True))
        return 0
    if args.command == "apply-plan":
        store = ImmutablePublicationStore.apply_plan(args.store, Path(args.seed).read_bytes(), checked)
        audit = store.audit_plan(checked)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["valid"] else 1
    audit = ImmutablePublicationStore(args.store).audit_plan(checked)
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
