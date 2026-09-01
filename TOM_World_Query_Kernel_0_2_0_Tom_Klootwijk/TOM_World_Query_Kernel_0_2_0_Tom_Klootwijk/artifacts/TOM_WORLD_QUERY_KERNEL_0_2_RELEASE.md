# TOM World & Query Kernel 0.2 — Completed Continuation

## Immutable indexes, deterministic plans, exact checkpoints, stable batches, and full ancestry audit

**Release:** 0.2.0  
**Date:** 2026-09-01  
**Underlying machine:** TOMAGI ABI 1.0  
**Canonical root:** `TOM_seed_genome_2026-09-01.txt`

## Result

This continuation completes Milestone 1B from the TOM AGI roadmap. The 0.1 world/query semantics remain authoritative; 0.2 adds reproducible acceleration and integrity layers around them.

```text
canonical seed
-> literal records and program blobs
-> exact stored transaction
-> immutable snapshot
-> immutable secondary indexes
-> indexed or exhaustive deterministic plan
-> exact TOMAGI replay and relation evaluation
-> semantic certificate
-> checkpoint/batch/event/lineage records
-> full ancestry audit
```

The implementation introduces no new TOMAGI opcode and changes no `State64`, `Cell48`, key, or `.tmg` layout.

## Delivered code

- `src/python/tom_world/indexes.py`
- `src/python/tom_world/planner.py`
- `src/python/tom_world/audit.py`
- checkpoint, batch, active-interval, and planned-query extensions in `query.py`
- exact transaction persistence and index-aware store extensions in `store.py`
- checkpoint/index validation in `records.py`
- new CLI operations in `cli.py`

## Immutable index set

The final snapshot carries content-addressed postings for record type, dependency, relation instance, support, compatibility, event-spec relation, generative address, topology sheet, definition hash, content hash, and checkpoint instance, plus sorted interval entries.

The record map remains authoritative. The release proves recovery by deleting the benchmark's final index file and reconstructing the exact bytes named by the immutable snapshot.

## Deterministic plans

Every plan records the commit, snapshot, index hash, mode, fixed stage sequence, keys, input/output counts, selected IDs/hash, and work counts. Indexed and exhaustive modes are deliberately both available. Their mechanics differ; their semantic results must match.

## Exact 10,000-record benchmark

The frozen literal population is:

| Record type | Count |
|---|---:|
| definition | 1 |
| supports | 16 |
| compatibility predicates | 4 |
| instances | 100 |
| exact relations | 9,600 |
| observations | 269 |
| checkpoints | 10 |
| **Total** | **10,000** |

The instances share an explicit one-cell TOMAGI trajectory. Each has 96 relation-zero events, partitioned over support and topology declarations.

Primary query:

```text
events_in_support(
    instance:benchmark:042,
    start=0,
    end=32,
    support=support:benchmark-bucket:04
)
```

Indexed candidate path:

```text
10,000 -> 9,600 -> 96 -> 6 -> 2
```

Returned event ticks:

```text
5, 21
```

The exhaustive plan returns byte-identical semantic result bytes.

## Checkpoint proof

Ten root-derived checkpoints are committed for instance 042 at ticks 0 through 900 in steps of 100.

For tick 999:

```text
root replay:        999 transitions
checkpoint replay:  99 transitions from tick 900
saved work:         900 transitions
terminal rho/tick:  999 / 999
semantic result:    byte-identical
```

A checkpoint is accepted only when its instance hash and program blob hash match the queried snapshot and its source commit is an ancestor.

## Stable batch proof

The shipped batch executes four requests in literal array order. Canonical semantic results are length-prefixed before reduction hashing. Indexed and exhaustive batches have equal semantic result hashes and equal semantic reduction hash. Plans and work counters remain visible and different.

## Audit proof

The benchmark audit clears caches and validates:

- descriptor and exact seed;
- both commit bytes and sequence/parent chain;
- both exact transaction bodies;
- both snapshots;
- both immutable indexes;
- byte-equal index reconstruction;
- every referenced record and dependency;
- the TOMAGI blob; and
- absence of unreachable immutable objects.

Result: valid, two commits, zero errors, zero orphans.

## Tests and validation

The release adds dedicated tests for:

- deterministic index identity;
- posting-list content;
- index deletion/rebuild;
- indexed/exhaustive event equality;
- checkpoint/root replay equality;
- stable batch reduction;
- ancestry audit;
- corruption detection;
- transaction/index preservation;
- exact benchmark population and candidate counts; and
- JSON schema validation.

The complete final test and validation counts are recorded in `validation/validation_report.json` and `validation/VALIDATION.md` after the clean rebuild.

## Causal documentation chain

This document is also delivered as a literal artifact:

```text
this exact Markdown source
-> content-addressed artifact definitions bound to the canonical seed
-> compiled .tmg EMIT graph
-> complete Python and C traces
-> generic byte materializer
-> byte-identical artifact/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md
```

No Markdown-specific materializer is used.

## What remains

0.2 is still exact-discrete. It does not certify a crossing between transition states, resolve simultaneous event sets, learn new definitions, consolidate memory, plan toward goals, ground raw perception, or govern external autonomous action.

The next release target is **0.3: certified interval/bracket event time and deterministic simultaneous-event semantics**.
