<!-- TOM-WQK-0.2-CONTINUATION -->
# TOM World & Query Kernel 0.2 continuation

Milestone 1B is now implemented: immutable content-addressed indexes, deterministic indexed/exhaustive plans, exact root-derived checkpoints, stable declared-order batches, full commit-ancestry audit, and a frozen 10,000-record benchmark. The primary plan records `10,000 -> 9,600 -> 96 -> 6 -> 2` candidates and returns events at ticks 5 and 21 with semantic byte equality against exhaustive evaluation. `state_at(...,999)` uses checkpoint 900 and replays 99 instead of 999 transitions while preserving the semantic certificate.

The next milestone is 1C / 0.3: typed residual intervals, bracketed event-time certificates, rational/fixed-point error policy, simultaneous-event sets, and explicit conflict semantics. See `docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md` and `spec/TOM_WORLD_QUERY_KERNEL_0_2.md`.
<!-- /TOM-WQK-0.2-CONTINUATION -->

# TOM AGI Roadmap and World/Query Kernel Starter

**Release:** 0.1.0  
**Date:** 2026-09-01  
**Canonical seed:** `TOM_seed_genome_2026-09-01.txt`  
**Underlying machine:** TOMAGI 1.0

## Executive answer

The deterministic execution core is stable enough to build on, but AGI is not present. The next missing substrate layer identified by TOM-SRS is a persistent query-first world with native definition, state, event, compatibility, trace, and reconstruction queries. This release starts that layer rather than adding speculative opcodes.

What is concrete now:

```text
canonical seed
-> content-addressed world records and TOMAGI program blobs
-> immutable snapshot and commit lineage
-> exact State64 replay
-> support + compatibility + zero-relation scan
-> event certificate
-> atomic transition
-> event/lineage commit
-> byte-equal reconstruction
```

The demonstration world certifies that a linear TOMAGI trajectory reaches `rho=5` at exact replay index 5. It commits that event and reconstructs it from lineage. A separate bounded grammar demonstration reaches depth 3 under explicit symbol, stack, and branch-bit budgets.

The next major research layer is a learner that turns observations into candidate definitions and accepts them only after counterexample and held-out testing.

---

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


---

# TOM World & Query Kernel 0.1 — Implementation Status

## Delivered and executable

| Capability | Status | Concrete file/API |
|---|---|---|
| Canonical seed verification | Complete for exact TOM-SRS 1.0 seed | `tom_world.seed` |
| Canonical JSON/content hashes | Complete for JSON-compatible values | `tom_world.canonical` |
| Persistent immutable objects/blobs | Complete starter | `tom_world.store.WorldStore` |
| Snapshot and commit hashes | Complete starter | `snapshots/`, `commits/`, `HEAD` |
| Atomic local commit publication | Complete starter | immutable writes, then atomic HEAD replace |
| Record types | Complete starter set | `tom_world.records` |
| Bounded expression evaluator | Complete 0.1 integer profile | `tom_world.expression` |
| `definition_at` | Implemented | `QueryEngine.definition_at` |
| `verify_definition` | Implemented | `QueryEngine.verify_definition` |
| `state_at` | Exact discrete replay implemented | `QueryEngine.state_at` |
| `trace` | Full TOMAGI trace implemented | `QueryEngine.trace` |
| `next_event` | Exact discrete finite-horizon scan implemented | `QueryEngine.next_event` |
| support gate | Implemented | content-addressed support expressions |
| compatibility gate | Implemented | event and pairwise compatibility expressions |
| `events_in_support` | Implemented | interval `(start,end]` |
| `compatible(q1,q2)` | Implemented | pairwise State64 expression |
| atomic transition | Implemented starter set/add/xor profile | event certificate post-state |
| event and lineage persistence | Implemented | `commit_event` |
| `reconstruct(lineage)` | Byte-equal certificate replay implemented | `QueryEngine.reconstruct` |
| bounded grammar | Implemented starter L-system profile | `GrammarEngine.expand` |
| literal artifact EMIT chain | Implemented | `tom_world.artifact` |
| Python/C TOMAGI agreement | Tested for counter trajectory and original examples | `build/tomagi-c --trace-json` |

## Explicitly partial

| Area | 0.1 boundary |
|---|---|
| Query planning | Exhaustive deterministic scan; no secondary indexes yet |
| Event solving | Integer state after whole TOMAGI transitions; no continuous root isolation |
| Intervals | Expression language can construct intervals, but no general interval trajectory solver |
| Transactions | Single-writer local directory lock; no distributed consensus or merge |
| Checkpoints | Replay begins at program initial state; no state checkpoint index |
| Grammar | Finite parallel rewrite with explicit bits; no grammar-to-Cell48 compiler yet |
| Uncertainty | Stored as explicit records/fields; no calibration or propagation framework |
| Learning | Observation and hypothesis record classes only; no autonomous inducer |
| Planning | Goal records only; no search or action executor |
| Perception/action | Not implemented |
| GPU | Original mappings retained; no new physical device dispatch claimed |

## Demonstrated benchmark

