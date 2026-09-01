# Immutable Index and Deterministic Query-Plan Profile

## Authority

A world snapshot's `records` and `blobs` maps are authoritative. `indexes_hash` names a content-addressed projection of those records. Index deletion is recoverable; record deletion is not.

## Shipped indexes

```text
by_type
by_dependency
relation_by_instance
relation_by_support
relation_by_compatibility
event_spec_by_relation
by_generative_address
time_intervals
by_topology_sheet
definition_by_hash
by_content_hash
checkpoint_by_instance
```

Posting lists and entries are sorted deterministically. No score, learned cost, ambient statistics, or wall-clock data influences a 0.2 plan.

## Indexed relation plan

```text
all snapshot records
-> relation type posting
-> instance posting
-> optional support posting
-> optional interval overlap
-> optional topology sheet posting
-> optional explicit relation IDs
```

Every stage records input count, output count, mechanism, and key. Exhaustive mode applies the same semantic filter order by reading records.

## Benchmark result

The 10,000-record world produces this exact candidate path for the primary support query:

```text
10,000 -> 9,600 -> 96 -> 6 -> 2
```

Events occur at logical ticks 5 and 21. Indexed and exhaustive semantic result bytes are equal. The indexed plan performs immutable posting-list lookups; the exhaustive plan records direct object reads.

## Rebuild

`rebuild_indexes` derives a fresh index from the immutable snapshot, requires its content hash to equal the snapshot's `indexes_hash`, and writes only after equality. The benchmark deletes the final index file, rebuilds it, and confirms byte equality.
