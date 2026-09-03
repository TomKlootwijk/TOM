# TOM World & Query Kernel 0.2

## Immutable index, deterministic query-plan, checkpoint, batch, and audit profile

**Normative identifier:** `TOM-WORLD-QUERY-KERNEL-0.2`  
**Version:** `0.2.0`  
**Underlying machine:** TOMAGI ABI 1.0  
**Root genome:** `TOM_seed_genome_2026-09-01.txt`  
**Date:** 2026-09-01

## 1. Purpose

Version 0.2 continues the query-first world layer introduced in 0.1. It does not change the semantic meaning of the native exact-discrete queries. It adds deterministic access structures and replay acceleration whose results can be checked against exhaustive evaluation.

The normative chain is:

```text
canonical seed
-> content-addressed records and blobs
-> immutable transaction
-> immutable snapshot
-> immutable secondary-index projection
-> deterministic query plan
-> exact TOMAGI state/event evaluation
-> canonical semantic certificate
-> optional committed checkpoint/event/lineage
-> full ancestry audit
```

The authoritative world remains the snapshot's record and blob maps. An index is a reproducible projection. Deleting an index MUST NOT destroy world meaning; rebuilding it from the referenced snapshot MUST reproduce its declared content hash and bytes.

## 2. Compatibility

This profile preserves:

- the canonical 244-byte TOM seed and its SHA-256;
- the TOMAGI 1.0 128-byte header, 64-byte `State64`, 48-byte `Cell48`, sixteen opcodes, and `.tmg` version;
- the 0.1 world record, transaction, snapshot, and commit schema identifiers;
- the 0.1 event-certificate and reconstruction semantics;
- exact-discrete transition-count meaning for `state_at(t)`; and
- the 0.1 native query set.

New 0.2 objects are distinguished by their own versioned schema identifiers. Existing 0.1 stores remain readable. A legacy snapshot without an `indexes_hash` MAY be queried through a deterministic computed index projection, but the plan MUST declare that the index was not attached to the snapshot.

## 3. World-store authority

A 0.2 store contains:

```text
store.json       content-addressed descriptor
seed.bin         exact canonical seed bytes
objects/         content-addressed world records
blobs/           content-addressed binary programs/data
transactions/    exact committed transaction bodies
indexes/         immutable secondary-index projections
snapshots/       immutable ID -> content-hash maps plus indexes_hash
commits/         append-only ancestry records
HEAD             the only mutable pointer
```

Commit publication order is:

1. validate the canonical seed and transaction content hash;
2. validate transaction sequence and base commit;
3. validate records, dependencies, references, and blobs;
4. write immutable blobs and records;
5. build and write the immutable index projection;
6. write the snapshot referencing that index;
7. write the exact transaction body;
8. write the commit referencing transaction, snapshot, and index; and
9. atomically replace `HEAD`.

A crash before step 9 may leave unreachable immutable objects. It MUST NOT expose a partially committed snapshot through `HEAD`.

## 4. Content-addressed records

The 0.1 record envelope remains:

```text
schema, record_type, id, version, dependencies,
payload, provenance, content_hash
```

Version 0.2 adds the record type `checkpoint`. Existing types are unchanged.

### 4.1 Indexable optional fields

Records MAY expose these payload fields:

- `generative_address`: scalar or finite JSON value;
- `time_interval` or `active_interval`: `{start,end}`, both nonnegative and `end >= start`;
- `topology_sheet`: unsigned 32-bit integer.

Relations already expose `instance_id`, `support_ids`, `compatibility_ids`, and optional `event_spec_id`. Event specifications expose `relation_id`. These declared fields form index keys; the indexer does not infer semantic keys from free text.

### 4.2 Checkpoint record

A checkpoint payload MUST contain:

```text
instance_id
logical tick
executed_steps
complete 16-field State64 mapping
instance_hash
program_blob_hash
source_commit
state_certificate_hash
topology_sheet
generative_address
time_interval
```

The checkpoint MUST be produced by exact replay from the instance root state with checkpoints disabled. Its `source_commit` MUST be an ancestor of any query commit that consumes it. Its stored instance and program hashes MUST match the queried snapshot. It is an acceleration record, not a replacement world state.

## 5. Immutable secondary index

The index schema is `TOM-WORLD-INDEXES-0.2`. It binds to:

- profile version 0.2.0;
- canonical seed hash;
- exact record count; and
- SHA-256 of the canonical sorted snapshot record map.

It contains these projections:

