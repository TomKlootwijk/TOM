# TOM World & Query Kernel 0.1

## Normative persistent-world and exact-discrete-query profile over TOMAGI 1.0

**Profile ID:** `TOM-WORLD-QUERY-KERNEL-0.1`  
**Underlying execution ABI:** TOMAGI 1.0  
**Canonical root:** `TOM_seed_genome_2026-09-01.txt`  
**Release date:** 2026-09-01

## 1. Scope

This profile begins the world/query layer described by TOM-SRS 1.0. It provides:

- a persistent content-addressed world store;
- immutable record, blob, snapshot, and commit objects;
- exact TOMAGI state replay;
- typed bounded relation, support, and compatibility expressions;
- exact finite-horizon discrete event scanning;
- event and transition certificates;
- append-only event and lineage commits;
- byte-equal reconstruction;
- bounded branch-selected grammar expansion; and
- literal definition to TOMAGI EMIT byte artifacts.

This release does not define a continuous numerical root solver, autonomous learner, planner, perception system, action system, distributed consensus protocol, or AGI.

The terms MUST, MUST NOT, REQUIRED, SHALL, SHOULD, and MAY are normative.

## 2. Source authority

The canonical TOM seed MUST be exactly 244 ASCII bytes, MUST have no terminal CR or LF, and MUST have SHA-256:

```text
d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5
```

Every store and transaction MUST bind to `sha256:` followed by that digest. Seed verification occurs before a store is initialized or a transaction is accepted.

TOMAGI 1.0 remains the machine authority. This profile does not change the 128-byte header, 64-byte `State64`, 48-byte `Cell48`, sixteen opcode numbers, key codecs, or fixed-width transition equations.

## 3. Deterministic JSON and hashes

Canonical JSON is:

```text
UTF8(json(value, sort_keys=true, ensure_ascii=false,
          separators=(",", ":"), allow_nan=false))
```

For a mapping `r`, its content identity is:

```text
content_hash(r) = "sha256:" + SHA256(canonicalJSON(r without top-level content_hash))
```

Hexadecimal is lower-case. Content-addressed records, store descriptors, transactions, snapshots, commits, event certificates, grammar certificates, and reconstruction certificates use this rule.

Blob identities are `sha256:` plus SHA-256 of the literal blob bytes.

## 4. Store object

A store directory contains:

```text
store.json
seed.bin
HEAD
objects/<digest>.json
blobs/<digest>.bin
snapshots/<digest>.json
commits/<digest>.json
```

`store.json` is a content-addressed descriptor naming profile version, seed identity, hash algorithm, and canonical JSON profile. `seed.bin` MUST contain the exact canonical seed.

Immutable JSON objects are written as canonical JSON bytes. Their filenames use the 64 hexadecimal characters after `sha256:`. Blobs contain literal bytes.

`HEAD` is the only mutable semantic pointer. It contains one commit hash plus LF or is absent before the first commit.

## 5. Atomic commit protocol

A transaction has schema `TOM-WORLD-TRANSACTION-0.1` and contains:

```text
seed_sha256
base_commit
sequence
message
records[]
blobs[]
provenance
content_hash
```

A conforming local commit implementation SHALL:

1. verify the store descriptor and seed;
2. verify the transaction content hash and seed binding;
3. acquire an exclusive commit lock;
4. require `base_commit` to equal current `HEAD`;
5. require sequence zero for the first commit, otherwise parent sequence plus one;
6. verify staged records and deterministic dependency order;
7. verify every staged blob's literal SHA-256;
8. validate type-specific references against the prospective snapshot;
9. write immutable blobs and records;
10. write a content-addressed snapshot;
11. write a content-addressed commit; and
12. atomically replace `HEAD` last.

A failure before step 12 MUST NOT publish a new world head.

## 6. Snapshot and commit

A snapshot has schema `TOM-WORLD-SNAPSHOT-0.1` and contains sorted mappings:

```text
records: record_id -> record_content_hash
blobs:   logical_blob_id -> literal_blob_hash
```

