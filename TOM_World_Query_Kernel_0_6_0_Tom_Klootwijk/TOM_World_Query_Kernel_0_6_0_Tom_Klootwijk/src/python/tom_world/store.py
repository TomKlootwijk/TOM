"""Persistent content-addressed TOM world store with immutable indexes.

World & Query Kernel 0.2 retains the 0.1 object/commit formats and adds two
content-addressed projections:

* the exact transaction body for every new commit;
* an immutable secondary-index object referenced by each new snapshot.

Only ``HEAD`` is mutable.  Records, blobs, indexes, transactions, snapshots,
and commits are written before ``HEAD`` is atomically replaced.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .canonical import attach_hash, canonical_bytes, digest_bytes, verify_hash
from .indexes import (
    INDEX_SCHEMA,
    build_index_record,
    canonical_index_key,
    ids_for,
    interval_ids,
    validate_index_record,
)
from .records import topological_record_order, validate_record
from .seed import CANONICAL_SEED_SHA256, SeedIdentity, verify_seed_bytes

# The base schemas are kept compatible with 0.1.  New optional fields are
# versioned by the object ``version`` and by the separate 0.2 index schema.
STORE_SCHEMA = "TOM-WORLD-STORE-0.1"
TRANSACTION_SCHEMA = "TOM-WORLD-TRANSACTION-0.1"
SNAPSHOT_SCHEMA = "TOM-WORLD-SNAPSHOT-0.1"
COMMIT_SCHEMA = "TOM-WORLD-COMMIT-0.1"
STORE_VERSION = "0.2.0"


def _digest_name(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"invalid sha256 identifier: {value!r}")
    suffix = value[7:]
    try:
        int(suffix, 16)
    except ValueError as exc:
        raise ValueError(f"invalid sha256 identifier: {value!r}") from exc
    return suffix


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _atomic_write(path: Path, data: bytes, *, fsync: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(data)
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class WorldStore:
    """Directory-backed append-only world objects with a mutable HEAD pointer."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.objects_dir = self.root / "objects"
        self.snapshots_dir = self.root / "snapshots"
        self.commits_dir = self.root / "commits"
        self.blobs_dir = self.root / "blobs"
        self.indexes_dir = self.root / "indexes"
        self.transactions_dir = self.root / "transactions"
        self.head_path = self.root / "HEAD"
        self.descriptor_path = self.root / "store.json"
        self.lock_path = self.root / ".commit.lock"
        # Immutable content-addressed objects may be cached safely within one
        # process.  This matters for query-plan comparison over large snapshots:
        # exhaustive and indexed plans must inspect the same bytes without
        # paying repeated filesystem parse costs.  Audits clear these caches
        # before checking disk integrity.
        self._record_cache: dict[str, dict[str, Any]] = {}
        self._commit_cache: dict[str, dict[str, Any]] = {}
        self._snapshot_cache: dict[str, dict[str, Any]] = {}
        self._index_cache: dict[str, dict[str, Any]] = {}
        self._transaction_cache: dict[str, dict[str, Any]] = {}
        self._blob_cache: dict[str, bytes] = {}

    def clear_caches(self) -> None:
        self._record_cache.clear()
        self._commit_cache.clear()
        self._snapshot_cache.clear()
        self._index_cache.clear()
        self._transaction_cache.clear()
        self._blob_cache.clear()

    @classmethod
    def initialize(cls, root: str | Path, seed_bytes: bytes, *, overwrite: bool = False) -> "WorldStore":
        identity = verify_seed_bytes(seed_bytes)
        store = cls(root)
        if store.root.exists() and any(store.root.iterdir()):
            if not overwrite:
                raise FileExistsError(f"store is not empty: {store.root}")
            shutil.rmtree(store.root)
        for path in (
            store.objects_dir,
            store.snapshots_dir,
            store.commits_dir,
            store.blobs_dir,
            store.indexes_dir,
            store.transactions_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        descriptor = attach_hash({
            "schema": STORE_SCHEMA,
            "version": STORE_VERSION,
            "seed": identity.as_record(),
            "hash_algorithm": "sha256",
            "canonical_json": "UTF-8; sorted keys; separators comma/colon; no NaN",
            "features": [
                "immutable-secondary-indexes",
                "stored-transactions",
                "deterministic-query-plans",
                "checkpoint-replay",
                "commit-ancestry-audit",
            ],
        })
        _atomic_write(store.descriptor_path, canonical_bytes(descriptor) + b"\n")
        _atomic_write(store.root / "seed.bin", seed_bytes)
        return store

    def validate(self) -> SeedIdentity:
        if not self.descriptor_path.is_file():
            raise FileNotFoundError(f"not a TOM world store: {self.root}")
        descriptor = _load_json(self.descriptor_path)
        if descriptor.get("schema") != STORE_SCHEMA or not verify_hash(descriptor):
            raise ValueError("world store descriptor is invalid")
        identity = verify_seed_bytes((self.root / "seed.bin").read_bytes())
        declared = descriptor.get("seed")
        if not isinstance(declared, Mapping) or declared.get("sha256") != identity.sha256:
            raise ValueError("world store seed descriptor mismatch")
        return identity

    @property
    def head(self) -> str | None:
        if not self.head_path.exists():
            return None
        value = self.head_path.read_text(encoding="ascii").strip()
        _digest_name(value)
        return value

    def _object_path(self, ident: str) -> Path:
        return self.objects_dir / (_digest_name(ident) + ".json")

    def _snapshot_path(self, ident: str) -> Path:
        return self.snapshots_dir / (_digest_name(ident) + ".json")

    def _commit_path(self, ident: str) -> Path:
        return self.commits_dir / (_digest_name(ident) + ".json")

    def _blob_path(self, ident: str) -> Path:
        return self.blobs_dir / (_digest_name(ident) + ".bin")

    def _index_path(self, ident: str) -> Path:
        return self.indexes_dir / (_digest_name(ident) + ".json")

    def _transaction_path(self, ident: str) -> Path:
        return self.transactions_dir / (_digest_name(ident) + ".json")

    def _put_hashed_json(self, directory: Path, value: Mapping[str, Any], *, durable: bool = True) -> str:
        if not verify_hash(value):
            raise ValueError("attempted to store a JSON object with an invalid content_hash")
        ident = str(value["content_hash"])
        path = directory / (_digest_name(ident) + ".json")
        data = canonical_bytes(value)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"content address collision for {ident}")
        else:
            _atomic_write(path, data, fsync=durable)
        return ident

    def put_blob(self, data: bytes, *, expected_hash: str | None = None, durable: bool = True) -> str:
        ident = digest_bytes(data)
        if expected_hash is not None and ident != expected_hash:
            raise ValueError(f"blob hash mismatch: {ident} != {expected_hash}")
        path = self._blob_path(ident)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"content address collision for blob {ident}")
        else:
            _atomic_write(path, data, fsync=durable)
        return ident

    def read_blob(self, ident: str) -> bytes:
        cached = self._blob_cache.get(ident)
        if cached is not None:
            return cached
        data = self._blob_path(ident).read_bytes()
        actual = digest_bytes(data)
        if actual != ident:
            raise ValueError(f"stored blob hash mismatch: {ident}")
        self._blob_cache[ident] = data
        return data

    def read_commit(self, ident: str | None = None) -> dict[str, Any]:
        commit_id = ident or self.head
        if commit_id is None:
            raise ValueError("world store has no commit")
        cached = self._commit_cache.get(commit_id)
        if cached is not None:
            return cached
        record = _load_json(self._commit_path(commit_id))
        if record.get("schema") != COMMIT_SCHEMA or not verify_hash(record):
            raise ValueError(f"invalid commit object: {commit_id}")
        if record["content_hash"] != commit_id:
            raise ValueError(f"commit filename/content mismatch: {commit_id}")
        self._commit_cache[commit_id] = record
        return record

    def read_snapshot(self, ident: str) -> dict[str, Any]:
        cached = self._snapshot_cache.get(ident)
        if cached is not None:
            return cached
        snapshot = _load_json(self._snapshot_path(ident))
        if snapshot.get("schema") != SNAPSHOT_SCHEMA or not verify_hash(snapshot):
            raise ValueError(f"invalid snapshot object: {ident}")
        if snapshot["content_hash"] != ident:
            raise ValueError(f"snapshot filename/content mismatch: {ident}")
        records = snapshot.get("records")
        blobs = snapshot.get("blobs")
        if not isinstance(records, Mapping) or not isinstance(blobs, Mapping):
            raise ValueError(f"snapshot maps are invalid: {ident}")
        self._snapshot_cache[ident] = snapshot
        return snapshot

    def read_index(self, ident: str) -> dict[str, Any]:
        cached = self._index_cache.get(ident)
        if cached is not None:
            return cached
        index = _load_json(self._index_path(ident))
        validate_index_record(index, seed_sha256="sha256:" + CANONICAL_SEED_SHA256)
        if index["content_hash"] != ident:
            raise ValueError(f"index filename/content mismatch: {ident}")
        self._index_cache[ident] = index
        return index

    def read_transaction(self, ident: str) -> dict[str, Any]:
        cached = self._transaction_cache.get(ident)
        if cached is not None:
            return cached
        transaction = _load_json(self._transaction_path(ident))
        if transaction.get("schema") != TRANSACTION_SCHEMA or not verify_hash(transaction):
            raise ValueError(f"invalid transaction object: {ident}")
        if transaction["content_hash"] != ident:
            raise ValueError(f"transaction filename/content mismatch: {ident}")
        self._transaction_cache[ident] = transaction
        return transaction

    def snapshot_for_commit(self, commit: str | None = None) -> dict[str, Any]:
        commit_record = self.read_commit(commit)
        return self.read_snapshot(str(commit_record["snapshot_hash"]))

    def is_ancestor(self, ancestor: str, descendant: str | None = None) -> bool:
        """Return whether ``ancestor`` is in the parent chain of ``descendant``."""

        _digest_name(ancestor)
        current = descendant or self.head
        seen: set[str] = set()
        while current is not None:
            if current == ancestor:
                return True
            if current in seen:
                raise ValueError("commit ancestry cycle")
            seen.add(current)
            record = self.read_commit(current)
            parent = record.get("parent")
            current = str(parent) if isinstance(parent, str) else None
        return False

    def index_for_commit(self, commit: str | None = None, *, required: bool = False) -> dict[str, Any] | None:
        snapshot = self.snapshot_for_commit(commit)
        index_id = snapshot.get("indexes_hash")
        if index_id is None:
            if required:
                raise ValueError("snapshot has no immutable 0.2 secondary index")
            return None
        index = self.read_index(str(index_id))
        validate_index_record(
            index,
            records={str(key): str(value) for key, value in snapshot["records"].items()},
            seed_sha256=str(snapshot["seed_sha256"]),
        )
        return index

    def _load_record_from_map(self, record_id: str, object_id: str) -> dict[str, Any]:
        record = self._record_cache.get(object_id)
        if record is None:
            record = _load_json(self._object_path(object_id))
            validate_record(record)
            if record["content_hash"] != object_id:
                raise ValueError(f"record filename/content mismatch: {record_id}")
            self._record_cache[object_id] = record
        if record["id"] != record_id:
            raise ValueError(f"record index/object mismatch: {record_id}")
        return record

    def read_record(self, record_id: str, *, commit: str | None = None) -> dict[str, Any]:
        snapshot = self.snapshot_for_commit(commit)
        records = snapshot["records"]
        if record_id not in records:
            raise KeyError(record_id)
        return self._load_record_from_map(record_id, str(records[record_id]))

    def list_record_ids(self, *, commit: str | None = None, record_type: str | None = None) -> list[str]:
        snapshot = self.snapshot_for_commit(commit)
        if record_type is None:
            return sorted(str(key) for key in snapshot["records"])
        index = self.index_for_commit(commit)
        if index is not None:
            return ids_for(index, "by_type", record_type)
        result: list[str] = []
        for record_id in sorted(snapshot["records"]):
            record = self._load_record_from_map(str(record_id), str(snapshot["records"][record_id]))
            if record["record_type"] == record_type:
                result.append(str(record_id))
        return result

    def list_records(self, *, commit: str | None = None, record_type: str | None = None) -> list[dict[str, Any]]:
        snapshot = self.snapshot_for_commit(commit)
        result: list[dict[str, Any]] = []
        for record_id in self.list_record_ids(commit=commit, record_type=record_type):
            result.append(self._load_record_from_map(record_id, str(snapshot["records"][record_id])))
        return result

    def indexed_record_ids(self, name: str, key: Any, *, commit: str | None = None) -> list[str]:
        index = self.index_for_commit(commit, required=True)
        assert index is not None
        if name == "by_generative_address":
            key, _ = canonical_index_key(key)
        elif name == "by_topology_sheet":
            if isinstance(key, bool) or not isinstance(key, int) or key < 0:
                raise ValueError("topology sheet key must be a nonnegative integer")
            key = str(key)
        else:
            key = str(key)
        return ids_for(index, name, key)

    def interval_record_ids(
        self,
        start: int,
        end: int,
        *,
        commit: str | None = None,
        record_type: str | None = None,
    ) -> list[str]:
        index = self.index_for_commit(commit, required=True)
        assert index is not None
        return interval_ids(index, start, end, record_type=record_type)

    def verify_record(self, record_id: str, *, commit: str | None = None) -> dict[str, Any]:
        snapshot = self.snapshot_for_commit(commit)
        index = snapshot["records"]
        if record_id not in index:
            return {"id": record_id, "valid": False, "reason": "not present in snapshot"}
        object_id = str(index[record_id])
        path = self._object_path(object_id)
        try:
            record = self._load_record_from_map(record_id, object_id)
        except Exception as exc:
            return {"id": record_id, "valid": False, "reason": str(exc), "object_hash": object_id}
        missing = [dep for dep in record["dependencies"] if dep not in index]
        return {
            "id": record_id,
            "record_type": record["record_type"],
            "object_hash": object_id,
            "file_present": path.is_file(),
            "content_hash_valid": verify_hash(record),
            "dependencies_resolved": not missing,
            "missing_dependencies": missing,
            "valid": path.is_file() and verify_hash(record) and not missing,
        }

    def compute_indexes(self, *, commit: str | None = None) -> dict[str, Any]:
        snapshot = self.snapshot_for_commit(commit)
        record_map = {str(key): str(value) for key, value in snapshot["records"].items()}
        return build_index_record(
            record_map,
            self._load_record_from_map,
            seed_sha256=str(snapshot["seed_sha256"]),
        )

    def rebuild_indexes(self, *, commit: str | None = None, write: bool = True) -> dict[str, Any]:
        """Recreate the exact index bytes named by an immutable snapshot."""

        commit_record = self.read_commit(commit)
        snapshot = self.read_snapshot(str(commit_record["snapshot_hash"]))
        expected = snapshot.get("indexes_hash")
        if expected is None:
            raise ValueError("cannot rebuild indexes for a legacy snapshot without indexes_hash")
        rebuilt = self.compute_indexes(commit=commit_record["content_hash"])
        if rebuilt["content_hash"] != expected:
            raise ValueError(
                f"rebuilt index hash mismatch: {rebuilt['content_hash']} != {expected}"
            )
        if write:
            self._put_hashed_json(self.indexes_dir, rebuilt)
        return attach_hash({
            "schema": "TOM-INDEX-REBUILD-CERTIFICATE-0.2",
            "commit": commit_record["content_hash"],
            "snapshot_hash": snapshot["content_hash"],
            "indexes_hash": expected,
            "record_count": rebuilt["record_count"],
            "written": write,
            "byte_equal_to_declared_hash": True,
        })

    @contextmanager
    def _commit_lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("another world transaction holds the commit lock") from exc
        try:
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            yield
        finally:
            self.lock_path.unlink(missing_ok=True)

    def commit_transaction(
        self,
        transaction: Mapping[str, Any],
        *,
        source_dir: str | Path | None = None,
        update_head: bool = True,
    ) -> dict[str, Any]:
        """Validate and atomically commit a content-addressed transaction."""

        identity = self.validate()
        source_root = Path(source_dir) if source_dir is not None else Path.cwd()
        if transaction.get("schema") != TRANSACTION_SCHEMA:
            raise ValueError(f"transaction schema must be {TRANSACTION_SCHEMA}")
        if not verify_hash(transaction):
            raise ValueError("transaction content hash mismatch")
        if transaction.get("seed_sha256") != "sha256:" + identity.sha256:
            raise ValueError("transaction is not bound to the canonical store seed")
        records = transaction.get("records")
        blobs = transaction.get("blobs", [])
        if not isinstance(records, list) or not isinstance(blobs, list):
            raise ValueError("transaction records and blobs must be arrays")

        with self._commit_lock():
            current_head = self.head
            declared_base = transaction.get("base_commit")
            if declared_base != current_head:
                raise ValueError(f"transaction base_commit {declared_base!r} does not match HEAD {current_head!r}")
            if current_head is None:
                existing_records: dict[str, str] = {}
                existing_blobs: dict[str, str] = {}
                expected_sequence = 0
            else:
                current_commit = self.read_commit(current_head)
                current_snapshot = self.read_snapshot(str(current_commit["snapshot_hash"]))
                existing_records = {str(key): str(value) for key, value in current_snapshot["records"].items()}
                existing_blobs = {str(key): str(value) for key, value in current_snapshot["blobs"].items()}
                expected_sequence = int(current_commit["sequence"]) + 1
            sequence = transaction.get("sequence")
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence != expected_sequence:
                raise ValueError(f"transaction sequence must be {expected_sequence}")

            order = topological_record_order(records, existing_ids=set(existing_records))
            staged_by_id = {str(record["id"]): record for record in records}

            blob_index = dict(existing_blobs)
            staged_blob_data: list[tuple[str, bytes, str]] = []
            seen_blob_ids: set[str] = set()
            for blob in blobs:
                if not isinstance(blob, Mapping):
                    raise ValueError("transaction blob entry must be an object")
                blob_id = blob.get("id")
                path_value = blob.get("path")
                expected_hash = blob.get("sha256")
                if not isinstance(blob_id, str) or not blob_id:
                    raise ValueError("blob id must be a nonempty string")
                if blob_id in seen_blob_ids:
                    raise ValueError(f"duplicate staged blob id: {blob_id}")
                seen_blob_ids.add(blob_id)
                if not isinstance(path_value, str) or not path_value:
                    raise ValueError(f"blob {blob_id} requires a path")
                if not isinstance(expected_hash, str):
                    raise ValueError(f"blob {blob_id} requires a sha256 identifier")
                data = (source_root / path_value).read_bytes()
                actual = digest_bytes(data)
                if actual != expected_hash:
                    raise ValueError(f"blob {blob_id} hash mismatch: {actual} != {expected_hash}")
                staged_blob_data.append((str(blob_id), data, actual))
                blob_index[str(blob_id)] = actual

            prospective_ids = set(existing_records).union(staged_by_id)
            prospective_blob_ids = set(blob_index)
            for ident in order:
                record = staged_by_id[ident]
                validate_record(record)
                payload = record["payload"]
                if record["record_type"] == "instance":
                    blob_id = payload["program_blob_id"]
                    if blob_id not in prospective_blob_ids:
                        raise ValueError(f"instance {ident} references unknown program blob {blob_id}")
                for field in ("instance_id", "event_spec_id", "relation_id", "transition_id"):
                    reference = payload.get(field)
                    if isinstance(reference, str) and reference not in prospective_ids:
                        raise ValueError(f"record {ident} references unknown {field} {reference}")
                for field in ("support_ids", "compatibility_ids"):
                    for reference in payload.get(field, []):
                        if reference not in prospective_ids:
                            raise ValueError(f"record {ident} references unknown {field} item {reference}")

            # Immutable content is written first.  Large synthetic transactions
            # avoid one fsync per object; the transaction/index/snapshot/commit
            # and final HEAD publication remain durably synchronized.
            bulk = len(records) + len(blobs) >= 1000
            for _, data, actual in staged_blob_data:
                self.put_blob(data, expected_hash=actual, durable=not bulk)
            record_index = dict(existing_records)
            for ident in order:
                record = staged_by_id[ident]
                object_id = self._put_hashed_json(self.objects_dir, record, durable=not bulk)
                self._record_cache[object_id] = dict(record)
                record_index[ident] = object_id

            index_record = build_index_record(
                record_index,
                self._load_record_from_map,
                seed_sha256="sha256:" + CANONICAL_SEED_SHA256,
            )
            index_id = self._put_hashed_json(self.indexes_dir, index_record)
            snapshot = attach_hash({
                "schema": SNAPSHOT_SCHEMA,
                "version": STORE_VERSION,
                "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
                "records": {key: record_index[key] for key in sorted(record_index)},
                "blobs": {key: blob_index[key] for key in sorted(blob_index)},
                "indexes_hash": index_id,
            })
            snapshot_id = self._put_hashed_json(self.snapshots_dir, snapshot)
            transaction_id = self._put_hashed_json(self.transactions_dir, transaction)
            commit = attach_hash({
                "schema": COMMIT_SCHEMA,
                "version": STORE_VERSION,
                "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
                "sequence": sequence,
                "parent": current_head,
                "transaction_hash": transaction_id,
                "snapshot_hash": snapshot_id,
                "indexes_hash": index_id,
                "message": str(transaction.get("message", "")),
                "provenance": dict(transaction.get("provenance", {})),
            })
            commit_id = self._put_hashed_json(self.commits_dir, commit)
            if update_head:
                _atomic_write(self.head_path, (commit_id + "\n").encode("ascii"))
            return commit

    def commit_transaction_file(self, path: str | Path, *, update_head: bool = True) -> dict[str, Any]:
        source = Path(path)
        transaction = _load_json(source)
        return self.commit_transaction(transaction, source_dir=source.parent, update_head=update_head)