| Index | Key -> posting/entry meaning |
|---|---|
| `by_type` | record type -> sorted record IDs |
| `by_dependency` | dependency ID -> records that depend on it |
| `relation_by_instance` | instance ID -> relation IDs |
| `relation_by_support` | support ID -> relation IDs |
| `relation_by_compatibility` | compatibility ID -> relation IDs |
| `event_spec_by_relation` | relation ID -> event-spec IDs |
| `by_generative_address` | canonical address key -> record IDs |
| `generative_address_values` | compound-address digest -> original canonical value |
| `time_intervals` | sorted interval records `{start,end,id,record_type}` |
| `by_topology_sheet` | decimal sheet value -> record IDs |
| `definition_by_hash` | definition content hash -> definition IDs |
| `by_content_hash` | object hash -> logical record IDs |
| `checkpoint_by_instance` | instance ID -> sorted checkpoint descriptors |

All posting lists are sorted, duplicate-free arrays. Map keys are emitted in canonical order. Interval entries are sorted by `(start,end,record_type,id)`. Checkpoints are sorted by `(tick,id)`.

### 5.1 Compound generative addresses

String, integer, boolean, and null addresses receive typed readable index keys. Compound JSON addresses are keyed by:

```text
json:SHA256(canonicalJSON(address))
```

The original canonical value is stored once in `generative_address_values`. If two unequal canonical values produce one digest, index construction MUST reject the collision.

### 5.2 Rebuild theorem

For immutable snapshot record map `M`, canonical seed hash `h`, and deterministic record loader `L`:

```text
I = BuildIndex(M,L,h)
```

is a pure function. If a stored index referenced by the snapshot is absent, `rebuild_indexes` MUST recompute `I`, require `I.content_hash == snapshot.indexes_hash`, and only then write it. Any mismatch is corruption or implementation nonconformance.

## 6. Deterministic query planning

A plan uses schema `TOM-QUERY-PLAN-0.2`. It records:

```text
commit
snapshot_hash
indexes_hash
mode
operation
ordered stages
selected_count
selected_ids
selected_ids_hash
work counters
content_hash
```

Planner modes are:

- `indexed`: use immutable posting lists and interval entries;
- `exhaustive`: inspect the snapshot record map and payloads directly.

Both modes MUST return the same sorted semantic candidate IDs. Their plan certificates are expected to differ.

### 6.1 Relation-selection order

The normative indexed stage order is:

```text
record type
-> instance
-> optional support
-> optional time interval
-> optional topology sheet
-> optional explicit-ID intersection
```

Each stage records mechanism, input count, output count, and declared key/details. The order is fixed rather than cost-based in 0.2, so identical snapshots and requests produce identical plan bytes.

Relations without an explicit active/time interval remain eligible for an interval query. The interval index may eliminate only relations that explicitly declare a disjoint interval.

### 6.2 Exhaustive baseline

The exhaustive planner:

1. starts from all sorted snapshot IDs;
2. reads and filters by record type;
3. reads relation payloads and filters by instance;
4. applies support, interval, sheet, and explicit-ID filters in the same semantic order.

It records exact record-read counts. It is a correctness baseline, not the desired scale path.

## 7. Checkpoint-aware `state_at`

`state_at(instance,t)` retains its semantic result: the complete state after exactly `t` logical TOMAGI transitions from the instance root, or earlier halt according to the existing machine semantics.

When checkpoints are enabled:

1. select all checkpoint entries for the instance;
2. retain entries with `tick <= t`;
3. choose maximum tick, breaking ties by checkpoint ID;
4. validate checkpoint instance hash, program blob hash, and ancestry;
5. start from the checkpoint state; and
6. execute the remaining transitions.

The semantic certificate is independent of the chosen plan. The plan records:

```text
checkpoint_tick
checkpoint_id
logical_steps
replayed_steps
executed_steps
saved_replay_steps
TOMAGI-step work
```

A root replay with checkpoints disabled MUST produce byte-identical semantic certificate data for the same immutable world and request.

## 8. Event queries

The 0.1 exact-discrete event condition remains authoritative. For each logical tick in the declared finite horizon:

1. execute one TOMAGI transition unless halted;
2. ignore relations outside their explicit active interval;
3. evaluate relation residual at pre-state and current state;
4. evaluate all declared support predicates;
5. evaluate all declared compatibility predicates;
6. apply the declared zero test and trigger mode;
7. construct event candidates; and
8. order simultaneous candidates by relation priority then relation ID.

`next_event` returns the first candidate in this deterministic order. `events_in_support` returns all candidates over `(start_tick,end_tick]`.

The scan plan records selected relations, ticks scanned, relation and predicate evaluations, inactive-interval skips, events found, state replay, and candidate-selection plan.

## 9. Stable batch queries

The batch schema is `TOM-BATCH-QUERY-CERTIFICATE-0.2`. Requests are evaluated strictly in their declared JSON array order. Each request requires a unique ID, operation, and parameter object.

Supported operations are:

```text
state_at
next_event
events_in_support
compatible
definition_at
```

For each semantic result, canonical JSON bytes are prefixed with an unsigned little-endian 64-bit byte length. The concatenation in declared order is hashed:

```text
semantic_reduction_hash = SHA256(
    len64(result_0) || canonical(result_0) ||
    ... ||
    len64(result_n) || canonical(result_n)
)
```