A commit has schema `TOM-WORLD-COMMIT-0.1` and contains:

```text
version
seed_sha256
sequence
parent
transaction_hash
snapshot_hash
message
provenance
content_hash
```

Commit and snapshot objects are immutable. Historical queries select a commit hash and therefore see an immutable snapshot.

## 7. Record contract

Every world record has schema `TOM-WORLD-RECORD-0.1` and fields:

```text
record_type
id
version
dependencies[]
payload
provenance
content_hash
```

IDs MUST match:

```text
[A-Za-z0-9][A-Za-z0-9._:/@+-]*
```

Dependencies MUST be unique. Within a transaction, dependencies must either exist in the base snapshot or appear in the staged acyclic dependency graph.

The 0.1 record types are:

- `definition`;
- `instance`;
- `relation`;
- `support`;
- `compatibility`;
- `transition`;
- `event_spec`;
- `grammar`;
- `observation`;
- `hypothesis`;
- `goal`;
- `policy`;
- `event`; and
- `lineage`.

Observation and hypothesis records do not become verified definitions merely because they are stored. Authority is determined by record type, explicit status, evidence, and later acceptance policy.

## 8. Definition records

A definition payload MUST name:

```text
kind
domain
codomain
operation
phase
order
```

The allowed phases are:

```text
parse, normalize, resolve, construct, transform,
support, compatibility, guard, transition, lineage
```

A definition MAY declare parameters, capabilities, invariants, and source evidence. This release stores these declarations but does not yet execute a general high-level definition compiler for every world record. TOMAGI program behavior remains present in literal `.tmg` source/blob inputs.

## 9. Instance records and state replay

An instance payload MUST name `program_blob_id`, which resolves through the selected snapshot to a valid `.tmg` blob. It MAY override any subset of the sixteen initial `State64` fields and MAY contain literal context.

For instance `x`, `state_at(x,n)` means:

- `n` is a nonnegative count of complete TOMAGI transitions;
- state at zero is the selected initial state;
- state at `n` is obtained by running the selected program for at most `n` transitions, stopping earlier only when TOMAGI halt semantics do so;
- the result certificate names commit, instance ID/hash, requested index, executed steps, state, and status.

The state index is distinct from the stored modular `tick` field, although a program may advance them equally as the starter example does.

`trace(x,n)` is `state_at` plus every TOMAGI transition record.

## 10. Bounded expression language

World relations and gates use a side-effect-free expression tree. Evaluation has explicit node and depth budgets. It performs no I/O, clock access, randomness, import, process execution, or arbitrary code evaluation.

### 10.1 Sources

A `field` expression selects a named source and path. Query contexts may expose:

```text
state
pre_state
left
right
context
event
```

A missing source or field is an error.

### 10.2 Atomic and arithmetic operations

The 0.1 operations are:

```text
const
field
add sub mul floor_div mod
abs neg max min
eq ne lt le gt ge
all any not if
cyclic_delta
interval contains_zero in_closed_interval
bit
```

Arithmetic inputs MUST be integers, not booleans. Arithmetic results MUST fit signed 64-bit range or evaluation fails. Division and modulo by zero fail. `cyclic_delta(value,center,period)` requires a positive integer period and returns the deterministic shortest signed modular difference.

An interval is an object `{lower,upper}` with integer `lower <= upper`.

## 11. Support and compatibility

A support record contains a boolean expression evaluated against the candidate state and context. A relation's support list is evaluated in declared order. All entries must return true.

A compatibility record also contains a boolean expression. During event solving it sees current/pre-state and context. During `compatible(left,right,tick)` it sees exact left and right states at the same replay index plus supplied context.

Support and compatibility are explicit candidate gates. They are not hidden runtime correction mechanisms.

## 12. Relation record

A relation payload MUST contain:

```text
instance_id
expression
```

It MAY contain:

```text
zero_test
trigger
support_ids[]
compatibility_ids[]
event_spec_id
priority
zero_relation
```

`zero_test` is one of:

- `equal_zero`: integer residual equals zero;
- `less_equal_zero`: integer residual is nonpositive;
- `contains_zero`: interval contains zero.