The counter world contains a one-cell TOMAGI trajectory. `KIN2` preserves `vrho=1` and `vtick=1`, so the exact discrete replay has `rho=tick=n` after `n` transitions.

A relation exposes residual:

```text
R(q) = q.rho - 5
```

It is gated by:

```text
support:       0 <= rho <= 10
compatibility: orientation = 0 and sheet = 0
```

The earliest event after index 0 is certified at index 5. The transition sets output to 5 and branch to 1 and updates lineage. The resulting event and lineage are committed in the shipped world store and reconstructed byte-for-byte from their source commit.


---

# Architecture: TOM World & Query Kernel 0.1

## 1. Layering

```text
canonical seed
    |
    v
content-addressed world records and TOMAGI blobs
    |
    v
immutable snapshot + commit lineage
    |
    v
query kernel
  definition_at / verify_definition
  state_at / trace
  support / compatibility
  next_event / events_in_support
  transition / event / lineage
  reconstruct
    |
    v
query certificates and optional literal EMIT artifacts
```

TOMAGI remains the deterministic state-transition engine. The world kernel stores definitions and context, selects exact program/state inputs, evaluates typed gates and relations, and returns content-addressed certificates.

## 2. TOM-SRS world-object mapping

| TOM-SRS component | 0.1 representation |
|---|---|
| `D` definitions | `definition` records |
| `X` instances/state seeds | `instance` records plus `.tmg` blobs |
| `G` finite grammar | `grammar` records and expansion certificates |
| `R` relations | `relation` records with bounded expressions |
| `S` support | `support` records |
| `C` compatibility | `compatibility` records |
| `H` hinges/connectors | TOMAGI HINGE cells or explicit transition records; no separate high-level hinge engine yet |
| `E` verified events | event certificates and committed `event` records |
| `T` transitions | `transition` records |
| `I` invariants | definition payload metadata; enforcement is partial in 0.1 |
| `L` lineage/novelty | commit ancestry and `lineage` records |
| `P` phase pipelines | dependencies plus query order; no general pipeline planner yet |
| `g,h_g` root | exact seed bytes and fixed hash in every store/transaction |

## 3. Store layout

```text
store/
  store.json                     content-addressed store descriptor
  seed.bin                       exact 244 canonical bytes
  HEAD                           mutable pointer to one immutable commit
  objects/<sha256>.json          immutable records
  blobs/<sha256>.bin             immutable `.tmg` or other bytes
  snapshots/<sha256>.json        ID -> object/blob hash maps
  commits/<sha256>.json          parent, sequence, transaction, snapshot
```

Only `HEAD` is mutable. A commit writes and verifies all immutable objects, the snapshot, and the commit before atomically replacing `HEAD`.

## 4. Query order

For each candidate relation at each exact discrete state:

```text
state replay
-> support decisions
-> compatibility decisions
-> relation residual/interval
-> zero/entry/crossing trigger
-> event certificate
-> atomic transition
-> optional event + lineage transaction
```

Candidates are ordered by integer priority and then relation ID. The first passing candidate at the earliest state index is `next_event`.

## 5. Host-code boundary

Generic host mechanics include hashing, immutable storage, dependency validation, expression evaluation, TOMAGI replay, event scanning, transition application, and certificate serialization.

The counter target, relation, support window, topology requirement, output token, and grammar productions are all literal records in `examples/world_counter/world_source.json`; they are not branches hard-coded in `QueryEngine`.


---

# Native Query API 0.1

The CLI is installed as `tom-world`. With an unpacked repository, prefix commands with `PYTHONPATH=src/python python3 -m tom_world.cli`.

## Initialize and commit

```bash
PYTHONPATH=src/python python3 -m tom_world.cli init \
  world/counter_store --seed TOM_seed_genome_2026-09-01.txt

PYTHONPATH=src/python python3 -m tom_world.cli commit \
  world/counter_store examples/world_counter/initial_transaction.json
```

## `definition_at(id)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli definition-at \
  world/counter_store relation:counter-rho-equals-five
```

Returns the exact immutable record at the selected commit.

## `verify_definition(id)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli verify-definition \
  world/counter_store definition:world-query-kernel
```

Verifies object identity, record content hash, and dependency resolution.

## `state_at(t)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli state-at \
  world/counter_store instance:counter 3
```

The 0.1 meaning of `t` is a zero-based count of complete TOMAGI transitions. The benchmark returns `rho=3` and `tick=3`.

## `next_event(t0)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli next-event \
  world/counter_store instance:counter 0 --horizon 8 \
  --output validation/next_event.json
```

Returns the earliest event at index 5 with residual zero, passed support and compatibility gates, event/pre/post states, transition, route, confidence record, guard margin, and definition hashes.

## `events_in_support`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli events-in-support \
  world/counter_store instance:counter 0 8 \
  --support support:counter-rho-window
```

The interval is `(start_tick, end_tick]`.

## `compatible(q1,q2)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli compatible \
  world/counter_store instance:counter instance:peer \
  compatibility:same-topology 3
```

Returns a certificate containing both exact states and the boolean result.

## `trace`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli trace \
  world/counter_store instance:counter 5
```