Indexed and exhaustive batches MUST have equal semantic result hashes and equal semantic reduction hashes for the same world and requests, although their plans and work counters differ.

## 10. Full ancestry and corruption audit

The audit schema is `TOM-WORLD-AUDIT-CERTIFICATE-0.2`. An audit clears in-process caches, then validates the target commit and every ancestor to sequence zero.

For each commit it verifies:

- content-addressed commit bytes and sequence continuity;
- parent relationship and seed binding;
- exact stored transaction body and transaction/commit metadata agreement;
- content-addressed snapshot and seed binding;
- content-addressed immutable index and commit/snapshot index agreement;
- byte-equal index reconstruction from snapshot records;
- every referenced record object and dependency;
- every referenced blob; and
- root/non-root parent conditions.

It reports all reachable immutable identifiers, record-type counts across snapshots, errors, warnings, and unreachable immutable objects. `require_no_orphans` turns any unreachable immutable object into an error.

The audit certificate contains no hostname, PID, duration, absolute path, or clock value. Repeated audits of identical store bytes produce the same certificate hash.

## 11. Caching boundary

Content-addressed immutable objects MAY be cached in memory by hash. Such caching MUST NOT change query semantics or plan counts. A disk-integrity audit MUST clear caches before reading and verifying stored bytes. Corruption testing MUST use uncached disk reads.

## 12. The 10,000-record benchmark

The normative benchmark is `TOM-INDEX-BENCHMARK-10000-0.2`.

### 12.1 Population

Initial transaction: 9,990 records.

| Type | Count |
|---|---:|
| definition | 1 |
| support | 16 |
| compatibility | 4 |
| instance | 100 |
| relation | 9,600 |
| observation | 269 |
| **Initial total** | **9,990** |

Second transaction adds ten exact checkpoints at ticks 0,100,...,900 for `instance:benchmark:042`, producing exactly 10,000 records.

Each instance runs the same one-cell TOMAGI linear trajectory with `vrho=1` and `vtick=1`. Each of its 96 relations is zero exactly when `rho` reaches target 1 through 96. Relations are partitioned over sixteen support IDs and four topology-compatible sheet IDs. Each relation declares an exact one-tick active interval.

### 12.2 Candidate reduction acceptance

For:

```text
events_in_support(
  instance:benchmark:042,
  interval=(0,32],
  support=support:benchmark-bucket:04
)
```

the indexed plan MUST record:

```text
10,000 total records
-> 9,600 relations
-> 96 relations for the instance
-> 6 relations in support bucket 04
-> 2 interval-overlapping relations
```

The semantic result contains events at ticks 5 and 21. The exhaustive plan MUST return byte-identical semantic result bytes.

### 12.3 Checkpoint acceptance

For `state_at(instance:benchmark:042,999)`:

- indexed replay selects the checkpoint at tick 900 and executes 99 transitions;
- root replay executes 999 transitions;
- both return `rho=999`, `tick=999`; and
- semantic certificate bytes are equal.

### 12.4 Additional acceptance

- batch semantic reduction hashes are equal across planner modes;
- deleting the referenced final index and rebuilding it reproduces exact bytes;
- the full two-commit ancestry audit passes with zero errors and zero orphans;
- the final store record count is exactly 10,000.

Performance claims in 0.2 are deterministic work-count claims, not wall-clock claims. Runtime duration is deliberately excluded from certificates because it depends on hardware and filesystem conditions.

## 13. Resource and claim boundary

Version 0.2 implements an indexed exact-discrete world kernel. It does not implement:

- continuous or interval-certified root solving;
- adaptive learned query planning;
- distributed or concurrent multi-writer consensus;
- automatic knowledge induction;
- semantic memory consolidation;
- general planning or tool use;
- multimodal grounding;
- autonomous governance; or
- AGI.

The next normative milestone is 0.3: typed interval/bracket relations, rational event-time certificates, simultaneous-event sets, and trusted-baseline comparison.

## 14. Determinism theorem

For fixed canonical seed, immutable commit, request bytes, planner mode, checkpoint policy, query budgets, and TOMAGI program bytes:

1. record and index identity is fixed by canonical JSON and SHA-256;
2. posting lists and interval entries have fixed sort orders;
3. query stages have fixed order and exact declared keys;
4. checkpoint selection has a total `(tick,id)` order;
5. TOMAGI replay is fixed by the 1.0 integer machine;
6. relation and gate expressions are bounded and side-effect free;
7. event candidate order is `(priority,id)`; and
8. batch reduction is length-prefixed declared-array order.

Therefore the plan, semantic certificate, batch reduction, and audit certificate are deterministic functions of their declared inputs. Indexed and exhaustive plans may differ, but a conforming implementation must prove equality of the semantic certificates on the validated domain.

---

**End of TOM World & Query Kernel 0.2 normative profile.**
