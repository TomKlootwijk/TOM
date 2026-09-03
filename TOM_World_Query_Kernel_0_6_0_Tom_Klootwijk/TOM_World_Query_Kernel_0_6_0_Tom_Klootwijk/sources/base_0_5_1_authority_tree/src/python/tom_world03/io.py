"""Load and write canonical 0.3 records."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_bytes
from .model import IntervalWorld


def load_record(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def load_world(path: str | Path) -> tuple[dict[str, Any], IntervalWorld]:
    record = load_record(path)
    return record, IntervalWorld.from_record(record)


def write_canonical(path: str | Path, value: Mapping[str, Any] | list[Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_bytes(value) + b"\n")
