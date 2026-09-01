# TOM AGI Research Roadmap

## From deterministic substrate to an evidence-backed general agent

**Roadmap version:** 0.1.0  
**Root seed:** `TOM_seed_genome_2026-09-01.txt`  
**Current implementation milestone:** TOM World & Query Kernel 0.1  
**Date:** 2026-09-01

## 1. Starting point

The project now has two source-defined foundations:

1. **TOMAGI 1.0**, a finite deterministic operator machine with a 64-byte state, 48-byte cell, exact 64-bit key, sixteen opcodes, portable `.tmg` format, Python and C99 implementations, and GPU mappings.
2. **TOM-SRS 1.0**, a query-first seeded world specification in which the canonical seed resolves into definitions, instances, grammar, relations, support, compatibility, events, transitions, and lineage.

TOMAGI explicitly evaluates what has been made literal. TOM-SRS explicitly says that it does not automatically learn unknown semantics or infer an undeclared world model. Therefore the roadmap must add cognition as independently testable layers rather than rename the existing virtual machine “AGI.”

## 2. Roadmap rule

Each milestone must meet four conditions before the next begins:

1. **Literal source:** domain behavior is present in content-addressed definitions or data, not hidden in a host adapter.
2. **Deterministic replay:** the same seed, world commit, query, context, budgets, and program bytes yield the same certificate.
3. **Falsifiable acceptance:** a test can fail because the implementation or model is wrong.
4. **Bounded claim:** documentation distinguishes implemented behavior, planned behavior, and open research.

The TOMAGI 1.0 ABI should remain frozen unless a workload demonstrates a specific irreducible deficiency. Higher-level services should be definitions, libraries, stores, query planners, learners, and agents above that ABI.

# 3. Milestone sequence

## Milestone 0 — Deterministic execution foundation

**Status:** supplied baseline; retained and regression-tested.

### Capability

- exact canonical seed identity;
- content-addressed definition records;
- exact `State64`, `Cell48`, key codecs, opcodes, and `.tmg` format;
- deterministic Python/C execution and trace;
- literal SDF-zero cell membership;
- explicit branches, output tokens, and lineage checksum.

### Exit criterion

The original 24 TOMAGI tests pass unchanged, the C evaluator agrees with Python on the supplied examples, and no world-kernel change alters the 128/64/48-byte ABI.

## Milestone 1 — World & Query Kernel

**Purpose:** make the TOM-SRS world object and minimum native queries real.

### Milestone 1A — Starter kernel 0.1

**Status:** implemented in this package.

Delivered now:

- append-only content-addressed object, blob, snapshot, and commit storage;
- atomic HEAD update after immutable content is written;
- typed records for definitions, instances, relations, supports, compatibility, transitions, event specifications, grammars, observations, hypotheses, goals, events, and lineage;
- bounded side-effect-free integer expression language;
- `definition_at` and `verify_definition`;
- exact discrete `state_at` and full TOMAGI `trace`;
- finite-horizon `next_event` with explicit support and compatibility gates;
- `events_in_support`;
- pairwise `compatible`;
- event certificate, atomic transition, event/lineage commit, and `reconstruct`;
- finite branch-selected grammar expansion with depth, symbol, stack, and bit budgets;
- literal-definition-to-`.tmg` emitted-byte artifacts;
- one executable counter benchmark whose event occurs exactly at step 5.

The 0.1 solver is deliberately **discrete and exact**. It does not claim a continuous root solver or interval-certified numerical integration.

### Milestone 1B — Indexed query kernel 0.2

**Work:**

- add immutable secondary indexes by record type, dependency, support, relation, generative address, time interval, topology sheet, and definition hash;
- add a deterministic query planner that records index selections and candidate counts;
- separate event scan cost from state replay cost through checkpoint records;
- add batch query execution with stable reduction order;
- add corruption audit and full commit ancestry verification;
- test at 10,000, then 1,000,000 records.

**Exit criteria:**

- indexed and exhaustive queries return byte-equal result sets;
- query plans are deterministic;
- support and compatibility reduce candidate counts on a published benchmark;
- all indexes can be deleted and rebuilt from immutable records.

### Milestone 1C — Relation and event kernel 0.3

**Work:**

- typed scalar and interval residuals;
- discrete crossing, bracketed integer roots, rational-time interpolation, and certified interval roots;
- explicit rounding and tolerance profiles;
- event tie handling and simultaneous-event sets;
- transition conflict detection;
- trusted baseline comparisons for `state_at` and `next_event`.

**Exit criteria:**

- every event certificate names relation, support, compatibility, bracket, residual/interval, direction, solver, tolerance, margin, and transition;
- event time and class match independent baselines within the declared model;
- jitter intervals are proven not to alter accepted event class or order when that profile is used.

### Milestone 1D — Persistent world kernel 1.0

**Work:**

- stable schemas and migration rules;
- snapshot/commit merge with explicit conflicts;
- cross-process locking and crash recovery;
- storage compaction that preserves object hashes;
- Python/C query-certificate agreement for the supported integer profile;
- optional GPU state batches without changing semantics.

**Exit criteria:**

The minimum TOM-SRS query set is complete, indexed, benchmarked, crash-tested, and versioned.

## Milestone 2 — Learner and definition induction

**Purpose:** turn observations into candidate world definitions without making unverified candidates authoritative.

