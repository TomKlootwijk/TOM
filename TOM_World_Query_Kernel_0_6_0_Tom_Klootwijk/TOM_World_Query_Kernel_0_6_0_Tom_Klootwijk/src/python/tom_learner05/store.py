"""Append-only content-addressed promotion store for TOM Learner 0.1."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from tom_world03.canonical import attach_hash, canonical_bytes, require_hash, verify_hash

from .learner import LearningRun
from .model import BASE_HANDOFF_HASH, BASE_WORLD_HASH, CANONICAL_SEED_SHA256, PROFILE

STORE_SCHEMA = "TOM-LEARNER-STORE-0.1"
SNAPSHOT_SCHEMA = "TOM-LEARNER-SNAPSHOT-0.1"
COMMIT_SCHEMA = "TOM-LEARNER-COMMIT-0.1"
GENESIS_TRANSACTION_SCHEMA = "TOM-LEARNER-GENESIS-TRANSACTION-0.1"
PROMOTION_TRANSACTION_SCHEMA = "TOM-LEARNER-PROMOTION-TRANSACTION-0.1"


def _digest(content_hash: str) -> str:
    if not isinstance(content_hash, str) or not content_hash.startswith("sha256:") or len(content_hash) != 71:
        raise ValueError("content hash must be sha256:<64 lowercase hex>")
    try:
        int(content_hash[7:], 16)
    except ValueError as exc:
        raise ValueError("content hash contains invalid hexadecimal") from exc
    return content_hash[7:]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _record_bytes(record: Mapping[str, Any]) -> bytes:
    require_hash(record, label="store record")
    return canonical_bytes(record) + b"\n"


class LearnerStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @classmethod
    def initialize(
        cls,
        root: str | Path,
        seed_bytes: bytes,
        *,
        base_world_hash: str = BASE_WORLD_HASH,
        base_handoff_hash: str = BASE_HANDOFF_HASH,
    ) -> "LearnerStore":
        target = Path(root)
        if target.exists() and any(target.iterdir()):
            raise ValueError("learner store target must be absent or empty")
        if len(seed_bytes) != 244 or seed_bytes.endswith((b"\n", b"\r")):
            raise ValueError("learner store requires the exact 244-byte canonical seed")
        seed_sha = _sha256(seed_bytes)
        if seed_sha != CANONICAL_SEED_SHA256:
            raise ValueError("learner store canonical seed hash mismatch")
        for name in ("objects", "snapshots", "transactions", "commits"):
            (target / name).mkdir(parents=True, exist_ok=True)
        (target / "seed.bin").write_bytes(seed_bytes)

        descriptor = attach_hash({
            "schema": STORE_SCHEMA,
            "profile": PROFILE,
            "seed_sha256": seed_sha,
            "base_world_hash": base_world_hash,
            "base_handoff_hash": base_handoff_hash,
            "publication": "immutable records, transaction, snapshot, commit, then atomic HEAD",
        })
        (target / "store.json").write_bytes(_record_bytes(descriptor))

        snapshot = attach_hash({
            "schema": SNAPSHOT_SCHEMA,
            "profile": PROFILE,
            "base_world_hash": base_world_hash,
            "base_handoff_hash": base_handoff_hash,
            "accepted_definitions": {},
            "sessions": [],
            "accepted_sessions": [],
            "rejected_sessions": [],
        })
        transaction = attach_hash({
            "schema": GENESIS_TRANSACTION_SCHEMA,
            "profile": PROFILE,
            "base_world_hash": base_world_hash,
            "base_handoff_hash": base_handoff_hash,
            "seed_sha256": seed_sha,
            "snapshot_hash": snapshot["content_hash"],
        })
        store = cls(target)
        store._put("snapshots", snapshot)
        store._put("transactions", transaction)
        commit = attach_hash({
            "schema": COMMIT_SCHEMA,
            "profile": PROFILE,
            "sequence": 0,
            "parent_commit_hash": None,
            "transaction_hash": transaction["content_hash"],
            "snapshot_hash": snapshot["content_hash"],
        })
        store._put("commits", commit)
        _write_atomic(target / "HEAD", (commit["content_hash"] + "\n").encode("ascii"))
        return store

    def descriptor(self) -> dict[str, Any]:
        value = json.loads((self.root / "store.json").read_text(encoding="utf-8"))
        require_hash(value, label="learner store descriptor")
        if value.get("schema") != STORE_SCHEMA:
            raise ValueError("unsupported learner store schema")
        return value

    def head(self) -> str:
        value = (self.root / "HEAD").read_text(encoding="ascii").strip()
        _digest(value)
        return value

    def _path(self, namespace: str, content_hash: str) -> Path:
        return self.root / namespace / f"{_digest(content_hash)}.json"

    def _put(self, namespace: str, record: Mapping[str, Any]) -> str:
        data = _record_bytes(record)
        path = self._path(namespace, str(record["content_hash"]))
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"immutable {namespace} hash collision or byte mismatch")
            return str(record["content_hash"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(record["content_hash"])

    def _get(self, namespace: str, content_hash: str) -> dict[str, Any]:
        path = self._path(namespace, content_hash)
        if not path.is_file():
            raise ValueError(f"missing {namespace} record {content_hash}")
        value = json.loads(path.read_text(encoding="utf-8"))
        require_hash(value, label=f"{namespace} record")
        if value.get("content_hash") != content_hash:
            raise ValueError(f"{namespace} filename/hash mismatch")
        return value

    def commit_learning(self, run: LearningRun, *, expected_parent: str) -> dict[str, Any]:
        current = self.head()
        if expected_parent != current:
            raise ValueError(f"stale learner-store parent: expected {expected_parent}, current {current}")
        parent = self._get("commits", current)
        parent_snapshot = self._get("snapshots", parent["snapshot_hash"])
        descriptor = self.descriptor()
        if run.dataset.base_world_hash != descriptor["base_world_hash"]:
            raise ValueError("learning run base world differs from learner store")
        if run.dataset.base_handoff_hash != descriptor["base_handoff_hash"]:
            raise ValueError("learning run base handoff differs from learner store")

        # Immutable literal inputs and derived evidence are published before the
        # transaction can reference them.  The transaction carries the complete
        # ordered hash list, so no evidence object is reachable only by an
        # implicit host-language relationship.
        evidence_records: list[Mapping[str, Any]] = []
        seen_evidence: set[str] = set()
        for record in run.all_records():
            content_hash = str(record["content_hash"])
            if content_hash in seen_evidence:
                continue
            seen_evidence.add(content_hash)
            evidence_records.append(record)
            self._put("objects", record)
        evidence_record_hashes = [str(record["content_hash"]) for record in evidence_records]

        accepted_definitions = dict(parent_snapshot["accepted_definitions"])
        sessions = list(parent_snapshot["sessions"])
        accepted_sessions = list(parent_snapshot["accepted_sessions"])
        rejected_sessions = list(parent_snapshot["rejected_sessions"])
        if run.dataset.id in sessions:
            raise ValueError(f"observation set {run.dataset.id} already has a committed session")
        sessions.append(run.dataset.id)
        if run.accepted:
            if run.learned_definition is None:
                raise AssertionError("accepted run has no learned definition")
            accepted_definitions[run.dataset.id] = run.learned_definition["content_hash"]
            accepted_sessions.append(run.certificate["content_hash"])
        else:
            if run.rejection_lineage is None:
                raise AssertionError("rejected run has no rejection lineage")
            rejected_sessions.append(run.rejection_lineage["content_hash"])

        snapshot = attach_hash({
            "schema": SNAPSHOT_SCHEMA,
            "profile": PROFILE,
            "base_world_hash": descriptor["base_world_hash"],
            "base_handoff_hash": descriptor["base_handoff_hash"],
            "accepted_definitions": {key: accepted_definitions[key] for key in sorted(accepted_definitions)},
            "sessions": sessions,
            "accepted_sessions": accepted_sessions,
            "rejected_sessions": rejected_sessions,
        })
        transaction = attach_hash({
            "schema": PROMOTION_TRANSACTION_SCHEMA,
            "profile": PROFILE,
            "sequence": int(parent["sequence"]) + 1,
            "parent_commit_hash": current,
            "parent_snapshot_hash": parent["snapshot_hash"],
            "base_world_hash": descriptor["base_world_hash"],
            "base_handoff_hash": descriptor["base_handoff_hash"],
            "observation_set_id": run.dataset.id,
            "observation_set_hash": run.dataset.content_hash,
            "learning_certificate_hash": run.certificate["content_hash"],
            "acceptance_decision_hash": run.decision["content_hash"],
            "evidence_record_hashes": evidence_record_hashes,
            "accepted": run.accepted,
            "learned_definition_hash": None if run.learned_definition is None else run.learned_definition["content_hash"],
            "rejection_lineage_hash": None if run.rejection_lineage is None else run.rejection_lineage["content_hash"],
            "new_snapshot_hash": snapshot["content_hash"],
            "authority_rule": "only this parent-bound transaction changes the learner overlay snapshot",
        })
        self._put("snapshots", snapshot)
        self._put("transactions", transaction)
        commit = attach_hash({
            "schema": COMMIT_SCHEMA,
            "profile": PROFILE,
            "sequence": int(parent["sequence"]) + 1,
            "parent_commit_hash": current,
            "transaction_hash": transaction["content_hash"],
            "snapshot_hash": snapshot["content_hash"],
        })
        self._put("commits", commit)
        _write_atomic(self.root / "HEAD", (commit["content_hash"] + "\n").encode("ascii"))
        return commit

    def chain(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        current: str | None = self.head()
        while current is not None:
            if current in seen:
                raise ValueError("learner-store commit cycle")
            seen.add(current)
            commit = self._get("commits", current)
            result.append(commit)
            current = commit.get("parent_commit_hash")
        result.reverse()
        for index, commit in enumerate(result):
            if int(commit.get("sequence", -1)) != index:
                raise ValueError("learner-store commit sequence is not contiguous")
            expected_parent = None if index == 0 else result[index - 1]["content_hash"]
            if commit.get("parent_commit_hash") != expected_parent:
                raise ValueError("learner-store parent chain mismatch")
        return result

    def reconstruct(self) -> dict[str, Any]:
        chain = self.chain()
        terminal = chain[-1]
        snapshot = self._get("snapshots", terminal["snapshot_hash"])
        sessions: list[dict[str, Any]] = []
        for commit in chain[1:]:
            transaction = self._get("transactions", commit["transaction_hash"])
            sessions.append({
                "sequence": commit["sequence"],
                "commit_hash": commit["content_hash"],
                "transaction_hash": transaction["content_hash"],
                "observation_set_id": transaction["observation_set_id"],
                "learning_certificate_hash": transaction["learning_certificate_hash"],
                "accepted": transaction["accepted"],
                "learned_definition_hash": transaction["learned_definition_hash"],
                "rejection_lineage_hash": transaction["rejection_lineage_hash"],
            })
        semantic = {
            "schema": "TOM-LEARNER-RECONSTRUCTION-SEMANTIC-0.1",
            "base_world_hash": snapshot["base_world_hash"],
            "base_handoff_hash": snapshot["base_handoff_hash"],
            "accepted_definitions": snapshot["accepted_definitions"],
            "sessions": sessions,
            "terminal_commit_hash": terminal["content_hash"],
            "terminal_snapshot_hash": snapshot["content_hash"],
        }
        return attach_hash({
            "schema": "TOM-LEARNER-RECONSTRUCTION-0.1",
            "profile": PROFILE,
            "semantic": semantic,
            "semantic_sha256": "sha256:" + hashlib.sha256(canonical_bytes(semantic)).hexdigest(),
        })

    def audit(self, *, require_no_orphans: bool = True) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        reachable: dict[str, set[str]] = {name: set() for name in ("objects", "snapshots", "transactions", "commits")}
        try:
            descriptor = self.descriptor()
            seed = (self.root / "seed.bin").read_bytes()
            if len(seed) != 244 or seed.endswith((b"\n", b"\r")) or _sha256(seed) != descriptor["seed_sha256"]:
                errors.append("seed.bin does not match the store descriptor")
            chain = self.chain()
            for commit in chain:
                commit_hash = commit["content_hash"]
                reachable["commits"].add(commit_hash)
                try:
                    transaction = self._get("transactions", commit["transaction_hash"])
                    snapshot = self._get("snapshots", commit["snapshot_hash"])
                except Exception as exc:
                    errors.append(str(exc))
                    continue
                reachable["transactions"].add(transaction["content_hash"])
                reachable["snapshots"].add(snapshot["content_hash"])
                if commit["sequence"] == 0:
                    if transaction.get("schema") != GENESIS_TRANSACTION_SCHEMA:
                        errors.append("genesis commit does not reference a genesis transaction")
                    continue
                if transaction.get("schema") != PROMOTION_TRANSACTION_SCHEMA:
                    errors.append(f"commit {commit_hash} has an unsupported promotion transaction")
                    continue
                if transaction.get("new_snapshot_hash") != snapshot["content_hash"]:
                    errors.append(f"commit {commit_hash} transaction/snapshot binding mismatch")
                evidence_hashes = transaction.get("evidence_record_hashes")
                if not isinstance(evidence_hashes, list) or not evidence_hashes:
                    errors.append(f"commit {commit_hash} promotion transaction has no evidence_record_hashes")
                    evidence_hashes = []
                if len(evidence_hashes) != len(set(evidence_hashes)):
                    errors.append(f"commit {commit_hash} promotion transaction repeats evidence hashes")
                object_hashes = [
                    *evidence_hashes,
                    transaction.get("learning_certificate_hash"),
                    transaction.get("acceptance_decision_hash"),
                    transaction.get("learned_definition_hash"),
                    transaction.get("rejection_lineage_hash"),
                ]
                for content_hash in object_hashes:
                    if content_hash is None:
                        continue
                    try:
                        self._get("objects", content_hash)
                        reachable["objects"].add(content_hash)
                    except Exception as exc:
                        errors.append(str(exc))
                for content_hash in snapshot.get("accepted_definitions", {}).values():
                    try:
                        self._get("objects", content_hash)
                        reachable["objects"].add(content_hash)
                    except Exception as exc:
                        errors.append(str(exc))
                for content_hash in snapshot.get("accepted_sessions", []):
                    try:
                        self._get("objects", content_hash)
                        reachable["objects"].add(content_hash)
                    except Exception as exc:
                        errors.append(str(exc))
                for content_hash in snapshot.get("rejected_sessions", []):
                    try:
                        self._get("objects", content_hash)
                        reachable["objects"].add(content_hash)
                    except Exception as exc:
                        errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))
            chain = []

        # Every immutable file must be correctly named and hashed.  Evidence
        # objects may be retained even if not in the terminal snapshot because
        # promotion transactions bind their top-level records.
        actual: dict[str, set[str]] = {name: set() for name in reachable}
        for namespace in actual:
            directory = self.root / namespace
            if not directory.exists():
                errors.append(f"missing namespace directory {namespace}")
                continue
            for path in sorted(directory.glob("*.json")):
                try:
                    raw = path.read_bytes()
                    value = json.loads(raw.decode("utf-8"))
                    if not verify_hash(value):
                        errors.append(f"{namespace}/{path.name} content hash mismatch")
                        continue
                    if raw != _record_bytes(value):
                        errors.append(f"{namespace}/{path.name} is not canonical JSON plus one LF")
                    content_hash = str(value["content_hash"])
                    if path.stem != _digest(content_hash):
                        errors.append(f"{namespace}/{path.name} filename hash mismatch")
                    actual[namespace].add(content_hash)
                except Exception as exc:
                    errors.append(f"{namespace}/{path.name}: {exc}")
        for namespace in actual:
            orphans = sorted(actual[namespace] - reachable[namespace])
            if not orphans:
                continue
            message = f"orphan {namespace}: " + ", ".join(orphans)
            if require_no_orphans:
                errors.append(message)
            else:
                warnings.append(message)

        return attach_hash({
            "schema": "TOM-LEARNER-STORE-AUDIT-0.1",
            "profile": PROFILE,
            "valid": not errors,
            "require_no_orphans": require_no_orphans,
            "commit_count": len(chain),
            "object_count": len(actual["objects"]),
            "snapshot_count": len(actual["snapshots"]),
            "transaction_count": len(actual["transactions"]),
            "errors": errors,
            "warnings": warnings,
        })
