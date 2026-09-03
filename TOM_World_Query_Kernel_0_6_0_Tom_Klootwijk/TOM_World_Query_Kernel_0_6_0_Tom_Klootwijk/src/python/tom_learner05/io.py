"""Literal JSON loading and canonical output helpers for TOM Learner 0.1."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from tom_world03.canonical import canonical_bytes, require_hash

from .model import ObservationSet


def load_record(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("literal source must contain a JSON object")
    require_hash(value, label=Path(path).name)
    return value


def load_observation_set(path: str | Path) -> tuple[dict[str, Any], ObservationSet]:
    record = load_record(path)
    dataset = ObservationSet.from_record(record)
    if canonical_bytes(dataset.to_record()) != canonical_bytes(record):
        raise ValueError("observation set contains unsupported or noncanonical fields")
    return record, dataset


def write_canonical(value: Mapping[str, Any] | list[Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_bytes(value) + b"\n")
