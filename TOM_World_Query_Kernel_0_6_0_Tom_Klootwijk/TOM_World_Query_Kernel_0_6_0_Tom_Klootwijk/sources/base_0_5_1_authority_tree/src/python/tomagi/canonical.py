"""Canonical JSON and content-addressed definition records."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def content_hash(record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "content_hash"}
    return "sha256:" + hashlib.sha256(canonical_bytes(body)).hexdigest()


def attach_hash(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    out["content_hash"] = content_hash(out)
    return out


def verify_hash(record: dict[str, Any]) -> bool:
    return record.get("content_hash") == content_hash(record)