Returns the ordered TOMAGI transitions and terminal state.

## `reconstruct(lineage)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli reconstruct \
  world/counter_store lineage:<certificate-prefix>
```

Loads the embedded event certificate, checks its content hash, replays the source commit and query, and reports whether the canonical certificate bytes are equal.

## Bounded grammar

```bash
PYTHONPATH=src/python python3 -m tom_world.cli expand-grammar \
  world/counter_store grammar:bounded-binary-branch --depth 3
```

Returns every finite generation, branch-bit decisions, stack depth, and terminal symbols.

## Literal emitted-byte documentation

```bash
PYTHONPATH=src/python python3 -m tom_world.cli make-artifact-source \
  docs/ROADMAP_AND_STARTER.md examples/artifacts/roadmap.source.json \
  --artifact-id tom-agi-roadmap-and-starter \
  --media-type text/markdown \
  --seed TOM_seed_genome_2026-09-01.txt

PYTHONPATH=src/python python3 -m tom_world.cli compile-artifact \
  examples/artifacts/roadmap.source.json \
  examples/artifacts/roadmap.tmg \
  --seed TOM_seed_genome_2026-09-01.txt

PYTHONPATH=src/python python3 -m tom_world.cli materialize-artifact \
  examples/artifacts/roadmap.tmg \
  artifacts/TOM_AGI_ROADMAP_AND_STARTER.md
```


---

# AGI Gap Matrix After World & Query Kernel 0.1

## What the starter closes

| Closure | Status |
|---|---|
| Canonical seed identity | closed for the exact TOM-SRS 1.0 seed |
| TOMAGI execution | closed for the supplied fixed-width machine |
| Persistent record identity | starter closed through object/snapshot/commit hashes |
| Exact discrete state query | implemented |
| Exact finite-horizon next-event query | implemented |
| Explicit support and compatibility gates | implemented |
| Event/transition/lineage certificate | implemented starter |
| Event reconstruction | implemented byte-for-byte |
| Bounded grammar termination | implemented for the starter rewrite profile |
| Documentation byte artifact | reproducible through literal definitions and EMIT |

## What remains for AGI

| Capability | Missing evidence or implementation |
|---|---|
| Knowledge acquisition | No mechanism yet proposes correct new definitions from raw evidence. |
| Generalization | No evidence of transfer to unseen concepts or domains. |
| Grounded perception | No raw text/image/audio/sensor adapter with measured grounding error. |
| Cognitive memory | Identity and event history exist, but retrieval, consolidation, contradiction repair, and relevance learning are incomplete. |
| Planning | Goal records exist, but no general plan search, action model, or replanning loop. |
| Tool use/action | No permissioned external action adapter. |
| Metacognition | No full known/unknown/assumption/conflict controller. |
| Uncertainty | Explicit fields exist; calibrated propagation and decision theory do not. |
| Continuous event solving | 0.1 scans exact integer transition states only. |
| Query scale | No million-record or distributed benchmark yet. |
| Safe autonomy | No complete governance and external capability enforcement layer. |
| AGI evidence | Not established. |

## Interpretation

The substrate is no longer missing a basic persistent query layer. It is still missing most of the cognitive mechanisms that would turn a deterministic world interpreter into a generally capable agent. The correct next research object is a learner that proposes and verifies new definitions, not another unmotivated opcode expansion.


---

# Next Experiments

## Experiment 1 — Indexed versus exhaustive next-event

Create 10,000 relation records across disjoint support windows. Implement immutable support and relation indexes. Verify that exhaustive and indexed certificates are byte-equal while recording candidate-count reduction and elapsed time separately.

## Experiment 2 — Discrete bracket and interval event

Add a trajectory that jumps from residual -2 to +3 without visiting zero. Define a crossing certificate with an explicit bracket and rational interpolation policy. Compare against an independently coded baseline.

## Experiment 3 — Simultaneous events

Create two relations that trigger at the same state index with different and equal priorities. Specify deterministic event-set and conflict semantics before implementing transitions.

## Experiment 4 — Candidate-definition learner

Provide input/output examples for small integer relations. Use exhaustive finite program synthesis to propose candidate expressions. Store every candidate and counterexample. Accept only the candidate that passes a held-out suite. This is the first learning milestone because it creates new authoritative definitions from evidence.

## Experiment 5 — Contradiction and supersession

Commit two incompatible factual definitions from different sources. Add explicit contradiction records, source evidence, and a policy that selects neither as silently true. Test historical reconstruction before and after supersession.

## Experiment 6 — Goal-directed planning

Define a small deterministic environment with three actions, costs, and a hidden test start state. Implement explicit breadth-first or A* planning over TOM query results. Commit the plan, execute through a sandbox adapter, observe the outcome, and replan after an injected action failure.

## Experiment 7 — Text grounding adapter

Parse a controlled synthetic language into observation and relation candidates. Measure exact entity/relation extraction and preserve source spans. Keep parser output as hypotheses until verified against the world.


## Normative specification

The exact record, store, transaction, query, event, grammar, rejection, and determinism contracts are in `spec/TOM_WORLD_QUERY_KERNEL_0_1.md`.
