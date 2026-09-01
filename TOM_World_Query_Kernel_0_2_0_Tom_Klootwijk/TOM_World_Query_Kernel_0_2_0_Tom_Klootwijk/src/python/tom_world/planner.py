"""Deterministic query planning over immutable TOM world indexes."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .canonical import attach_hash, canonical_bytes, digest_bytes
from .indexes import checkpoint_entries, ids_for, interval_ids, record_time_interval
from .store import WorldStore

PLAN_SCHEMA = "TOM-QUERY-PLAN-0.2"
PLANNER_MODES = frozenset({"indexed", "exhaustive"})


def _intersect(current: Sequence[str], allowed: Sequence[str]) -> list[str]:
    allowed_set = set(allowed)
    return [ident for ident in current if ident in allowed_set]


def _stage(
    name: str,
    mechanism: str,
    before: Sequence[str] | int,
    after: Sequence[str],
    **detail: Any,
) -> dict[str, Any]:
    input_count = before if isinstance(before, int) else len(before)
    return {
        "name": name,
        "mechanism": mechanism,
        "input_count": input_count,
        "output_count": len(after),
        "detail": detail,
    }


def make_plan(
    *,
    commit: str,
    snapshot_hash: str,
    indexes_hash: str | None,
    mode: str,
    operation: str,
    stages: list[dict[str, Any]],
    selected_ids: Sequence[str],
    work: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    selected = list(selected_ids)
    return attach_hash({
        "schema": PLAN_SCHEMA,
        "version": "0.2.0",
        "commit": commit,
        "snapshot_hash": snapshot_hash,
        "indexes_hash": indexes_hash,
        "mode": mode,
        "operation": operation,
        "stages": stages,
        "selected_count": len(selected),
        "selected_ids_hash": digest_bytes(canonical_bytes(selected)),
        "selected_ids": selected,
        "work": {key: int(value) for key, value in sorted((work or {}).items())},
    })


class QueryPlanner:
    """Pure planner for one immutable commit.

    The planner may choose immutable secondary indexes or exhaustive record
    inspection.  Both modes return the same sorted semantic IDs.  Their plan
    certificates differ only in the declared mechanics and work counts.
    """

    def __init__(self, store: WorldStore, *, commit: str | None = None, mode: str = "indexed") -> None:
        if mode not in PLANNER_MODES:
            raise ValueError(f"planner mode must be one of {sorted(PLANNER_MODES)}")
        self.store = store
        self.commit = commit or store.head
        if self.commit is None:
            raise ValueError("query planner requires a committed world")
        self.commit_record = store.read_commit(self.commit)
        self.snapshot = store.read_snapshot(str(self.commit_record["snapshot_hash"]))
        self.mode = mode
        self.index = store.index_for_commit(self.commit) if mode == "indexed" else None
        if mode == "indexed" and self.index is None:
            # Deterministic fallback for legacy snapshots.  The computed index is
            # not attached to that immutable snapshot, so the plan declares it.
            self.index = store.compute_indexes(commit=self.commit)
            self.index_source = "computed_legacy_projection"
        else:
            self.index_source = "snapshot_immutable_index" if self.index is not None else "none"

    @property
    def indexes_hash(self) -> str | None:
        return str(self.index["content_hash"]) if self.index is not None else None

    def relation_ids(
        self,
        instance_id: str,
        *,
        explicit_ids: Sequence[str] | None = None,
        support_id: str | None = None,
        interval: tuple[int, int] | None = None,
        topology_sheet: int | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        stages: list[dict[str, Any]] = []
        records = {str(key): str(value) for key, value in self.snapshot["records"].items()}
        record_reads = 0

        if self.mode == "indexed":
            assert self.index is not None
            current = ids_for(self.index, "by_type", "relation")
            stages.append(_stage(
                "record_type",
                "immutable_index:by_type",
                len(records),
                current,
                key="relation",
                index_source=self.index_source,
            ))
            allowed = ids_for(self.index, "relation_by_instance", instance_id)
            before = current
            current = _intersect(current, allowed)
            stages.append(_stage(
                "instance",
                "immutable_index:relation_by_instance",
                before,
                current,
                key=instance_id,
            ))
            if support_id is not None:
                allowed = ids_for(self.index, "relation_by_support", support_id)
                before = current
                current = _intersect(current, allowed)
                stages.append(_stage(
                    "support",
                    "immutable_index:relation_by_support",
                    before,
                    current,
                    key=support_id,
                ))
            if interval is not None:
                allowed = interval_ids(self.index, interval[0], interval[1], record_type="relation")
                # Relations without an active/time interval remain candidates;
                # the interval index may eliminate only records that explicitly
                # declare a disjoint interval.
                indexed_interval_ids = {
                    str(entry["id"])
                    for entry in self.index["indexes"]["time_intervals"]
                    if entry["record_type"] == "relation"
                }
                allowed_set = set(allowed)
                before = current
                current = [ident for ident in current if ident not in indexed_interval_ids or ident in allowed_set]
                stages.append(_stage(
                    "time_interval",
                    "immutable_index:time_intervals",
                    before,
                    current,
                    start=interval[0],
                    end=interval[1],
                ))
            if topology_sheet is not None:
                allowed = ids_for(self.index, "by_topology_sheet", str(topology_sheet))
                before = current
                current = _intersect(current, allowed)
                stages.append(_stage(
                    "topology_sheet",
                    "immutable_index:by_topology_sheet",
                    before,
                    current,
                    key=topology_sheet,
                ))
        else:
            current = sorted(records)
            stages.append(_stage("snapshot", "exhaustive:snapshot_records", len(records), current))
            relations: list[str] = []
            for ident in current:
                record = self.store.read_record(ident, commit=self.commit)
                record_reads += 1
                if record["record_type"] == "relation":
                    relations.append(ident)
            stages.append(_stage("record_type", "exhaustive:read_and_filter", current, relations, key="relation"))
            current = relations

            selected: list[str] = []
            for ident in current:
                record = self.store.read_record(ident, commit=self.commit)
                record_reads += 1
                if record["payload"]["instance_id"] == instance_id:
                    selected.append(ident)
            stages.append(_stage("instance", "exhaustive:payload_filter", current, selected, key=instance_id))
            current = selected

            if support_id is not None:
                selected = []
                for ident in current:
                    record = self.store.read_record(ident, commit=self.commit)
                    record_reads += 1
                    if support_id in record["payload"].get("support_ids", []):
                        selected.append(ident)
                stages.append(_stage("support", "exhaustive:payload_filter", current, selected, key=support_id))
                current = selected

            if interval is not None:
                selected = []
                for ident in current:
                    record = self.store.read_record(ident, commit=self.commit)
                    record_reads += 1
                    declared = record_time_interval(record)
                    if declared is None or (declared[0] <= interval[1] and declared[1] >= interval[0]):
                        selected.append(ident)
                stages.append(_stage(
                    "time_interval", "exhaustive:payload_filter", current, selected,
                    start=interval[0], end=interval[1],
                ))
                current = selected

            if topology_sheet is not None:
                selected = []
                for ident in current:
                    record = self.store.read_record(ident, commit=self.commit)
                    record_reads += 1
                    if record["payload"].get("topology_sheet") == topology_sheet:
                        selected.append(ident)
                stages.append(_stage(
                    "topology_sheet", "exhaustive:payload_filter", current, selected, key=topology_sheet,
                ))
                current = selected

        if explicit_ids is not None:
            requested = sorted(set(str(value) for value in explicit_ids))
            before = current
            current = _intersect(current, requested)
            stages.append(_stage(
                "explicit_ids", "declared_intersection", before, current,
                requested_count=len(requested), requested_ids_hash=digest_bytes(canonical_bytes(requested)),
            ))

        current = sorted(current)
        plan = make_plan(
            commit=self.commit,
            snapshot_hash=str(self.snapshot["content_hash"]),
            indexes_hash=self.indexes_hash,
            mode=self.mode,
            operation="select_relations",
            stages=stages,
            selected_ids=current,
            work={"record_reads": record_reads, "index_lookups": sum(
                1 for stage in stages if stage["mechanism"].startswith("immutable_index:")
            )},
        )
        return current, plan

    def checkpoint_ids(self, instance_id: str, target_tick: int) -> tuple[list[str], dict[str, Any]]:
        if isinstance(target_tick, bool) or not isinstance(target_tick, int) or target_tick < 0:
            raise ValueError("target_tick must be a nonnegative integer")
        stages: list[dict[str, Any]] = []
        record_reads = 0
        records = {str(key): str(value) for key, value in self.snapshot["records"].items()}
        candidates: list[tuple[int, str]] = []

        if self.mode == "indexed":
            assert self.index is not None
            entries = checkpoint_entries(self.index, instance_id)
            ids = [str(entry["id"]) for entry in entries]
            stages.append(_stage(
                "instance_checkpoints",
                "immutable_index:checkpoint_by_instance",
                int(self.index["record_count"]),
                ids,
                key=instance_id,
            ))
            for entry in entries:
                tick = int(entry["tick"])
                if tick <= target_tick:
                    candidates.append((tick, str(entry["id"])))
        else:
            all_ids = sorted(records)
            checkpoint_ids: list[str] = []
            for ident in all_ids:
                record = self.store.read_record(ident, commit=self.commit)
                record_reads += 1
                if record["record_type"] == "checkpoint" and record["payload"]["instance_id"] == instance_id:
                    checkpoint_ids.append(ident)
                    tick = int(record["payload"]["tick"])
                    if tick <= target_tick:
                        candidates.append((tick, ident))
            stages.append(_stage(
                "instance_checkpoints", "exhaustive:read_and_filter", all_ids, checkpoint_ids, key=instance_id,
            ))

        candidates.sort(key=lambda item: (item[0], item[1]))
        eligible = [ident for _, ident in candidates]
        selected = [eligible[-1]] if eligible else []
        stages.append(_stage(
            "nearest_not_after",
            "deterministic:max_tick_then_id",
            eligible,
            selected,
            target_tick=target_tick,
            selected_tick=candidates[-1][0] if candidates else None,
        ))
        plan = make_plan(
            commit=self.commit,
            snapshot_hash=str(self.snapshot["content_hash"]),
            indexes_hash=self.indexes_hash,
            mode=self.mode,
            operation="select_checkpoint",
            stages=stages,
            selected_ids=selected,
            work={"record_reads": record_reads, "index_lookups": 1 if self.mode == "indexed" else 0},
        )
        return selected, plan
