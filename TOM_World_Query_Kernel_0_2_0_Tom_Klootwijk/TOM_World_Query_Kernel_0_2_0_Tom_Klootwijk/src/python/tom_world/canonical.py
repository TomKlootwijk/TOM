"""Canonical JSON and content-addressed objects for the TOM world kernel."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

HASH_PREFIX = "sha256:"


def _validate_json_domain(value: Any, path: str = "$") -> None:
    """Reject Python values that JSON would silently change on persistence."""

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
    """Return the profile's deterministic UTF-8 JSON representation."""

    _validate_json_domain(value)
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
