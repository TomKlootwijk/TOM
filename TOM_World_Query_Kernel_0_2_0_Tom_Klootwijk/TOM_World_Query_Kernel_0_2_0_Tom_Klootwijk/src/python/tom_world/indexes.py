"""Immutable secondary indexes for TOM World & Query Kernel 0.2.

The index is a pure, content-addressed projection of an immutable snapshot's
record map.  It contains no timestamps, host paths, object addresses, or
backend-specific ordering.  Deleting an index file cannot destroy world data:
``WorldStore.rebuild_indexes`` deterministically reconstructs the exact bytes
from the snapshot's immutable records.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .canonical import attach_hash, canonical_bytes, digest_bytes, verify_hash
from .records import validate_record

INDEX_SCHEMA = "TOM-WORLD-INDEXES-0.2"
INDEX_VERSION = "0.2.0"


def _sorted_map_of_sets(source: Mapping[str, set[str]]) -> dict[str, list[str]]:
    return {key: sorted(source[key]) for key in sorted(source)}


def _require_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def canonical_index_key(value: Any) -> tuple[str, Any | None]:
    """Return a stable string key plus optional canonical value metadata.

    Scalar values remain human-readable.  Compound JSON values are keyed by
    their canonical SHA-256 and retained once in ``generative_address_values``.
    """

    if value is None:
        return "null", None
    if isinstance(value, bool):
        return "bool:true" if value else "bool:false", None
    if isinstance(value, int):
        return f"int:{value}", None
    if isinstance(value, str):
        return "str:" + value, None
    data = canonical_bytes(value)
    return "json:" + digest_bytes(data, prefix=False), value


def record_time_interval(record: Mapping[str, Any]) -> tuple[int, int] | None:
    payload = record["payload"]
    interval = payload.get("active_interval", payload.get("time_interval"))
    if isinstance(interval, Mapping):
        start = _require_int(interval.get("start"), f"{record['id']}.interval.start", minimum=0)
        end = _require_int(interval.get("end"), f"{record['id']}.interval.end", minimum=0)
        if end < start:
            raise ValueError(f"{record['id']} interval end precedes start")
        return start, end
    if record["record_type"] == "event" and isinstance(payload.get("event_tick"), int):
        tick = _require_int(payload["event_tick"], f"{record['id']}.event_tick", minimum=0)
        return tick, tick
    if record["record_type"] == "checkpoint" and isinstance(payload.get("tick"), int):
        tick = _require_int(payload["tick"], f"{record['id']}.tick", minimum=0)
        return tick, tick
    return None


def record_topology_sheet(record: Mapping[str, Any]) -> int | None:
    payload = record["payload"]
    if "topology_sheet" in payload:
        return _require_int(payload["topology_sheet"], f"{record['id']}.topology_sheet", minimum=0)
    if record["record_type"] == "instance":
        state = payload.get("initial_state")
        if isinstance(state, Mapping) and "sheet" in state:
            return _require_int(state["sheet"], f"{record['id']}.initial_state.sheet", minimum=0)
    return None


def build_index_record(
    records: Mapping[str, str],
    loader: Callable[[str, str], Mapping[str, Any]],
    *,
    seed_sha256: str,
) -> dict[str, Any]:
    """Build the exact immutable index projection for one snapshot record map."""

    by_type: dict[str, set[str]] = defaultdict(set)
    by_dependency: dict[str, set[str]] = defaultdict(set)
    relation_by_instance: dict[str, set[str]] = defaultdict(set)
    relation_by_support: dict[str, set[str]] = defaultdict(set)
    relation_by_compatibility: dict[str, set[str]] = defaultdict(set)
    event_spec_by_relation: dict[str, set[str]] = defaultdict(set)
    by_generative_address: dict[str, set[str]] = defaultdict(set)
    generative_address_values: dict[str, Any] = {}
    by_topology_sheet: dict[str, set[str]] = defaultdict(set)
    definition_by_hash: dict[str, set[str]] = defaultdict(set)
    by_content_hash: dict[str, set[str]] = defaultdict(set)
    checkpoint_by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    time_intervals: list[dict[str, Any]] = []

    for record_id in sorted(records):
        object_hash = str(records[record_id])
        record = loader(record_id, object_hash)
        validate_record(record)
        if record["id"] != record_id or record["content_hash"] != object_hash:
            raise ValueError(f"record map/object mismatch while indexing: {record_id}")

        record_type = str(record["record_type"])
        payload = record["payload"]
        by_type[record_type].add(record_id)
        by_content_hash[object_hash].add(record_id)
        if record_type == "definition":
            definition_by_hash[object_hash].add(record_id)
        for dependency in record["dependencies"]:
            by_dependency[str(dependency)].add(record_id)

        if record_type == "relation":
            instance_id = str(payload["instance_id"])
            relation_by_instance[instance_id].add(record_id)
            for support_id in payload.get("support_ids", []):
                relation_by_support[str(support_id)].add(record_id)
            for compatibility_id in payload.get("compatibility_ids", []):
                relation_by_compatibility[str(compatibility_id)].add(record_id)
        elif record_type == "event_spec":
            event_spec_by_relation[str(payload["relation_id"])].add(record_id)
        elif record_type == "checkpoint":
            checkpoint_by_instance[str(payload["instance_id"])].append({
                "tick": int(payload["tick"]),
                "id": record_id,
                "content_hash": object_hash,
            })

        if "generative_address" in payload:
            key, compound = canonical_index_key(payload["generative_address"])
            by_generative_address[key].add(record_id)
            if compound is not None:
                existing = generative_address_values.get(key)
                if existing is not None and canonical_bytes(existing) != canonical_bytes(compound):
                    raise ValueError(f"generative-address digest collision: {key}")
                generative_address_values[key] = compound

        sheet = record_topology_sheet(record)
        if sheet is not None:
            by_topology_sheet[str(sheet)].add(record_id)

        interval = record_time_interval(record)
        if interval is not None:
            time_intervals.append({
                "start": interval[0],
                "end": interval[1],
                "id": record_id,
                "record_type": record_type,
            })

    time_intervals.sort(key=lambda item: (item["start"], item["end"], item["record_type"], item["id"]))
    checkpoints = {
        instance_id: sorted(items, key=lambda item: (item["tick"], item["id"]))
        for instance_id, items in sorted(checkpoint_by_instance.items())
    }
    record_map = {key: str(records[key]) for key in sorted(records)}
    index = attach_hash({
        "schema": INDEX_SCHEMA,
        "version": INDEX_VERSION,
        "seed_sha256": seed_sha256,
        "record_count": len(record_map),
        "records_map_hash": digest_bytes(canonical_bytes(record_map)),
        "indexes": {
            "by_type": _sorted_map_of_sets(by_type),
            "by_dependency": _sorted_map_of_sets(by_dependency),
            "relation_by_instance": _sorted_map_of_sets(relation_by_instance),
            "relation_by_support": _sorted_map_of_sets(relation_by_support),
            "relation_by_compatibility": _sorted_map_of_sets(relation_by_compatibility),
            "event_spec_by_relation": _sorted_map_of_sets(event_spec_by_relation),
            "by_generative_address": _sorted_map_of_sets(by_generative_address),
            "generative_address_values": {
                key: generative_address_values[key] for key in sorted(generative_address_values)
            },
            "time_intervals": time_intervals,
            "by_topology_sheet": _sorted_map_of_sets(by_topology_sheet),
            "definition_by_hash": _sorted_map_of_sets(definition_by_hash),
            "by_content_hash": _sorted_map_of_sets(by_content_hash),
            "checkpoint_by_instance": checkpoints,
        },
    })
    validate_index_record(index, records=record_map, seed_sha256=seed_sha256)
    return index


def validate_index_record(
    index: Mapping[str, Any],
    *,
    records: Mapping[str, str] | None = None,
    seed_sha256: str | None = None,
) -> None:
    if index.get("schema") != INDEX_SCHEMA:
        raise ValueError(f"index schema must be {INDEX_SCHEMA}")
    if index.get("version") != INDEX_VERSION:
        raise ValueError(f"index version must be {INDEX_VERSION}")
    if not verify_hash(index):
        raise ValueError("index content hash mismatch")
    if seed_sha256 is not None and index.get("seed_sha256") != seed_sha256:
        raise ValueError("index seed binding mismatch")
    indexes = index.get("indexes")
    if not isinstance(indexes, Mapping):
        raise ValueError("index indexes field must be an object")
    required = {
        "by_type", "by_dependency", "relation_by_instance", "relation_by_support",
        "relation_by_compatibility", "event_spec_by_relation", "by_generative_address",
        "generative_address_values", "time_intervals", "by_topology_sheet",
        "definition_by_hash", "by_content_hash", "checkpoint_by_instance",
    }
    missing = sorted(required - set(indexes))
    if missing:
        raise ValueError("index is missing fields: " + ", ".join(missing))
    if records is not None:
        canonical_map = {key: str(records[key]) for key in sorted(records)}
        if index.get("record_count") != len(canonical_map):
            raise ValueError("index record_count mismatch")
        if index.get("records_map_hash") != digest_bytes(canonical_bytes(canonical_map)):
            raise ValueError("index records_map_hash mismatch")


def ids_for(index: Mapping[str, Any], name: str, key: str) -> list[str]:
    values = index["indexes"].get(name, {})
    if not isinstance(values, Mapping):
        raise ValueError(f"index {name} is invalid")
    result = values.get(key, [])
    if not isinstance(result, list) or any(not isinstance(item, str) for item in result):
        raise ValueError(f"index {name}[{key!r}] is invalid")
    return list(result)


def interval_ids(
    index: Mapping[str, Any],
    start: int,
    end: int,
    *,
    record_type: str | None = None,
) -> list[str]:
    """Return IDs whose indexed inclusive interval overlaps ``[start,end]``."""

    _require_int(start, "interval start", minimum=0)
    _require_int(end, "interval end", minimum=0)
    if end < start:
        raise ValueError("interval end precedes start")
    entries = index["indexes"]["time_intervals"]
    if not isinstance(entries, list):
        raise ValueError("time_intervals index is invalid")
    starts = [int(item["start"]) for item in entries]
    limit = bisect_right(starts, end)
    result = {
        str(item["id"])
        for item in entries[:limit]
        if int(item["end"]) >= start and (record_type is None or item["record_type"] == record_type)
    }
    return sorted(result)


def checkpoint_entries(index: Mapping[str, Any], instance_id: str) -> list[dict[str, Any]]:
    mapping = index["indexes"].get("checkpoint_by_instance", {})
    if not isinstance(mapping, Mapping):
        raise ValueError("checkpoint_by_instance index is invalid")
    values = mapping.get(instance_id, [])
    if not isinstance(values, list):
        raise ValueError(f"checkpoint index for {instance_id} is invalid")
    return [dict(item) for item in values]
