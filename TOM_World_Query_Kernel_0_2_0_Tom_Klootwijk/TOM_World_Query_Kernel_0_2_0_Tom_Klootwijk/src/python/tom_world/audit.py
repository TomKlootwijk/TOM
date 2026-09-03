"""Deterministic corruption and commit-ancestry audit for TOM world stores."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from tomagi.format import loads as load_tomagi_program

from .canonical import attach_hash, canonical_bytes
from .indexes import validate_index_record
from .records import validate_record, validate_record_dependency_graph
from .store import (
    COMMIT_SCHEMA,
    SNAPSHOT_SCHEMA,
    TRANSACTION_SCHEMA,
    WorldStore,
    _validate_record_relationships,
)

AUDIT_SCHEMA = "TOM-WORLD-AUDIT-CERTIFICATE-0.2"


def _hash_ids(directory: Path, suffix: str) -> set[str]:
    if not directory.exists():
        return set()
    result: set[str] = set()
    for path in directory.glob("*" + suffix):
        stem = path.name[:-len(suffix)] if suffix else path.name
        if len(stem) == 64:
            try:
                int(stem, 16)
            except ValueError:
                continue
            result.add("sha256:" + stem)
    return result


def audit_store(
    store: WorldStore,
    *,
    commit: str | None = None,
    require_no_orphans: bool = False,
    strict: bool = False,
    max_event_replay_steps: int = 100_000,
) -> dict[str, Any]:
    """Audit a target commit, all ancestors, and all reachable immutable bytes.

    The certificate is deterministic: it contains no duration, hostname, PID,
    or absolute path. Repeated audits of the same bytes with the same arguments
    produce the same hash.
    """

    if (
        isinstance(max_event_replay_steps, bool)
        or not isinstance(max_event_replay_steps, int)
        or max_event_replay_steps < 0
    ):
        raise ValueError("max_event_replay_steps must be a nonnegative integer")

    # An audit is a disk-integrity operation and must not inherit cached parses
    # from prior queries in the same process.
    store.clear_caches()
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []

    def error(kind: str, ident: str, message: str) -> None:
        errors.append({"kind": kind, "id": ident, "message": message})

    def warning(kind: str, ident: str, message: str) -> None:
        warnings.append({"kind": kind, "id": ident, "message": message})

    try:
        identity = store.validate()
        checks.append({"name": "store_descriptor_and_seed", "valid": True, "seed_sha256": identity.sha256})
    except Exception as exc:
        identity = None
        error("store", "descriptor", f"{type(exc).__name__}: {exc}")
        checks.append({"name": "store_descriptor_and_seed", "valid": False})

    try:
        head = store.head
    except Exception as exc:
        head = None
        error("head", "HEAD", f"{type(exc).__name__}: {exc}")
    target = commit or head
    if target is None:
        error("commit", "HEAD", "store has no target commit")
        certificate = attach_hash({
            "schema": AUDIT_SCHEMA,
            "version": "0.2.0",
            "target_commit": None,
            "head": head,
            "valid": False,
            "checks": checks,
            "counts": {},
            "ancestry": [],
            "errors": errors,
            "warnings": warnings,
            "orphans": {},
            "require_no_orphans": require_no_orphans,
            "max_event_replay_steps": max_event_replay_steps,
        })
        if strict:
            raise ValueError("world audit failed: store has no target commit")
        return certificate

    reachable_commits: set[str] = set()
    reachable_snapshots: set[str] = set()
    reachable_indexes: set[str] = set()
    reachable_transactions: set[str] = set()
    reachable_objects: set[str] = set()
    reachable_blobs: set[str] = set()
    verified_objects: set[str] = set()
    verified_blobs: set[str] = set()
    verified_checkpoint_objects: set[str] = set()
    verified_event_certificates: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    ancestry: list[dict[str, Any]] = []
    type_counts: Counter[str] = Counter()
    record_references = 0
    blob_references = 0

    current: str | None = target
    expected_sequence: int | None = None
    seen: set[str] = set()
    while current is not None:
        if current in seen:
            error("commit", current, "commit ancestry cycle")
            break
        seen.add(current)
        reachable_commits.add(current)
        try:
            commit_record = store.read_commit(current)
        except Exception as exc:
            error("commit", current, f"{type(exc).__name__}: {exc}")
            break
        if commit_record.get("schema") != COMMIT_SCHEMA:
            error("commit", current, "commit schema mismatch")
        sequence = commit_record.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            error("commit", current, "commit sequence is invalid")
            break
        if expected_sequence is not None and sequence != expected_sequence:
            error("commit", current, f"sequence discontinuity: {sequence} != {expected_sequence}")
        expected_sequence = sequence - 1
        if identity is not None and commit_record.get("seed_sha256") != "sha256:" + identity.sha256:
            error("commit", current, "commit seed binding mismatch")

        transaction_hash = str(commit_record.get("transaction_hash"))
        transaction: dict[str, Any] | None = None
        transaction_valid = False
        try:
            transaction_path = store._transaction_path(transaction_hash)
        except Exception as exc:
            transaction_path = None
            error("transaction", transaction_hash, f"invalid transaction identifier: {type(exc).__name__}: {exc}")
        if transaction_path is not None and transaction_path.is_file():
            reachable_transactions.add(transaction_hash)
            try:
                transaction = store.read_transaction(transaction_hash)
                transaction_valid = (
                    transaction.get("schema") == TRANSACTION_SCHEMA
                    and transaction.get("base_commit") == commit_record.get("parent")
                    and transaction.get("sequence") == sequence
                    and transaction.get("seed_sha256") == commit_record.get("seed_sha256")
                    and isinstance(transaction.get("message", ""), str)
                    and transaction.get("message", "") == commit_record.get("message")
                    and isinstance(transaction.get("provenance", {}), dict)
                    and transaction.get("provenance", {}) == commit_record.get("provenance")
                )
                if not transaction_valid:
                    error("transaction", transaction_hash, "transaction/commit metadata mismatch")
            except Exception as exc:
                error("transaction", transaction_hash, f"{type(exc).__name__}: {exc}")
        elif transaction_path is not None:
            if commit_record.get("version") == "0.1.0":
                warning("transaction", transaction_hash, "legacy 0.1 commit has no stored transaction body")
            else:
                error("transaction", transaction_hash, "stored transaction body is missing")

        snapshot_hash = str(commit_record.get("snapshot_hash"))
        reachable_snapshots.add(snapshot_hash)
        try:
            snapshot = store.read_snapshot(snapshot_hash)
        except Exception as exc:
            error("snapshot", snapshot_hash, f"{type(exc).__name__}: {exc}")
            break
        if snapshot.get("schema") != SNAPSHOT_SCHEMA:
            error("snapshot", snapshot_hash, "snapshot schema mismatch")
        if identity is not None and snapshot.get("seed_sha256") != "sha256:" + identity.sha256:
            error("snapshot", snapshot_hash, "snapshot seed binding mismatch")

        # A valid hash for each object is not enough to establish lineage.  Replay
        # the stored transaction as a map update over its parent's snapshot and
        # require that the result is exactly the snapshot named by this commit.
        # This detects self-consistent but false transaction/snapshot pairings.
        if transaction is not None and transaction_valid:
            expected_records: dict[str, str] = {}
            expected_blobs: dict[str, str] = {}
            parent = commit_record.get("parent")
            try:
                if isinstance(parent, str):
                    parent_commit = store.read_commit(parent)
                    parent_snapshot = store.read_snapshot(str(parent_commit["snapshot_hash"]))
                    expected_records = {
                        str(key): str(value) for key, value in parent_snapshot["records"].items()
                    }
                    expected_blobs = {
                        str(key): str(value) for key, value in parent_snapshot["blobs"].items()
                    }

                staged_records = transaction.get("records")
                staged_blobs = transaction.get("blobs", [])
                if not isinstance(staged_records, list) or not isinstance(staged_blobs, list):
                    raise ValueError("transaction records and blobs must be arrays")

                seen_record_ids: set[str] = set()
                for record in staged_records:
                    if not isinstance(record, dict):
                        raise ValueError("transaction record must be an object")
                    validate_record(record)
                    record_id = str(record["id"])
                    if record_id in seen_record_ids:
                        raise ValueError(f"duplicate staged record id: {record_id}")
                    seen_record_ids.add(record_id)
                    expected_records[record_id] = str(record["content_hash"])

                seen_blob_ids: set[str] = set()
                for blob in staged_blobs:
                    if not isinstance(blob, dict):
                        raise ValueError("transaction blob entry must be an object")
                    blob_id = blob.get("id")
                    blob_hash = blob.get("sha256")
                    if not isinstance(blob_id, str) or not blob_id:
                        raise ValueError("transaction blob id must be a nonempty string")
                    if blob_id in seen_blob_ids:
                        raise ValueError(f"duplicate staged blob id: {blob_id}")
                    seen_blob_ids.add(blob_id)
                    # _blob_path also validates the sha256 identifier syntax.
                    store._blob_path(str(blob_hash))
                    expected_blobs[blob_id] = str(blob_hash)

                actual_records = {
                    str(key): str(value) for key, value in snapshot["records"].items()
                }
                actual_blobs = {
                    str(key): str(value) for key, value in snapshot["blobs"].items()
                }
                if expected_records != actual_records or expected_blobs != actual_blobs:
                    transaction_valid = False
                    error(
                        "transaction",
                        transaction_hash,
                        "replaying transaction over parent does not reproduce snapshot maps",
                    )
            except Exception as exc:
                transaction_valid = False
                error("transaction", transaction_hash, f"lineage replay failed: {type(exc).__name__}: {exc}")

        index_hash = snapshot.get("indexes_hash")
        index_valid = False
        index_rebuilt_equal = False
        if isinstance(index_hash, str):
            reachable_indexes.add(index_hash)
            if (
                commit_record.get("version") == "0.1.0"
                and commit_record.get("indexes_hash") not in (None, index_hash)
            ) or (
                commit_record.get("version") != "0.1.0"
                and commit_record.get("indexes_hash") != index_hash
            ):
                error("index", index_hash, "commit/snapshot index hash mismatch")
            try:
                index = store.read_index(index_hash)
                validate_index_record(
                    index,
                    records={str(key): str(value) for key, value in snapshot["records"].items()},
                    seed_sha256=str(snapshot["seed_sha256"]),
                )
                index_valid = True
                rebuilt = store.compute_indexes(commit=current)
                index_rebuilt_equal = canonical_bytes(rebuilt) == canonical_bytes(index)
                if not index_rebuilt_equal:
                    error("index", index_hash, "rebuilt index bytes differ from stored index")
            except Exception as exc:
                error("index", index_hash, f"{type(exc).__name__}: {exc}")
        else:
            if commit_record.get("version") == "0.1.0":
                warning("index", snapshot_hash, "legacy snapshot has no immutable secondary index")
            else:
                error("index", snapshot_hash, "0.2 snapshot has no immutable secondary index")

        snapshot_record_errors = 0
        records = snapshot["records"]
        snapshot_records: dict[str, Mapping[str, Any]] = {}
        for record_id in sorted(records):
            record_references += 1
            object_hash = str(records[record_id])
            reachable_objects.add(object_hash)
            try:
                record = store._load_record_from_map(str(record_id), object_hash)
                type_counts[str(record["record_type"])] += 1
                missing = [dependency for dependency in record["dependencies"] if dependency not in records]
                if missing:
                    snapshot_record_errors += 1
                    error("record", str(record_id), "unresolved dependencies: " + ", ".join(sorted(missing)))
                snapshot_records[str(record_id)] = record
                verified_objects.add(object_hash)
            except Exception as exc:
                snapshot_record_errors += 1
                error("record", str(record_id), f"{type(exc).__name__}: {exc}")

        snapshot_blob_errors = 0
        blobs = snapshot["blobs"]
        for blob_id in sorted(blobs):
            blob_references += 1
            blob_hash = str(blobs[blob_id])
            reachable_blobs.add(blob_hash)
            if blob_hash in verified_blobs:
                continue
            try:
                store.read_blob(blob_hash)
                verified_blobs.add(blob_hash)
            except Exception as exc:
                snapshot_blob_errors += 1
                error("blob", str(blob_id), f"{type(exc).__name__}: {exc}")

        # Reapply the same whole-snapshot invariants enforced at publication.
        # Individually valid hashes and resolved dependency names do not rule
        # out cycles, wrong reference types, invalid bytecode, or forged
        # executable checkpoint/event claims.
        if len(snapshot_records) == len(records):
            try:
                validate_record_dependency_graph(snapshot_records)
                _validate_record_relationships(snapshot_records)
            except Exception as exc:
                snapshot_record_errors += 1
                error("record", snapshot_hash, f"record graph validation failed: {type(exc).__name__}: {exc}")

            program_cache: dict[str, Any] = {}
            for record_id in sorted(snapshot_records):
                record = snapshot_records[record_id]
                if record["record_type"] != "instance":
                    continue
                try:
                    payload = record["payload"]
                    blob_id = str(payload["program_blob_id"])
                    if blob_id not in blobs:
                        raise ValueError(f"unknown program blob {blob_id}")
                    blob_hash = str(blobs[blob_id])
                    if blob_hash not in program_cache:
                        program = load_tomagi_program(store.read_blob(blob_hash))
                        program_cache[blob_hash] = program
                    program = program_cache[blob_hash]
                    initial_state = payload.get("initial_state", {})
                    selected_cell = initial_state.get("cell", program.entry)
                    if (int(selected_cell) & 0xFFFFFFFF) >= len(program.cells):
                        raise ValueError("initial_state.cell is outside its program cell table")
                except Exception as exc:
                    snapshot_record_errors += 1
                    error("record", record_id, f"program validation failed: {type(exc).__name__}: {exc}")

            query_engine = None
            for record_id in sorted(snapshot_records):
                record = snapshot_records[record_id]
                record_type = str(record["record_type"])
                object_hash = str(record["content_hash"])
                if record_type == "checkpoint":
                    try:
                        source_commit = str(record["payload"]["source_commit"])
                        if not store.is_ancestor(source_commit, current):
                            raise ValueError("source commit is not in snapshot commit ancestry")
                        if object_hash not in verified_checkpoint_objects:
                            from .query import verify_checkpoint_record

                            verify_checkpoint_record(store, record)
                            verified_checkpoint_objects.add(object_hash)
                    except Exception as exc:
                        snapshot_record_errors += 1
                        error(
                            "record",
                            record_id,
                            f"checkpoint semantic verification failed: {type(exc).__name__}: {exc}",
                        )
                elif record_type in {"event", "lineage"}:
                    try:
                        certificate = record["payload"].get("certificate")
                        if not isinstance(certificate, Mapping):
                            raise ValueError("embedded event certificate is missing")
                        source_commit = certificate.get("source_commit")
                        if not isinstance(source_commit, str) or not store.is_ancestor(source_commit, current):
                            raise ValueError("certificate source is not in snapshot commit ancestry")
                        certificate_hash = str(certificate.get("content_hash"))
                        expected_pair = verified_event_certificates.get(certificate_hash)
                        if expected_pair is None:
                            from .query import QueryEngine

                            query_engine = query_engine or QueryEngine(
                                store,
                                commit=current,
                                max_query_steps=max_event_replay_steps,
                                use_checkpoints=False,
                            )
                            reconstruction = query_engine.reconstruct(certificate)
                            if not reconstruction["byte_equal"]:
                                raise ValueError("certificate does not reconstruct byte-for-byte")
                            expected_pair = query_engine.event_records(certificate)
                            verified_event_certificates[certificate_hash] = expected_pair
                        expected = expected_pair[0] if record_type == "event" else expected_pair[1]
                        if canonical_bytes(record) != canonical_bytes(expected):
                            raise ValueError("record is not the canonical certificate-derived record")
                    except Exception as exc:
                        snapshot_record_errors += 1
                        error(
                            "record",
                            record_id,
                            f"event semantic verification failed: {type(exc).__name__}: {exc}",
                        )

        parent = commit_record.get("parent")
        if sequence == 0 and parent is not None:
            error("commit", current, "root sequence zero must have null parent")
        if sequence > 0 and not isinstance(parent, str):
            error("commit", current, "non-root commit must name a parent")
        ancestry.append({
            "commit": current,
            "sequence": sequence,
            "parent": parent,
            "transaction_hash": transaction_hash,
            "transaction_valid": transaction_valid,
            "snapshot_hash": snapshot_hash,
            "record_count": len(records),
            "blob_count": len(blobs),
            "record_errors": snapshot_record_errors,
            "blob_errors": snapshot_blob_errors,
            "indexes_hash": index_hash,
            "index_valid": index_valid,
            "index_rebuilt_byte_equal": index_rebuilt_equal,
        })
        current = str(parent) if isinstance(parent, str) else None

    if ancestry and ancestry[-1]["sequence"] != 0:
        error("commit", ancestry[-1]["commit"], "ancestry did not terminate at sequence zero")
    if commit is None and target != head:
        error("head", "HEAD", "audit target does not equal current HEAD")

    disk_sets = {
        "commits": _hash_ids(store.commits_dir, ".json"),
        "snapshots": _hash_ids(store.snapshots_dir, ".json"),
        "indexes": _hash_ids(store.indexes_dir, ".json"),
        "transactions": _hash_ids(store.transactions_dir, ".json"),
        "objects": _hash_ids(store.objects_dir, ".json"),
        "blobs": _hash_ids(store.blobs_dir, ".bin"),
    }
    reachable_sets = {
        "commits": reachable_commits,
        "snapshots": reachable_snapshots,
        "indexes": reachable_indexes,
        "transactions": reachable_transactions,
        "objects": reachable_objects,
        "blobs": reachable_blobs,
    }
    orphan_record: dict[str, Any] = {}
    for kind in sorted(disk_sets):
        values = sorted(disk_sets[kind] - reachable_sets[kind])
        orphan_record[kind] = {"count": len(values), "sample": values[:32]}
        if require_no_orphans and values:
            error("orphan", kind, f"{len(values)} unreachable immutable objects")

    valid = not errors
    checks.extend([
        {"name": "commit_ancestry", "valid": bool(ancestry) and ancestry[-1]["sequence"] == 0},
        {"name": "reachable_records", "valid": not any(item["kind"] == "record" for item in errors)},
        {"name": "reachable_blobs", "valid": not any(item["kind"] == "blob" for item in errors)},
        {"name": "immutable_indexes", "valid": not any(item["kind"] == "index" for item in errors)},
        {"name": "stored_transactions", "valid": not any(item["kind"] == "transaction" for item in errors)},
    ])
    certificate = attach_hash({
        "schema": AUDIT_SCHEMA,
        "version": "0.2.0",
        "target_commit": target,
        "head": head,
        "valid": valid,
        "checks": checks,
        "counts": {
            "commits": len(reachable_commits),
            "snapshots": len(reachable_snapshots),
            "indexes": len(reachable_indexes),
            "transactions": len(reachable_transactions),
            "unique_objects": len(verified_objects),
            "record_references": record_references,
            "unique_blobs": len(verified_blobs),
            "blob_references": blob_references,
            "record_types_across_snapshots": {key: type_counts[key] for key in sorted(type_counts)},
        },
        "ancestry": ancestry,
        "errors": errors,
        "warnings": warnings,
        "orphans": orphan_record,
        "require_no_orphans": require_no_orphans,
        "max_event_replay_steps": max_event_replay_steps,
    })
    if strict and not valid:
        summary = "; ".join(f"{item['kind']}:{item['id']}:{item['message']}" for item in errors[:8])
        raise ValueError("world audit failed: " + summary)
    return certificate
