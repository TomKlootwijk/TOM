# TOM World & Query Kernel 0.2

## Immutable indexes, deterministic query plans, exact checkpoints, batch reduction, and ancestry audit

This release continues the first post-substrate milestone above TOMAGI 1.0. Version 0.1 made the TOM-SRS world object and minimum native exact-discrete queries executable. Version 0.2 makes that world **indexable, replay-accelerated, auditable, and benchmarked at exactly 10,000 records**.

It does **not** claim AGI. It implements the next world/query infrastructure required before interval event solving, autonomous definition learning, memory consolidation, planning, grounding, and governed action can be tested.

## What 0.2 adds

```text
immutable world commit
-> content-addressed secondary indexes
-> deterministic indexed or exhaustive query plan
-> exact state/event semantics
-> root-derived checkpoint acceleration
-> stable ordered batch certificate
-> index deletion/rebuild proof
-> full commit-ancestry corruption audit
```

New modules:

- `tom_world.indexes` — immutable type, dependency, relation, support, compatibility, interval, topology, generative-address, hash, and checkpoint indexes;
- `tom_world.planner` — indexed and exhaustive plans with exact candidate and work counts;
- checkpoint support in `tom_world.query`;
- stable declared-order `batch` queries;
- `tom_world.audit` — uncached disk verification of every reachable transaction, snapshot, index, record, dependency, blob, and parent commit;
- persistent exact transaction bodies in the store;
- CLI commands for index queries, index rebuilding, audits, checkpoints, planned queries, and batches.

The TOMAGI ABI remains frozen: 128-byte header, 64-byte `State64`, 48-byte `Cell48`, sixteen opcodes, and unchanged transition semantics.

## Exact 10,000-record benchmark

The frozen benchmark source contains:

| Type | Count |
|---|---:|
| definition | 1 |
| support | 16 |
| compatibility | 4 |
| instance | 100 |
| relation | 9,600 |
| observation | 269 |
| checkpoint | 10 |
| **Total** | **10,000** |

For `instance:benchmark:042`, interval `(0,32]`, and `support:benchmark-bucket:04`, the indexed plan records:

```text
10,000 total records
-> 9,600 relation records
-> 96 relations for the instance
-> 6 relations in the support bucket
-> 2 interval-overlapping relations
```

The two events occur at ticks **5** and **21**. Exhaustive evaluation returns byte-identical semantic certificate data.

For `state_at(instance:benchmark:042,999)`:

```text
indexed checkpoint at 900 -> 99 TOMAGI transitions
checkpoint-free baseline  -> 999 TOMAGI transitions
saved deterministic work  -> 900 transitions
semantic state/certificate -> byte-equal
```

The benchmark also deletes its final immutable index file, rebuilds it from the snapshot, and proves exact byte equality. A full two-commit ancestry audit reports zero errors and zero orphans.

## Native query surface

The 0.1 semantic API remains:

```text
definition_at(id)
verify_definition(id)
state_at(instance,t)
next_event(instance,t0)
events_in_support(...)
compatible(q1,q2)
trace(instance,t)
reconstruct(certificate_or_lineage)
```

Version 0.2 adds plan/certificate and maintenance surfaces:

```text
state_at_with_plan(...)
next_event_with_plan(...)
events_in_support_with_plan(...)
compatible_with_plan(...)
batch(requests, planner_mode)
make_checkpoint_record(...)
commit_checkpoints(...)
index_for_commit(...)
indexed_record_ids(...)
interval_record_ids(...)
rebuild_indexes(...)
audit_store(...)
```

## Build and validation

Requirements:

- Python 3.10+;
- C99 compiler;
- optional `jsonschema` for schema validation.

```bash
make validate
```

This rebuilds the original TOMAGI examples, counter world, 10,000-record index benchmark, roadmap artifact, 0.2 release artifact, C runtime, tests, static schemas, full validation report, and clean rebuild.

Expected test count after 0.2: **60 or more**.

Useful commands:

