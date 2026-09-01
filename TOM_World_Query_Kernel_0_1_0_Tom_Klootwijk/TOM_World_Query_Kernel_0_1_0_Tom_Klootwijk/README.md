# TOM World & Query Kernel 0.1

## The first post-substrate milestone toward an evidence-backed general agent

This package takes the next concrete step after TOMAGI 1.0 and TOM-SRS 1.0: a persistent, content-addressed world with native exact-discrete queries.

It does **not** claim AGI. It implements the first missing world/query services on which learning, memory, planning, perception, and governed action can be built and tested.

## What is implemented now

```text
exact 244-byte TOM seed
-> content-addressed definitions, instances, relations, gates, grammar, events, lineage
-> immutable object/blob snapshot and commit store
-> exact TOMAGI state replay
-> support + compatibility + zero-relation scan
-> event certificate and atomic transition
-> event/lineage commit
-> byte-equal reconstruction
```

Native 0.1 APIs:

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

The implementation also includes finite branch-selected grammar expansion with depth, symbol, stack, and bit budgets.

## Demonstration

The shipped counter world contains a one-cell TOMAGI trajectory with `vrho=1` and `vtick=1`. After `n` transitions:

```text
rho = n
tick = n
```

A literal relation defines:

```text
R(q) = q.rho - 5
```

with a support window `0 <= rho <= 10` and compatibility requirement `orientation=0, sheet=0`.

The query kernel proves:

- `state_at(instance:counter,3)` returns `rho=3`, `tick=3`;
- `next_event(instance:counter,0,horizon=8)` returns the first zero at index 5;
- the transition sets output to 5 and branch to 1;
- the event and lineage are committed append-only; and
- reconstruction from the lineage reproduces the canonical event-certificate bytes.

A second example expands a bounded binary grammar to depth 3, consuming seven explicit branch bits and producing 29 symbols.

## Roadmap documentation

Start with:

- `artifacts/TOM_AGI_ROADMAP_AND_STARTER.md` — primary combined roadmap and implementation guide;
- `docs/ROADMAP.md` — milestone plan from query kernel through learner, memory, agent, grounding, governance, and AGI evaluation;
- `docs/IMPLEMENTATION_STATUS.md` — exact delivered/partial/missing matrix;
- `docs/ARCHITECTURE.md` — world/store/query layering;
- `docs/QUERY_API.md` — CLI and API examples;
- `docs/AGI_GAP_MATRIX.md` — what remains;
- `spec/TOM_WORLD_QUERY_KERNEL_0_1.md` — normative profile.

The primary roadmap artifact has its own literal causal chain:

```text
canonical seed
-> executable content-addressed artifact definitions
-> 7,039 Cell48 EMIT cells
-> Python and C execution traces
-> generic byte materialization
-> byte-identical Markdown artifact
```

No Markdown-aware writer is used in materialization.

## Build and validate

Requirements:

- Python 3.10 or later;
- a C99 compiler;
- `jsonschema` is optional and used when available.

```bash
make validate
```

This command:

1. rebuilds the original TOMAGI examples;
2. builds the counter world from literal program/world sources;
3. executes all native starter queries;
4. builds the roadmap through the literal `.tmg` EMIT chain;
5. runs the original and new Python test suites;
6. compares complete Python/C TOMAGI traces;
7. validates schemas and hashes;
8. performs a clean generated-output-free rebuild; and
9. writes `validation/validation_report.json` and `validation/VALIDATION.md`.

Current expected test count: **47**.

## CLI examples

```bash
# Exact state after three transitions
PYTHONPATH=src/python python3 -m tom_world.cli state-at \
  world/counter_store instance:counter 3

# Earliest event after state index zero
PYTHONPATH=src/python python3 -m tom_world.cli next-event \
  world/counter_store instance:counter 0 --horizon 8

# Pairwise topology compatibility
PYTHONPATH=src/python python3 -m tom_world.cli compatible \
  world/counter_store instance:counter instance:peer \
  compatibility:same-topology 3

# Bounded grammar development
PYTHONPATH=src/python python3 -m tom_world.cli expand-grammar \
  world/counter_store grammar:bounded-binary-branch --depth 3
```

See `docs/QUERY_API.md` for the complete command set.

## Package map

```text
TOM_seed_genome_2026-09-01.txt   authoritative root
AGENTS.md                         causal-source rules
docs/                             roadmap and implementation documentation
spec/TOM_WORLD_QUERY_KERNEL_0_1.md normative profile
spec/world/                       JSON schemas
src/python/tom_world/             store, records, expressions, queries, grammar, artifacts, CLI
src/python/tomagi/                original TOMAGI Python runtime
src/c/                            TOMAGI C99 runtime with full JSON trace mode
src/gpu/                          original GPU mappings
examples/world_counter/           literal program/world sources and transaction
examples/artifacts/               literal roadmap definition and compiled .tmg
world/counter_store/              committed example world
artifacts/                         TOMAGI-materialized roadmap
validation/                        query certificates, traces, proofs, clean rebuild, reports
tests/                             original TOMAGI plus world/query tests
```

## Exact boundary

Implemented:

- local single-writer content-addressed world;
- exact replay at complete TOMAGI transitions;
- finite-horizon discrete event scanning;
- explicit gates, event records, transitions, and lineage;
- bounded grammar;
- deterministic artifacts.

Not implemented or claimed:

- continuous/interval trajectory root solving;
- immutable query indexes at scale;
- autonomous definition learning;
- cognitive retrieval and consolidation;
- general planning and tool execution;
- grounded multimodal perception;
- safe autonomous action;
- new physical GPU execution evidence;
- AGI.

The next release target is **World & Query Kernel 0.2: immutable indexes, deterministic query plans, checkpoints, and a 10,000-record benchmark**.

## Source basis

The package preserves the supplied TOMAGI 1.0 report and TOM-SRS 1.0 seeded-substrate document under `sources/`. TOM-SRS provides the minimum native query set and the support → compatibility → event → transition → lineage order. TOMAGI provides the exact fixed-width state machine and explicitly states that learned generalization is outside the literal execution core.

Requester-supplied attribution: Tom Klootwijk; 10-07-1990; NL200678942. It is not independently verified.
