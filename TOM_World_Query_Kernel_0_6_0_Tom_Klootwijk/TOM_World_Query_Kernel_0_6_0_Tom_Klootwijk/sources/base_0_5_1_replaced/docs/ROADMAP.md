# TOM AGI Research Roadmap

## From deterministic substrate to an evidence-backed general agent

**Roadmap version:** 0.2.0  
**Root seed:** `TOM_seed_genome_2026-09-01.txt`  
**Current implementation milestone:** TOM World & Query Kernel 0.2 / Milestone 1B  
**Date:** 2026-09-01

## 1. Starting point

The project has three implemented foundations:

1. **TOMAGI 1.0** — a finite deterministic operator machine with a 64-byte state, 48-byte cell, exact 64-bit key, sixteen opcodes, portable `.tmg`, Python/C99 execution, and GPU mappings.
2. **TOM Genesis** — executable seeded definitions and generic emitted-byte causal closure.
3. **TOM World & Query Kernel 0.2** — a persistent content-addressed world with native queries, immutable indexes, deterministic query plans, exact checkpoints, stable batch certificates, and full ancestry audit.

TOMAGI evaluates what has been made literal. TOM-SRS states that the core does not automatically learn unknown semantics or infer an undeclared world. The roadmap therefore adds cognition as separate falsifiable layers instead of relabeling the machine as AGI.

## 2. Roadmap governance rule

A milestone is complete only when it has:

1. **Literal source:** domain laws, examples, and expected outputs are content-addressed records or definitions, not hidden host behavior.
2. **Deterministic replay:** the same seed, commit, query, context, budgets, and machine bytes produce the same semantic certificate.
3. **Independent baseline:** an exhaustive, alternate backend, or separately implemented solver can disagree and fail the milestone.
4. **Measured acceptance:** operation counts, error bounds, held-out cases, and hashes are explicit.
5. **Bounded claim:** delivered, partial, planned, and unknown are distinguished.

The TOMAGI ABI remains frozen until a concrete workload proves an irreducible deficiency.

# 3. Milestone sequence

## Milestone 0 — Deterministic execution foundation

**Status:** complete supplied baseline; continuously regression-tested.

Delivered:

- exact seed identity;
- fixed 128/64/48-byte ABI;
- sixteen deterministic opcodes;
- Python/C execution equality;
- literal LUT membership zero relation;
- explicit branch, output, status, and lineage.

## Milestone 1 — World & Query Kernel

### Milestone 1A — Starter kernel 0.1

**Status:** complete.

Delivered:

- local append-only content-addressed records, blobs, snapshots, and commits;
- atomic `HEAD` publication;
- typed records for definitions, instances, relations, supports, compatibility, transitions, event specifications, grammar, observations, hypotheses, goals, events, and lineage;
- bounded query-expression evaluator;
- minimum TOM-SRS native queries;
- exact finite-horizon event scan;
- event/transition/lineage certificate and reconstruction;
- bounded binary grammar;
- counter-world demonstration.

### Milestone 1B — Indexed kernel 0.2

**Status:** complete in this release.

Delivered:

- exact transaction bodies retained for every new commit;
- immutable content-addressed indexes attached to snapshots;
- indexes by type, dependency, relation instance/support/compatibility, event-spec relation, generative address, interval, topology sheet, definition/content hash, and checkpoint instance;
- deterministic indexed and exhaustive query plans;
- exact stage candidate counts and work counters;
- root-derived complete-state checkpoints;
- checkpoint-aware replay with root semantic baseline;
- stable declared-order batch certificates;
- index deletion and exact rebuild;
- uncached disk/ancestry corruption audit;
- frozen 10,000-record benchmark;
- exact candidate reduction `10000 -> 9600 -> 96 -> 6 -> 2`;
- 900-transition checkpoint work reduction at tick 999;
- indexed/exhaustive semantic byte equality.

### Milestone 1C — Interval and simultaneous-event kernel 0.3

**Status:** next target.

Required work:

- typed residual intervals and exact discrete brackets;
- rational or fixed-point interpolation profile;
- certified event-time interval and error bound;
- root isolation for declared monotone/polynomial relation families;
- crossing direction and solver-status taxonomy;
- simultaneous-event set construction;
- deterministic priority, compatible commutation, and conflict rules;
- independent solver baseline;
- jitter interval proof that perturbation cannot alter event class/order;
- topological invariant checks across bracketed events.

Exit criteria:

1. A residual jump that skips zero still yields a certified bracketed event.
2. State and event certificates match an independent reference solver.
3. Simultaneous events are insertion-order independent.
4. Conflicting transitions reject or resolve only by an explicit content-addressed policy.
5. Numeric type, rounding, interpolation, and error bounds are present in every certificate.

### Milestone 1D — Stable World & Query Kernel 1.0

**Status:** planned.

Required:

- stabilized schemas and migration rules;
- scalable object packing while preserving content hashes;
- checkpoint scheduling policy;
- deterministic query-plan compatibility versioning;
- multi-process read safety and explicit single-writer transaction lock semantics;
- benchmark at 1,000,000 records;
- documented backup, replication, and corruption recovery;
- complete query conformance vectors.

## Milestone 2 — Candidate-definition learner

**Purpose:** create new candidate knowledge from evidence without making opaque weights authoritative.

