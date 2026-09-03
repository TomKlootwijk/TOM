"""Event-driven continuation engine for the corrective 0.4 rebuild."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from tom_world03.canonical import attach_hash, canonical_bytes

from .model import ContinuationWorld, OpenSegment, qmap_record
from .solver import next_event_set
from .transition import EventBundle, FinalizationBundle, apply_event_set, finalize_segment


@dataclass(frozen=True, slots=True)
class ContinuationRun:
    record: Mapping[str, Any]
    open_segments: tuple[OpenSegment, ...]
    bundles: tuple[EventBundle, ...]
    finalization: FinalizationBundle


def _semantic_chain(
    world: ContinuationWorld,
    open_segments: list[OpenSegment],
    bundles: list[EventBundle],
    finalization: FinalizationBundle,
) -> dict[str, Any]:
    realized_segments: list[dict[str, Any]] = []
    for segment, bundle in zip(open_segments, bundles):
        realized_segments.append({
            "sequence": segment.sequence,
            "domain": bundle.seal["realized_domain"],
            "start_state": qmap_record(segment.start_state),
            "rates": qmap_record(segment.rates),
            "end_state": bundle.seal["end_state"],
        })
    final_segment = open_segments[-1]
    realized_segments.append({
        "sequence": final_segment.sequence,
        "domain": finalization.seal["realized_domain"],
        "start_state": qmap_record(final_segment.start_state),
        "rates": qmap_record(final_segment.rates),
        "end_state": finalization.seal["end_state"],
    })

    event_sets = [
        {
            "event_time": bundle.event_set["event_time"],
            "event_order": list(bundle.event_set["event_order"]),
            "relation_order": list(bundle.event_set["relation_order"]),
            "pre_state": bundle.transition["pre_state"],
            "post_state": bundle.transition["post_state"],
            "pre_rates": bundle.transition["pre_rates"],
            "post_rates": bundle.transition["post_rates"],
            "fired_relations_after": list(bundle.successor.fired_relations),
        }
        for bundle in bundles
    ]
    return {
        "schema": "TOM-CONTINUATION-SEMANTIC-CHAIN-0.4.1",
        "world_hash": world.content_hash,
        "corrected_v03_zip_sha256": world.corrected_v03_zip_sha256,
        "corrected_interval_sha256": world.corrected_interval_sha256,
        "realized_segments": realized_segments,
        "event_sets": event_sets,
        "final_time": world.horizon.upper.to_record(),
        "final_state": finalization.transaction["final_state"],
        "fired_relations": list(final_segment.fired_relations),
        "boundary_policy": "event times are solver outputs; final boundary is the declared world horizon",
    }


def run_continuation(
    world: ContinuationWorld,
    *,
    planner: str = "indexed",
    max_event_sets: int | None = None,
    store: Any | None = None,
) -> ContinuationRun:
    max_sets = int(world.solver.get("max_event_sets", 64) if max_event_sets is None else max_event_sets)
    profile_max = int(world.solver.get("profile_max_event_sets", 1024))
    if max_sets < 0 or max_sets > profile_max:
        raise ValueError(f"max_event_sets {max_sets} outside 0..{profile_max}")

    current = world.initial_segment
    open_segments: list[OpenSegment] = [current]
    bundles: list[EventBundle] = []
    query_certificates: list[Mapping[str, Any]] = []
    while True:
        event_set = next_event_set(world, current, planner=planner)
        query_certificates.append(event_set)
        if event_set["status"] == "none":
            finalization = finalize_segment(world, current)
            if store is not None:
                store.commit_finalization(finalization)
            break
        if len(bundles) >= max_sets:
            raise ValueError("event-set budget exhausted before world horizon")
        bundle = apply_event_set(world, current, event_set)
        if store is not None:
            store.commit_event(bundle)
        bundles.append(bundle)
        current = bundle.successor
        open_segments.append(current)

    semantic = _semantic_chain(world, open_segments, bundles, finalization)
    semantic_hash = "sha256:" + hashlib.sha256(canonical_bytes(semantic)).hexdigest()
    record = attach_hash({
        "schema": "TOM-CONTINUATION-RUN-0.4.1",
        "world_hash": world.content_hash,
        "planner": planner,
        "status": "complete",
        "stop_reason": "no-later-event-and-horizon-sealed",
        "event_set_count": len(bundles),
        "realized_segment_count": len(open_segments),
        "open_segment_hashes": [segment.content_hash for segment in open_segments],
        "event_set_hashes": [bundle.event_set["content_hash"] for bundle in bundles],
        "transition_hashes": [bundle.transition["content_hash"] for bundle in bundles],
        "seal_hashes": [bundle.seal["content_hash"] for bundle in bundles] + [finalization.seal["content_hash"]],
        "transaction_hashes": [bundle.transaction["content_hash"] for bundle in bundles] + [finalization.transaction["content_hash"]],
        "query_certificate_hashes": [record["content_hash"] for record in query_certificates],
        "total_scanned_brackets": sum(int(record["scanned_brackets"]) for record in query_certificates),
        "total_candidate_relations": sum(int(record["total_candidate_relations"]) for record in query_certificates),
        "semantic_chain": semantic,
        "semantic_chain_sha256": semantic_hash,
        "journal_head": None if store is None else store.head,
    })
    return ContinuationRun(record, tuple(open_segments), tuple(bundles), finalization)
