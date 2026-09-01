"""Persistent content-addressed TOM world store with atomic commits."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .canonical import attach_hash, canonical_bytes, digest_bytes, verify_hash
from .records import topological_record_order, validate_record
from .seed import CANONICAL_SEED_SHA256, SeedIdentity, verify_seed_bytes

STORE_SCHEMA = "TOM-WORLD-STORE-0.1"
TRANSACTION_SCHEMA = "TOM-WORLD-TRANSACTION-0.1"
SNAPSHOT_SCHEMA = "TOM-WORLD-SNAPSHOT-0.1"
COMMIT_SCHEMA = "TOM-WORLD-COMMIT-0.1"


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


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class WorldStore:
    """Directory-backed append-only world objects with a mutable HEAD pointer.

    Objects, snapshots, commits, and blobs are immutable and addressed by SHA-256.
    Only ``HEAD`` changes.  A transaction writes every immutable object first and
    atomically replaces ``HEAD`` last.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.objects_dir = self.root / "objects"
        self.snapshots_dir = self.root / "snapshots"
        self.commits_dir = self.root / "commits"
        self.blobs_dir = self.root / "blobs"
        self.head_path = self.root / "HEAD"
        self.descriptor_path = self.root / "store.json"
        self.lock_path = self.root / ".commit.lock"

    @classmethod
    def initialize(cls, root: str | Path, seed_bytes: bytes, *, overwrite: bool = False) -> "WorldStore":
        identity = verify_seed_bytes(seed_bytes)
        store = cls(root)
        if store.root.exists() and any(store.root.iterdir()):
            if not overwrite:
                raise FileExistsError(f"store is not empty: {store.root}")
            shutil.rmtree(store.root)
        for path in (store.objects_dir, store.snapshots_dir, store.commits_dir, store.blobs_dir):
            path.mkdir(parents=True, exist_ok=True)
        descriptor = attach_hash({
            "schema": STORE_SCHEMA,
            "version": "0.1.0",
            "seed": identity.as_record(),
            "hash_algorithm": "sha256",
            "canonical_json": "UTF-8; sorted keys; separators comma/colon; no NaN",
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

    def _put_hashed_json(self, directory: Path, value: Mapping[str, Any]) -> str:
        if not verify_hash(value):
            raise ValueError("attempted to store a JSON object with an invalid content_hash")
        ident = str(value["content_hash"])
        path = directory / (_digest_name(ident) + ".json")
        data = canonical_bytes(value)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"content address collision for {ident}")
        else:
            _atomic_write(path, data)
        return ident

    def put_blob(self, data: bytes, *, expected_hash: str | None = None) -> str:
        ident = digest_bytes(data)
        if expected_hash is not None and ident != expected_hash:
            raise ValueError(f"blob hash mismatch: {ident} != {expected_hash}")
        path = self._blob_path(ident)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"content address collision for blob {ident}")
        else:
            _atomic_write(path, data)
        return ident

    def read_blob(self, ident: str) -> bytes:
        data = self._blob_path(ident).read_bytes()
        actual = digest_bytes(data)
        if actual != ident:
            raise ValueError(f"stored blob hash mismatch: {ident}")
        return data

    def read_commit(self, ident: str | None = None) -> dict[str, Any]:
        commit_id = ident or self.head
        if commit_id is None:
            raise ValueError("world store has no commit")
        record = _load_json(self._commit_path(commit_id))
        if record.get("schema") != COMMIT_SCHEMA or not verify_hash(record):
            raise ValueError(f"invalid commit object: {commit_id}")
        if record["content_hash"] != commit_id:
            raise ValueError(f"commit filename/content mismatch: {commit_id}")
        return record

    def read_snapshot(self, ident: str) -> dict[str, Any]:
        snapshot = _load_json(self._snapshot_path(ident))
        if snapshot.get("schema") != SNAPSHOT_SCHEMA or not verify_hash(snapshot):
            raise ValueError(f"invalid snapshot object: {ident}")
        if snapshot["content_hash"] != ident:
            raise ValueError(f"snapshot filename/content mismatch: {ident}")
        return snapshot

    def snapshot_for_commit(self, commit: str | None = None) -> dict[str, Any]:
        commit_record = self.read_commit(commit)
        return self.read_snapshot(str(commit_record["snapshot_hash"]))

    def read_record(self, record_id: str, *, commit: str | None = None) -> dict[str, Any]:
        snapshot = self.snapshot_for_commit(commit)
        records = snapshot.get("records")
        if not isinstance(records, Mapping) or record_id not in records:
            raise KeyError(record_id)
        object_id = str(records[record_id])
        record = _load_json(self._object_path(object_id))
        validate_record(record)
        if record["content_hash"] != object_id or record["id"] != record_id:
            raise ValueError(f"record index/object mismatch: {record_id}")
        return record

    def list_records(self, *, commit: str | None = None, record_type: str | None = None) -> list[dict[str, Any]]:
        snapshot = self.snapshot_for_commit(commit)
        index = snapshot.get("records")
        if not isinstance(index, Mapping):
            raise ValueError("snapshot records index is invalid")
        result = []
        for record_id in sorted(index):
            record = self.read_record(record_id, commit=commit)
            if record_type is None or record["record_type"] == record_type:
                result.append(record)
        return result

    def verify_record(self, record_id: str, *, commit: str | None = None) -> dict[str, Any]:
        snapshot = self.snapshot_for_commit(commit)
        index = snapshot["records"]
        if record_id not in index:
            return {"id": record_id, "valid": False, "reason": "not present in snapshot"}
        object_id = str(index[record_id])
        path = self._object_path(object_id)
        try:
            record = self.read_record(record_id, commit=commit)
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
                existing_records = dict(current_snapshot["records"])
                existing_blobs = dict(current_snapshot["blobs"])
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
                staged_blob_data.append((blob_id, data, actual))
                blob_index[blob_id] = actual

            # Validate type-specific references against the prospective snapshot.
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

            # Store immutable staged content before publishing the snapshot/commit.
            for _, data, actual in staged_blob_data:
                self.put_blob(data, expected_hash=actual)
            record_index = dict(existing_records)
            for ident in order:
                record = staged_by_id[ident]
                object_id = self._put_hashed_json(self.objects_dir, record)
                record_index[ident] = object_id

            snapshot = attach_hash({
                "schema": SNAPSHOT_SCHEMA,
                "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
                "records": {key: record_index[key] for key in sorted(record_index)},
                "blobs": {key: blob_index[key] for key in sorted(blob_index)},
            })
            snapshot_id = self._put_hashed_json(self.snapshots_dir, snapshot)
            commit = attach_hash({
                "schema": COMMIT_SCHEMA,
                "version": "0.1.0",
                "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
                "sequence": sequence,
                "parent": current_head,
                "transaction_hash": transaction["content_hash"],
                "snapshot_hash": snapshot_id,
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
