"""Canonical JSON and content addressing for TOM World & Query Kernel 0.3."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def content_hash(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("content_hash", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(body)).hexdigest()


def attach_hash(record: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out.pop("content_hash", None)
    out["content_hash"] = content_hash(out)
    return out


def verify_hash(record: Mapping[str, Any]) -> bool:
    expected = record.get("content_hash")
    return isinstance(expected, str) and expected == content_hash(record)


def require_hash(record: Mapping[str, Any], *, label: str = "record") -> None:
    if not verify_hash(record):
        raise ValueError(f"{label} content hash mismatch")