`trigger` is one of:

- `zero`;
- `enter_zero`;
- `crossing`; or
- `enter_nonpositive`.

`SDF0@Def` is represented as typed `zero_relation` metadata describing domain, codomain, and zero locus. It does not imply that all stored values are numerically zero.

## 13. Exact discrete event solver

`next_event(instance,t0,horizon,relations,context)` scans exact replay indices:

```text
t = t0 + 1 ... t0 + horizon
```

At each index it:

1. retains the pre-state;
2. executes at most one TOMAGI transition;
3. evaluates candidate relations ordered by integer priority then ID;
4. evaluates every declared support;
5. evaluates every declared compatibility predicate;
6. evaluates relation residual at pre-state and event-state;
7. applies the declared zero and trigger tests;
8. creates candidate event certificates; and
9. returns the first passing candidate at the earliest index.

If no candidate passes within the finite horizon, the result is `null`.

This is an exact discrete scanner. It makes no claim about a relation zero between two replay indices unless a later profile supplies a bracket/interpolation/interval policy.

## 14. Event certificate

A certificate has schema `TOM-EVENT-CERTIFICATE-0.1` and records at least:

```text
source_commit
query
instance_hash
event_tick
relation_id/hash
event_spec_id/hash
transition_id/hash
previous_residual
residual
zero_test
trigger
direction
guard_margin
support decisions
compatibility decisions
solver_status
confidence
route
pre_state
event_state
post_state
context
content_hash
```

The solver status in 0.1 is `exact_discrete_scan`. Confidence is explicit source data. The kernel does not derive or enforce a hidden confidence threshold.

## 15. Transition

A transition payload contains one or more of:

```text
set
add
xor
```

Each mapping selects `State64` fields and bounded expressions. Field application order is operation order (`set`, then `add`, then `xor`) and lexicographic field name within each mapping.

Periodic normalization, when enabled, applies TOMAGI moduli to theta, tick, and phi and masks orientation and branch to one bit.

An optional integer `lineage_salt` updates the post-state lineage with TOMAGI `mix32`, event index, and relation hash word. This is a deterministic compact lineage contribution, not a cryptographic proof.

## 16. Event and lineage persistence

A verified certificate may be converted to:

- one `event` record embedding the certificate and naming the relation/route; and
- one `lineage` record embedding the certificate, event ID, pre/post lineage values, and definition hashes.

Their IDs derive from the certificate hash prefix. A commit transaction appends them without modifying prior objects.

## 17. Reconstruction

`reconstruct(certificate)` SHALL:

1. verify the certificate content hash;
2. select its source commit;
3. rerun the stored query parameters;
4. canonicalize the recomputed certificate; and
5. report byte equality.

`reconstruct(lineage_id)` first loads the embedded certificate from a committed event or lineage record, then applies the same algorithm.

The reconstruction certificate names requested and recomputed hashes and a `byte_equal` result.

## 18. Events in support

`events_in_support(instance,start,end,support,relations,context)` scans `(start,end]` and returns every candidate event whose declared support and compatibility gates pass. If a support ID is supplied, only relations explicitly naming that support are selected.

## 19. Compatibility query

`compatible(left,right,compatibility,tick,context)` replays both instances to the same nonnegative index and evaluates the selected compatibility expression with sources `left` and `right`. Its certificate includes both states and the boolean result.

## 20. Bounded grammar

A grammar record contains:

```text
axiom[]
productions
branch_bits[]
branch_policy
budgets {max_depth,max_symbols,max_stack}
```

A production is either an unconditional replacement array or a `{zero,one}` pair. Parallel rewriting proceeds left to right. A branched production consumes one explicit bit. `cycle` reuses the bit sequence modulo its length; `strict` fails when bits are exhausted.

Each generation checks symbol count and balanced `[`/`]` stack depth. A depth greater than the declared maximum fails. The expansion certificate includes every generation and branch decision.

This is bounded grammar development, not a recursive definition-dependency graph.