```bash
# Build only the 10,000-record benchmark
make benchmark

# Inspect one immutable posting list
PYTHONPATH=src/python python3 -m tom_world.cli index-query \
  world/index_benchmark_store relation_by_instance instance:benchmark:042

# Planned indexed event query
PYTHONPATH=src/python python3 -m tom_world.cli events-in-support \
  world/index_benchmark_store instance:benchmark:042 0 32 \
  --support support:benchmark-bucket:04 --plan --planner indexed

# Checkpoint-aware state query
PYTHONPATH=src/python python3 -m tom_world.cli state-at \
  world/index_benchmark_store instance:benchmark:042 999 \
  --plan --planner indexed

# Stable declared-order batch
PYTHONPATH=src/python python3 -m tom_world.cli batch-query \
  world/index_benchmark_store examples/index_benchmark/batch_requests.json \
  --planner indexed

# Full disk/ancestry audit
PYTHONPATH=src/python python3 -m tom_world.cli audit \
  world/index_benchmark_store --require-no-orphans
```

## Documentation

- `spec/TOM_WORLD_QUERY_KERNEL_0_2.md` — normative 0.2 profile;
- `docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md` — release record and completed work;
- `docs/INDEX_AND_QUERY_PLAN_PROFILE.md` — immutable indexes and plans;
- `docs/CHECKPOINT_AND_AUDIT_PROFILE.md` — checkpoint, batch, and audit semantics;
- `docs/BENCHMARK_10000.md` — frozen benchmark population and acceptance;
- `docs/ROADMAP.md` — AGI research milestones, with 1B complete and 1C next;
- `docs/IMPLEMENTATION_STATUS.md` — exact delivered/partial/missing matrix;
- `docs/QUERY_API.md` — Python and CLI usage;
- `docs/AGI_GAP_MATRIX.md` — what remains before any AGI claim.

The primary 0.2 release record is itself reproduced through the literal artifact chain:

```text
canonical seed
-> content-addressed literal documentation definitions
-> compiled TOMAGI .tmg
-> equal Python/C traces
-> ordered EMIT records
-> byte-identical Markdown artifact
```

## Package map

```text
TOM_seed_genome_2026-09-01.txt     authoritative root
AGENTS.md                           causal-source and replay rules
docs/                               roadmap and release documentation
spec/TOM_WORLD_QUERY_KERNEL_0_2.md  normative 0.2 profile
spec/world/                         record/index/plan/batch/audit schemas
src/python/tom_world/               store, index, planner, query, audit, grammar, artifact, CLI
src/python/tomagi/                  retained TOMAGI Python runtime
src/c/                              retained TOMAGI C99 runtime with JSON trace
src/gpu/                            retained shared-ABI mappings
examples/world_counter/             starter world sources
examples/index_benchmark/           frozen 10,000-record transactions and query batch
world/counter_store/                committed starter world
world/index_benchmark_store/        committed two-transaction benchmark world
examples/artifacts/                 literal documentation artifact sources and .tmg files
artifacts/                           TOMAGI-materialized Markdown documents
validation/                          query plans, certificates, audit, traces, clean rebuild, reports
tests/                               TOMAGI, world/query, index, checkpoint, batch, audit tests
```

## Exact evidence boundary

Implemented and executed:

- local append-only single-writer content-addressed storage;
- immutable secondary indexes and exact deterministic rebuilding;
- indexed/exhaustive query-plan certificates;
- exact-discrete state and event queries;
- exact root-derived checkpoints;
- stable ordered batch reduction;
- full commit-ancestry disk audit;
- 10,000-record candidate-reduction benchmark;
- Python/C equality for TOMAGI artifact chains;
- clean source-to-boundary rebuild.

Not implemented or claimed:

- continuous or interval-certified event time;
- simultaneous-event set/conflict semantics;
- adaptive or learned cost-based planning;
- autonomous knowledge acquisition or generalization;
- cognitive memory consolidation;
- general goal planning and tool use;
- grounded multimodal perception;
- safe autonomous action;
- new physical GPU dispatch evidence;
- AGI.

The next target is **World & Query Kernel 0.3: interval/bracket event certificates and deterministic simultaneous-event semantics**.

Requester-supplied attribution: Tom Klootwijk; 10-07-1990; NL200678942. It is not independently verified.