### 2A — Finite symbolic learner

- bounded expression grammar;
- complete candidate enumeration under cost budget;
- typed training/validation/held-out examples;
- candidate, counterexample, and rejection records;
- minimum-description or explicit declared tie-break;
- commit only verified hypotheses;
- reproduce learning trace from source examples.

### 2B — Observation-to-relation induction

- infer relation parameters and support windows;
- cross-validation and adversarial counterexamples;
- uncertainty and provenance;
- contradiction detection against current world;
- explicit human or policy approval before verified-definition promotion.

### 2C — Optional learned teacher

A learned model may propose candidate records, but cannot directly mutate authoritative world state. Every accepted proposal must become typed literal data and pass deterministic validation.

Exit criterion: correct rules are recovered on unseen finite tasks, incorrect candidates retain explicit failure evidence, and the same source examples reproduce the same final committed definition.

## Milestone 3 — Cognitive memory

### 3A — Typed memory classes

- semantic facts and definitions;
- episodic event/lineage records;
- procedural `.tmg` programs and skills;
- working-memory query contexts;
- source and evidence memory;
- counterfactual and rejected hypotheses.

### 3B — Retrieval and consolidation

- explicit relevance features;
- deterministic retrieval baseline;
- learned retrieval candidate layer with held-out evaluation;
- abstraction and summary definitions linked to source records;
- contradiction and supersession graphs;
- forgetting only through explicit policy while history remains reconstructable.

Exit criterion: benchmark questions require retrieval across commits and episodes; answers include sufficient source lineage and outperform exhaustive search at equal semantics.

## Milestone 4 — Goal, planning, and action

### 4A — Deterministic planning

- typed goals, actions, preconditions, effects, costs, and resources;
- breadth-first/A* reference planners;
- plan certificate and predicted transition trace;
- explicit no-plan and budget-exhausted outcomes.

### 4B — Tool execution and replanning

- sandboxed capability adapters;
- permission and approval records;
- action invocation and observation transactions;
- compare predicted and actual outcomes;
- replan on explicit discrepancy.

Exit criterion: held-out deterministic environments are solved, actions are permission-bounded, every plan/action/outcome is replayable, and injected failures trigger correct replanning.

## Milestone 5 — Grounded perception and language

### 5A — Controlled language

- exact source spans;
- typed entity/relation candidates;
- ambiguity alternatives;
- hypothesis status until verified;
- measured extraction precision and recall.

### 5B — Images, audio, and sensors

- immutable raw blobs;
- calibrated observation records;
- spatial/temporal relation candidates;
- benchmark error and uncertainty;
- no unrecorded perceptual state becomes authoritative.

Exit criterion: observations ground to world IDs/relations with measured held-out error and preserved raw evidence.

## Milestone 6 — Metacognition, governance, and safe autonomy

- known/unknown/assumption/contradiction records;
- plan-progress and failure diagnosis;
- capability grants and denials;
- human approval gates;
- resource ceilings;
- rollback and recovery procedures;
- audit and shutdown authority outside the hot VM;
- red-team evaluation.

Safety remains explicit above TOMAGI. The no-failsafe opcode semantics are not secretly changed.

## Milestone 7 — General-capability evaluation

Only after the preceding layers exist should broad AGI claims be tested.

Required evidence:

- unseen-domain task suites;
- transfer and compositional generalization;
- long-horizon planning;
- continual learning without catastrophic corruption;
- tool use and environmental feedback;
- calibrated uncertainty and abstention;
- provenance-complete explanations;
- resource and safety compliance;
- comparison with strong learned and symbolic baselines.

Failure is informative. The architecture may require new definition libraries, query services, learning methods, or a versioned substrate change. No result should be described as AGI solely because the runtime is self-referential, deterministic, or content-addressed.

# 4. Immediate 0.3 implementation plan

## Work package A — Relation interval record

Add an explicit relation evaluation result:

```text
point residual or closed rational interval
numeric profile
rounding rule
error source
monotonicity declaration
```

## Work package B — Bracket solver

Implement a finite solver over exact state endpoints. For an admissible relation family, return:

```text
left/right logical tick
left/right residual
crossing direction
rational event-time interval
proof conditions
solver status
```

## Work package C — Simultaneous events

Define event-set identity as a sorted list of event-certificate hashes. Classify transition pairs as:

```text
commuting
ordered by explicit priority
conflicting and rejected
resolved by named policy
```

## Work package D — Baselines

Implement a separate reference interpolator and property tests. Compare all event times and error bounds. Retain adversarial discontinuity cases.

## Work package E — 0.3 artifact and benchmark

Create a literal documentation artifact and a benchmark with exact jump-over-zero, tangent contact, two simultaneous commuting events, and one transition conflict.

# 5. Current truthful conclusion

The project now has a deterministic machine, executable seeded definitions, a persistent world, native queries, immutable indexes, reproducible query plans, exact checkpoints, stable batches, and ancestry auditing. That is enough to begin serious event-solver and learner research without redesigning the VM.

It is not yet a learner, memory system, planner, grounded agent, safety architecture, or AGI. The next substrate question is no longer “can the world be queried at scale?” at the starter level; it is “can non-integer and simultaneous events be certified under explicit numeric semantics?” The next cognitive question is “can correct new definitions be induced from evidence and committed without opaque authority?”