## 21. Literal artifact profile

`TOM-LITERAL-ARTIFACT-SOURCE-0.1` permits a primary documentation or other finite artifact to be represented by executable content-addressed definitions:

```text
seed.bytes
literal.bytes / concat.bytes
emit.bytes
```

`emit.bytes` lowers one to four bytes per TOMAGI `EMIT` cell. Cell flag bits 8..10 encode byte count, bit 11 encodes big-endian when set, and the existing low halt bit may halt the final cell. Program flag bits 8 and 9 declare the literal-artifact and emitted-byte profiles.

The materializer iterates an ordered TOMAGI trace, locates executed `EMIT` cells by `cell_before`, decodes only count/order/payload, and appends bytes. It MUST NOT inspect a target filename, media type, magic header, or domain semantics.

## 22. Rejection conditions

A conforming implementation rejects at least:

- altered seed bytes, length, hash, encoding, or terminal newline;
- invalid store, record, transaction, snapshot, commit, or certificate hash;
- stale transaction base or wrong sequence;
- duplicate staged IDs or blob IDs;
- unresolved dependency or dependency cycle;
- blob hash mismatch;
- instance reference to an absent blob;
- relation/event/transition reference to an absent record;
- unsupported record type, expression, zero test, trigger, or branch policy;
- expression depth/node/overflow/division errors;
- query horizon beyond the configured budget;
- malformed interval or nonboolean gate;
- unknown `State64` transition field;
- grammar depth, symbol, stack, bracket, or bit-budget error;
- artifact source/hash/root/byte/chunk/key errors; and
- materialization from a program without the required profile flags or without EMIT records.

## 23. Determinism theorem

For fixed:

```text
canonical seed bytes g
store commit c
instance/program blob x
query q and context k
query/expression/grammar budgets b
```

all conforming implementations of this profile and TOMAGI 1.0 produce equal observable values:

```text
snapshot(c)
record resolution
state_at(x,n)
trace(x,n)
support and compatibility decisions
next_event(x,t0)
event certificate
transition post-state
grammar expansion
reconstruction result
literal artifact bytes
```

Reason:

1. seed and object identities are exact bytes and SHA-256;
2. snapshots select immutable object hashes;
3. expression and grammar traversal orders are fixed;
4. arithmetic types and failure conditions are explicit;
5. relation candidates have a total priority/ID order;
6. TOMAGI transition semantics and serialization are fixed-width;
7. certificates use canonical JSON; and
8. artifact materialization is an ordered fold over explicit EMIT payloads.

Filesystem location, Python dictionary insertion history, wall time, process ID, and scheduling are not semantic inputs.

## 24. Starter acceptance tests

The package is accepted as 0.1 when:

1. the original TOMAGI tests continue to pass;
2. the exact seed is verified and a one-byte mutation fails;
3. two stores committing the same transaction produce equal commit and snapshot hashes;
4. stale-base and bad-blob transactions fail;
5. `state_at(instance:counter,3)` returns `rho=3` and `tick=3`;
6. `next_event(instance:counter,0,horizon=8)` returns index 5;
7. support and compatibility decisions are true for the event;
8. pair compatibility has one passing and one failing example;
9. `events_in_support` returns the one event;
10. a committed lineage reconstructs the event certificate byte-for-byte;
11. bounded grammar reaches depth 3 and rejects excess depth/insufficient strict bits;
12. the C and Python TOMAGI traces match for the counter program; and
13. the roadmap documentation is rebuilt byte-identically from its literal definition source, `.tmg`, and EMIT trace.

## 25. Known limitations

The following are outside 0.1:

- immutable secondary indexes and query planning;
- state checkpoints;
- interval trajectory propagation and continuous roots;
- simultaneous-event conflict semantics;
- distributed writers and branch/merge;
- learned candidate generation or acceptance;
- contradiction resolution and source-reliability models;
- planning, tools, perception, or autonomous action;
- new GPU device-execution evidence;
- large-world performance claims; and
- AGI.

These limitations define the next roadmap milestones rather than hidden assumptions.
