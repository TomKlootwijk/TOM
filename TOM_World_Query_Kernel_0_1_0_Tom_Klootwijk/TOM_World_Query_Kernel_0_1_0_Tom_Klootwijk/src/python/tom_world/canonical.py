"""Canonical JSON and content-addressed objects for the TOM world kernel."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

HASH_PREFIX = "sha256:"


def canonical_bytes(value: Any) -> bytes:
    """Return the profile's deterministic UTF-8 JSON representation."""

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest_bytes(data: bytes, *, prefix: bool = True) -> str:
    digest = hashlib.sha256(data).hexdigest()
    return HASH_PREFIX + digest if prefix else digest


def digest_file(path: str | Path, *, prefix: bool = True) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    return HASH_PREFIX + digest if prefix else digest


def content_hash(record: Mapping[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "content_hash"}
    return digest_bytes(canonical_bytes(body))


def attach_hash(record: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["content_hash"] = content_hash(result)
    return result


def verify_hash(record: Mapping[str, Any]) -> bool:
    return isinstance(record.get("content_hash"), str) and record["content_hash"] == content_hash(record)


def write_canonical(path: str | Path, value: Any, *, terminal_newline: bool = True) -> None:
    data = canonical_bytes(value) + (b"\n" if terminal_newline else b"")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
