"""Generic append-only content-addressed publication store.

This module deliberately knows nothing about learners, observations, models, or
promotion policy.  Its only semantics are finite canonical JSON, immutable
content-addressed records, a declared namespace set, ordered publication
batches, and compare-and-swap replacement of one mutable ``HEAD`` pointer.

Domain authority must arrive in a content-addressed publication plan produced by
an executable TOMAGI definition graph.  This host module validates and applies
that plan; it does not invent its records or decide what they mean.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Iterator, Mapping, Sequence

from .canonical import canonical_bytes, content_hash, verify_hash

PLAN_SCHEMA = "TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.0"
CONTINUATION_PLAN_SCHEMA = "TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.1"
PUBLICATION_SCHEMA = "TOMAGI-IMMUTABLE-PUBLICATION-1.0"
DESCRIPTOR_SCHEMA = "TOMAGI-IMMUTABLE-STORE-DESCRIPTOR-1.0"
AUDIT_SCHEMA = "TOMAGI-IMMUTABLE-STORE-AUDIT-1.0"

_HASH_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_NAMESPACE_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


_THREAD_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.RLock] = {}


def _thread_lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _THREAD_LOCKS[key] = lock
        return lock


@contextmanager
def _same_host_publication_lock(root: Path) -> Iterator[None]:
    """Serialize publication on one host across threads and processes.

    The lock spans the expected-HEAD read, immutable writes and verification,
    and atomic HEAD replacement. OS file locks are released automatically if a
    publishing process exits abnormally. Cross-host shared-store coordination is
    deliberately outside this profile.
    """

    lock_path = root / ".publication.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock_for(lock_path)
    with thread_lock:
        with lock_path.open("a+b") as handle:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                    os.fsync(handle.fileno())
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _hash_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be sha256:<64 lowercase hex>")
    return value


def _namespace(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or _NAMESPACE_RE.fullmatch(value) is None:
        raise ValueError(f"{label} is not a safe namespace")
    return value


def _addressed(record: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TypeError(f"{label} must be an object")
    value = dict(record)
    try:
        canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not finite canonical JSON") from exc
    if not verify_hash(value):
        raise ValueError(f"{label} content hash mismatch")
    _hash_text(value.get("content_hash"), label=f"{label}.content_hash")
    return value


def _record_bytes(record: Mapping[str, Any]) -> bytes:
    value = _addressed(record, label="immutable record")
    return canonical_bytes(value) + b"\n"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _strict_keys(value: Mapping[str, Any], *, required: set[str], allowed: set[str], label: str) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        raise ValueError(f"{label} missing fields: {missing}")
    if extra:
        raise ValueError(f"{label} has unknown fields: {extra}")


def validate_descriptor(record: Any) -> dict[str, Any]:
    value = _addressed(record, label="store descriptor")
    _strict_keys(
        value,
        required={
            "schema", "profile", "seed_sha256", "namespaces", "head_namespace",
            "record_encoding", "publication_rule", "content_hash",
        },
        allowed={
            "schema", "profile", "seed_sha256", "base_world_hash",
            "base_handoff_hash", "corrective_handoff_hash", "namespaces",
            "head_namespace", "record_encoding", "publication_rule", "content_hash",
        },
        label="store descriptor",
    )
    if value["schema"] != DESCRIPTOR_SCHEMA:
        raise ValueError("unsupported store descriptor schema")
    if not isinstance(value["profile"], str) or not value["profile"]:
        raise ValueError("store descriptor profile must be a non-empty string")
    _hash_text(value["seed_sha256"], label="store descriptor seed_sha256")
    for optional in ("base_world_hash", "base_handoff_hash", "corrective_handoff_hash"):
        if optional in value:
            _hash_text(value[optional], label=f"store descriptor {optional}")
    namespaces = value["namespaces"]
    if not isinstance(namespaces, list) or not namespaces:
        raise ValueError("store descriptor namespaces must be a non-empty array")
    checked = [_namespace(item, label="store descriptor namespace") for item in namespaces]
    if len(checked) != len(set(checked)):
        raise ValueError("store descriptor namespaces must be unique")
    if checked != sorted(checked):
        raise ValueError("store descriptor namespaces must be sorted")
    head_namespace = _namespace(value["head_namespace"], label="head_namespace")
    if head_namespace not in checked:
        raise ValueError("head_namespace must be one of the declared namespaces")
    if value["record_encoding"] != "canonical-json-plus-lf":
        raise ValueError("unsupported immutable record encoding")
    if value["publication_rule"] != "write-immutable-records-then-cas-head":
        raise ValueError("unsupported publication rule")
    return value


def validate_publication(record: Any, descriptor: Mapping[str, Any]) -> dict[str, Any]:
    value = _addressed(record, label="publication")
    _strict_keys(
        value,
        required={
            "schema", "profile", "sequence", "expected_head", "replacement_head",
            "required_hashes", "writes", "content_hash",
        },
        allowed={
            "schema", "profile", "sequence", "expected_head", "replacement_head",
            "required_hashes", "writes", "content_hash",
        },
        label="publication",
    )
    if value["schema"] != PUBLICATION_SCHEMA:
        raise ValueError("unsupported publication schema")
    if value["profile"] != descriptor["profile"]:
        raise ValueError("publication profile differs from store descriptor")
    sequence = value["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("publication sequence must be a non-negative integer")
    expected = value["expected_head"]
    if expected is not None:
        _hash_text(expected, label="publication expected_head")
    replacement = _hash_text(value["replacement_head"], label="publication replacement_head")
    required = value["required_hashes"]
    if not isinstance(required, list):
        raise ValueError("publication required_hashes must be an array")
    required_checked = [_hash_text(item, label="publication required hash") for item in required]
    if len(required_checked) != len(set(required_checked)):
        raise ValueError("publication required_hashes must be unique")
    writes = value["writes"]
    if not isinstance(writes, list) or not writes:
        raise ValueError("publication writes must be a non-empty array")
    normalized_writes: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for index, item in enumerate(writes):
        if not isinstance(item, Mapping):
            raise TypeError(f"publication write {index} must be an object")
        _strict_keys(
            item,
            required={"namespace", "record"},
            allowed={"namespace", "record"},
            label=f"publication write {index}",
        )
        namespace = _namespace(item["namespace"], label=f"publication write {index} namespace")
        if namespace not in descriptor["namespaces"]:
            raise ValueError(f"publication write {index} names an undeclared namespace")
        addressed = _addressed(item["record"], label=f"publication write {index} record")
        identity = (namespace, addressed["content_hash"])
        if identity in identities:
            raise ValueError("publication repeats an immutable write")
        identities.add(identity)
        normalized_writes.append({"namespace": namespace, "record": addressed})
    if not any(
        item["namespace"] == descriptor["head_namespace"]
        and item["record"]["content_hash"] == replacement
        for item in normalized_writes
    ):
        raise ValueError("replacement_head must be written in head_namespace by the publication")
    value["writes"] = normalized_writes
    return value


def _validate_writes(
    writes: Any,
    descriptor: Mapping[str, Any],
    *,
    label: str,
    require_nonempty: bool,
) -> list[dict[str, Any]]:
    if not isinstance(writes, list) or (require_nonempty and not writes):
        qualifier = "a non-empty" if require_nonempty else "an"
        raise ValueError(f"{label} must be {qualifier} array")
    normalized: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for index, item in enumerate(writes):
        if not isinstance(item, Mapping):
            raise TypeError(f"{label} {index} must be an object")
        _strict_keys(
            item,
            required={"namespace", "record"},
            allowed={"namespace", "record"},
            label=f"{label} {index}",
        )
        namespace = _namespace(item["namespace"], label=f"{label} {index} namespace")
        if namespace not in descriptor["namespaces"]:
            raise ValueError(f"{label} {index} names an undeclared namespace")
        addressed = _addressed(item["record"], label=f"{label} {index} record")
        identity = (namespace, addressed["content_hash"])
        if identity in identities:
            raise ValueError(f"{label} repeats an immutable record")
        identities.add(identity)
        normalized.append({"namespace": namespace, "record": addressed})
    return normalized


def validate_plan(record: Any) -> dict[str, Any]:
    """Validate a genesis plan (1.0) or a parent-bound continuation plan (1.1).

    Version 1.1 is a mechanical store extension.  It carries the immutable
    records needed to reconstruct an already-authoritative starting HEAD, then
    applies a new contiguous publication suffix.  It does not decide which
    records are evidence or whether a learner proposal should be accepted.
    """

    value = _addressed(record, label="publication plan")
    schema = value.get("schema")
    if schema == PLAN_SCHEMA:
        _strict_keys(
            value,
            required={
                "schema", "profile", "store_descriptor", "publications",
                "terminal_head", "content_hash",
            },
            allowed={
                "schema", "profile", "store_descriptor", "publications",
                "terminal_head", "content_hash",
            },
            label="publication plan",
        )
        initial_head: str | None = None
        base_records: list[dict[str, Any]] = []
    elif schema == CONTINUATION_PLAN_SCHEMA:
        _strict_keys(
            value,
            required={
                "schema", "profile", "store_descriptor", "initial_head",
                "base_records", "publications", "terminal_head", "content_hash",
            },
            allowed={
                "schema", "profile", "store_descriptor", "initial_head",
                "base_records", "publications", "terminal_head", "content_hash",
            },
            label="continuation publication plan",
        )
        initial_head = _hash_text(value["initial_head"], label="publication plan initial_head")
        # The descriptor is validated below before base records are checked.
        base_records = []
    else:
        raise ValueError("unsupported publication plan schema")

    descriptor = validate_descriptor(value["store_descriptor"])
    if value["profile"] != descriptor["profile"]:
        raise ValueError("publication plan profile differs from descriptor")

    if schema == CONTINUATION_PLAN_SCHEMA:
        base_records = _validate_writes(
            value["base_records"], descriptor,
            label="publication plan base record", require_nonempty=True,
        )
        head_matches = [
            item for item in base_records
            if item["namespace"] == descriptor["head_namespace"]
            and item["record"]["content_hash"] == initial_head
        ]
        if len(head_matches) != 1:
            raise ValueError(
                "continuation plan initial_head must occur exactly once in base_records "
                "under head_namespace"
            )

    publications = value["publications"]
    if not isinstance(publications, list) or not publications:
        raise ValueError("publication plan requires a non-empty publications array")
    checked: list[dict[str, Any]] = []
    previous = initial_head
    first_sequence: int | None = None
    for index, item in enumerate(publications):
        publication = validate_publication(item, descriptor)
        if first_sequence is None:
            first_sequence = publication["sequence"]
            if schema == PLAN_SCHEMA and first_sequence != 0:
                raise ValueError("version 1.0 publication sequences must start at zero")
        assert first_sequence is not None
        if publication["sequence"] != first_sequence + index:
            raise ValueError("publication plan sequences must be contiguous")
        if publication["expected_head"] != previous:
            raise ValueError("publication plan expected_head chain mismatch")
        previous = publication["replacement_head"]
        checked.append(publication)
    terminal = _hash_text(value["terminal_head"], label="publication plan terminal_head")
    if terminal != previous:
        raise ValueError("publication plan terminal_head differs from final replacement")

    # An immutable identity may occur in one namespace only once across the
    # continuation prefix and suffix.  Equal content in different namespaces is
    # allowed because namespaces are part of the store address.
    identities: dict[tuple[str, str], bytes] = {}
    for write in base_records:
        key = (write["namespace"], write["record"]["content_hash"])
        identities[key] = _record_bytes(write["record"])
    for publication in checked:
        for write in publication["writes"]:
            key = (write["namespace"], write["record"]["content_hash"])
            data = _record_bytes(write["record"])
            prior = identities.get(key)
            if prior is not None and prior != data:
                raise ValueError("publication plan contains incompatible immutable bytes")
            identities[key] = data

    value["store_descriptor"] = descriptor
    value["initial_head"] = initial_head
    value["base_records"] = base_records
    value["publications"] = checked
    return value


class ImmutablePublicationStore:
    """Apply one validated plan to an empty or matching append-only store."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def _digest(content_hash_text: str) -> str:
        return _hash_text(content_hash_text, label="content hash")[7:]

    def _path(self, namespace: str, content_hash_text: str) -> Path:
        namespace = _namespace(namespace, label="namespace")
        return self.root / namespace / f"{self._digest(content_hash_text)}.json"

    def _put(self, namespace: str, record: Mapping[str, Any]) -> None:
        data = _record_bytes(record)
        path = self._path(namespace, str(record["content_hash"]))
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("immutable content-address collision or byte mismatch")
            return
        _atomic_write(path, data)

    def _current_head(self) -> str | None:
        path = self.root / "HEAD"
        if not path.exists():
            return None
        raw = path.read_bytes()
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("HEAD must be ASCII") from exc
        if not text.endswith("\n") or text.count("\n") != 1:
            raise ValueError("HEAD must contain one hash and one terminal LF")
        return _hash_text(text[:-1], label="HEAD")

    def _all_hashes(self, descriptor: Mapping[str, Any]) -> set[str]:
        result: set[str] = set()
        for namespace in descriptor["namespaces"]:
            directory = self.root / namespace
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                record = _addressed(
                    json.loads(path.read_text(encoding="utf-8")),
                    label=f"stored record {namespace}/{path.name}",
                )
                if path.stem != self._digest(record["content_hash"]):
                    raise ValueError(f"stored record filename/hash mismatch: {namespace}/{path.name}")
                if path.read_bytes() != _record_bytes(record):
                    raise ValueError(f"stored record is not canonical JSON plus LF: {namespace}/{path.name}")
                result.add(record["content_hash"])
        return result

    @classmethod
    def initialize(
        cls,
        root: str | Path,
        descriptor: Mapping[str, Any],
        seed_bytes: bytes,
        *,
        base_records: Sequence[Mapping[str, Any]] | None = None,
        initial_head: str | None = None,
    ) -> "ImmutablePublicationStore":
        store = cls(root)
        if store.root.exists() and any(store.root.iterdir()):
            raise ValueError("immutable publication store target must be absent or empty")
        checked = validate_descriptor(descriptor)
        seed_hash = "sha256:" + __import__("hashlib").sha256(seed_bytes).hexdigest()
        if seed_hash != checked["seed_sha256"]:
            raise ValueError("seed bytes do not match store descriptor")
        if seed_bytes.endswith((b"\n", b"\r")):
            raise ValueError("canonical seed must not have a terminal line ending")
        normalized_base = _validate_writes(
            list(base_records or []), checked,
            label="store base record", require_nonempty=initial_head is not None,
        )
        if initial_head is not None:
            initial_head = _hash_text(initial_head, label="initial_head")
            matches = [
                item for item in normalized_base
                if item["namespace"] == checked["head_namespace"]
                and item["record"]["content_hash"] == initial_head
            ]
            if len(matches) != 1:
                raise ValueError(
                    "initial_head must occur exactly once in base_records under head_namespace"
                )
        elif normalized_base:
            raise ValueError("base_records require an explicit initial_head")

        store.root.mkdir(parents=True, exist_ok=True)
        for namespace in checked["namespaces"]:
            (store.root / namespace).mkdir(parents=True, exist_ok=True)
        _atomic_write(store.root / "seed.bin", bytes(seed_bytes))
        _atomic_write(store.root / "store.json", _record_bytes(checked))
        for write in normalized_base:
            store._put(write["namespace"], write["record"])
        if initial_head is not None:
            _atomic_write(store.root / "HEAD", (initial_head + "\n").encode("ascii"))
        return store


    def descriptor(self) -> dict[str, Any]:
        path = self.root / "store.json"
        if not path.is_file():
            raise ValueError("store descriptor is missing")
        record = json.loads(path.read_text(encoding="utf-8"))
        checked = validate_descriptor(record)
        if path.read_bytes() != _record_bytes(checked):
            raise ValueError("store descriptor is not canonical JSON plus LF")
        return checked

    def apply_publication(self, publication: Mapping[str, Any]) -> str:
        descriptor = self.descriptor()
        checked = validate_publication(publication, descriptor)
        with _same_host_publication_lock(self.root):
            current = self._current_head()
            if checked["expected_head"] != current:
                raise ValueError(
                    f"stale publication head: expected {checked['expected_head']}, current {current}"
                )
            for write in checked["writes"]:
                self._put(write["namespace"], write["record"])
            available = self._all_hashes(descriptor)
            missing = [item for item in checked["required_hashes"] if item not in available]
            if missing:
                raise ValueError(
                    "publication required hashes are unavailable: " + ", ".join(missing)
                )
            replacement_path = self._path(
                descriptor["head_namespace"], checked["replacement_head"]
            )
            if not replacement_path.is_file():
                raise ValueError("replacement_head record is missing from head_namespace")
            _atomic_write(
                self.root / "HEAD",
                (checked["replacement_head"] + "\n").encode("ascii"),
            )
            return checked["replacement_head"]

    @classmethod
    def apply_plan(
        cls,
        root: str | Path,
        seed_bytes: bytes,
        plan: Mapping[str, Any],
    ) -> "ImmutablePublicationStore":
        checked = validate_plan(plan)
        store = cls.initialize(
            root,
            checked["store_descriptor"],
            seed_bytes,
            base_records=checked["base_records"],
            initial_head=checked["initial_head"],
        )
        for publication in checked["publications"]:
            store.apply_publication(publication)
        if store._current_head() != checked["terminal_head"]:
            raise ValueError("applied plan did not reach terminal_head")
        return store

    def audit_plan(
        self,
        plan: Mapping[str, Any],
        *,
        require_no_extra_records: bool = True,
    ) -> dict[str, Any]:
        errors: list[str] = []
        try:
            checked = validate_plan(plan)
            descriptor = self.descriptor()
            if descriptor != checked["store_descriptor"]:
                errors.append("stored descriptor differs from publication plan")
            seed = (self.root / "seed.bin").read_bytes()
            seed_hash = "sha256:" + __import__("hashlib").sha256(seed).hexdigest()
            if seed_hash != descriptor["seed_sha256"] or seed.endswith((b"\n", b"\r")):
                errors.append("stored seed differs from descriptor")
            expected_records: dict[tuple[str, str], bytes] = {}
            for write in checked["base_records"]:
                key = (write["namespace"], write["record"]["content_hash"])
                expected_records[key] = _record_bytes(write["record"])
            expected_head = checked["initial_head"]
            for publication in checked["publications"]:
                if publication["expected_head"] != expected_head:
                    errors.append("publication expected-head chain differs during audit")
                for write in publication["writes"]:
                    key = (write["namespace"], write["record"]["content_hash"])
                    data = _record_bytes(write["record"])
                    previous = expected_records.get(key)
                    if previous is not None and previous != data:
                        errors.append("plan contains incompatible duplicate immutable records")
                    expected_records[key] = data
                expected_head = publication["replacement_head"]
            for (namespace, content_hash_text), expected in expected_records.items():
                path = self._path(namespace, content_hash_text)
                if not path.is_file():
                    errors.append(f"missing planned record {namespace}/{content_hash_text}")
                elif path.read_bytes() != expected:
                    errors.append(f"planned record byte mismatch {namespace}/{content_hash_text}")
            if self._current_head() != checked["terminal_head"]:
                errors.append("HEAD differs from plan terminal_head")
            if require_no_extra_records:
                actual: set[tuple[str, str]] = set()
                for namespace in descriptor["namespaces"]:
                    for path in sorted((self.root / namespace).glob("*.json")):
                        actual.add((namespace, "sha256:" + path.stem))
                extras = sorted(actual - set(expected_records))
                if extras:
                    errors.append(
                        "unplanned immutable records: "
                        + ", ".join(f"{n}/{h}" for n, h in extras)
                    )
        except Exception as exc:  # audit returns evidence rather than hiding the failure.
            errors.append(str(exc))
            checked = None
            expected_records = {}
        body = {
            "schema": AUDIT_SCHEMA,
            "valid": not errors,
            "require_no_extra_records": require_no_extra_records,
            "plan_schema": None if checked is None else checked["schema"],
            "base_records": 0 if checked is None else len(checked["base_records"]),
            "planned_publications": 0 if checked is None else len(checked["publications"]),
            "planned_records": len(expected_records),
            "initial_head": None if checked is None else checked["initial_head"],
            "terminal_head": None if checked is None else checked["terminal_head"],
            "errors": errors,
        }
        body["content_hash"] = content_hash(body)
        return body


__all__ = [
    "PLAN_SCHEMA",
    "CONTINUATION_PLAN_SCHEMA",
    "PUBLICATION_SCHEMA",
    "DESCRIPTOR_SCHEMA",
    "AUDIT_SCHEMA",
    "validate_descriptor",
    "validate_publication",
    "validate_plan",
    "ImmutablePublicationStore",
]
