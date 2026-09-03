"""Canonical JSON and content-addressed definition records."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def _validate_json_domain(value: Any, path: str = "$") -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(
                    f"canonical JSON object key at {path} must be a string, "
                    f"not {type(key).__name__}"
                )
            _validate_json_domain(item, f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            _validate_json_domain(item, f"{path}[{index}]")
    elif value is None or type(value) in {str, int, float, bool}:
        return
    else:
        raise TypeError(
            f"canonical JSON value at {path} must use exact JSON-domain types, "
            f"not {type(value).__name__}"
        )


def canonical_bytes(value: Any) -> bytes:
    _validate_json_domain(value)
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