### Milestone 2A — Candidate pipeline

Implement the explicit lifecycle:

```text
observation
-> extracted typed claims
-> hypothesis
-> candidate relation/transition/grammar
-> counterexample search
-> held-out test
-> accepted definition or rejected candidate
-> new world commit and lineage
```

A learned model may be a teacher or proposer. It is not the authority. The accepted output is a typed, hash-verified definition plus evidence.

**Required record classes:** observation, source span, hypothesis, candidate definition, test case, counterexample, scorecard, acceptance decision, supersession, contradiction.

**Exit criteria:**

- learn at least three small deterministic domains from examples;
- generate held-out predictions through TOM queries rather than the proposing model;
- reject deliberately false candidates;
- reproduce every acceptance decision from stored evidence.

### Milestone 2B — Rule and relation induction

Add:

- finite program synthesis over the declared expression/transition algebra;
- relation-template induction;
- grammar-production induction;
- causal intervention tests where the environment permits them;
- minimum-description and evidence-coverage metrics as explicit policies, not hidden truth rules.

**Exit criteria:** new definitions improve held-out accuracy without invalidating prior conformance tests, and every improvement has an auditable evidence chain.

## Milestone 3 — Cognitive memory

**Purpose:** distinguish identity/replay from useful memory.

Build four explicit memory views over the same content-addressed store:

- **semantic:** definitions, facts, types, relations;
- **episodic:** observations, events, contexts, actions, outcomes;
- **procedural:** TOMAGI programs, grammars, policies, skills;
- **working:** active goals, hypotheses, plans, and temporary bindings.

Add contradiction sets, source reliability records, retrieval queries, consolidation proposals, and explicit expiry/supersession without deleting immutable history.

**Exit criteria:** benchmark retrieval precision/recall, contradiction detection, source attribution, and reconstruction over long event histories.

## Milestone 4 — Planner and agent kernel

**Purpose:** move from answering fixed queries to pursuing explicit goals.

### Required loop

```text
goal
-> current-state query
-> candidate actions/plans
-> predicted events and costs
-> policy/permission check
-> selected action
-> external execution adapter
-> observation
-> world transaction
-> replanning
```

Planning methods can include finite graph search, constraint solving, program synthesis, and learned proposal ranking. The committed plan and action must remain explicit.

**Exit criteria:**

- solve deterministic tool-use tasks with hidden test instances;
- recover from failed actions by updating the world and replanning;
- explain each plan through goals, assumptions, predicted transitions, and costs;
- never execute an external action without a typed permission record and bounded resource declaration.

## Milestone 5 — Grounded perception and action

**Purpose:** connect raw external data to typed world records while retaining provenance and uncertainty.

Add adapters for text first, then selected image/audio/sensor domains. Each adapter must emit observations with source bytes or stable references, extraction spans, uncertainty, and candidate entity/relation links. Raw model output remains an observation or hypothesis until verified.

**Exit criteria:**

- preserve exact source provenance;
- measure extraction and grounding error against labelled data;
- propagate uncertainty into event/query certificates;
- demonstrate closed-loop action with environmental feedback in a sandbox.

## Milestone 6 — Metacognition, governance, and safe autonomy

TOMAGI's no-failsafe transition core should remain transparent. Governance belongs above it as explicit records and external enforcement:

- capability and permission records;
- action scopes and resource budgets;
- human-approval gates;
- sandbox boundaries;
- policy versions and conflict resolution;
- rollback and incident lineage;
- self-assessment records: known, unknown, assumed, contradicted, and unverified.

**Exit criteria:** red-team tests demonstrate that denied capabilities remain unavailable even when a plan or learned proposer requests them.

## Milestone 7 — Scale and AGI evaluation

Do not claim AGI from architecture alone. Establish a published evaluation programme covering:

- novel concept acquisition;
- transfer across unrelated domains;
- long-horizon planning;
- tool learning;
- continual world updates;
- contradiction repair;
- uncertainty calibration;
- autonomous experiment selection;
- robustness to distribution shift;
- compute, latency, and storage costs;
- reproducibility and explanation fidelity.

Compare against appropriate conventional and learned baselines at equal task semantics. A general-agent claim requires broad empirical evidence, not only deterministic replay.

# 4. Immediate engineering backlog

## Next release: World & Query Kernel 0.2

Priority order:

1. immutable indexes and deterministic query plans;
2. checkpointed `state_at` and scan reuse;
3. interval residual type and certified discrete brackets;
4. simultaneous-event and transition-conflict semantics;
5. larger benchmark generator with 10,000 content-addressed records;
6. corruption, interrupted-write, and ancestry audit tests;
7. API stability review and schema migration proposal.

## Parallel research track: Learner 0.1 design

Before implementation, freeze:

- candidate/verified status model;
- training/validation/test evidence records;
- counterexample format;
- definition supersession and contradiction semantics;
- acceptance policies and how they remain explicit;
- boundary between a learned proposer and authoritative TOM commits.

# 5. Decision gates

The following claims are not yet supported:

- continuous certified next-event solving;
- automatic induction of correct unknown rules;
- grounded perception from raw modalities;
- general planning or autonomous tool use;
- large-scale world performance;
- device-executed GPU query equivalence in this package;
- AGI.

The project is ready to research those layers because it now has a deterministic world/query starter, not because those layers are already present.
