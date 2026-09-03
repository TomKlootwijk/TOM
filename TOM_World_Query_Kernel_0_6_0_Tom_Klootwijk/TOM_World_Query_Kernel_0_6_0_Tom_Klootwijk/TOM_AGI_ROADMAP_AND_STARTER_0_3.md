# TOM AGI Roadmap — updated through World & Query Kernel 0.3

## Current position

TOM now has three completed foundation layers:

```text
Genesis 1.0
  exact seed -> executable definitions -> Cell48 -> .tmg -> EMIT -> bytes

World & Query Kernel 0.1
  persistent content-addressed world -> state/event queries -> lineage

World & Query Kernel 0.2
  immutable indexes -> deterministic plans -> checkpoints -> audit -> 10,000-record fixture

World & Query Kernel 0.3
  exact rational intervals -> certified crossings -> simultaneous event sets
  -> deterministic conflict-checked transitions -> trusted baseline comparison
```

This is still a substrate and query kernel, not AGI. The missing cognitive work remains knowledge acquisition, learning, memory consolidation, planning, perception, action, metacognition, and governance.

## Frozen foundation

The following should remain stable while higher layers are built:

- the exact 244-byte canonical seed and token registry;
- the TOMAGI 1.0 128/64/48-byte ABI and sixteen opcodes;
- content-addressed executable definitions;
- deterministic source-to-cell crosswalks;
- generic ordered `EMIT` byte materialization;
- immutable world commits and ancestry;
- exhaustive/indexed semantic equality;
- exact rational and interval certificate formats introduced in 0.3.

A new core opcode should be considered only when a real workload demonstrates that a capability cannot be represented as a definition/query service without losing correctness or practical viability.

## Stage 1 — complete the world substrate

### 1A. Persistent world and native exact-discrete queries — completed in 0.1

Delivered content-addressed objects, commits, snapshots, state replay, event query, transition, grammar expansion, and lineage reconstruction.

### 1B. Indexes, plans, checkpoints, and scale — completed in 0.2

Delivered immutable secondary indexes, deterministic plans, exact checkpoints, stable batches, full ancestry audit, recovery, corruption detection, and a frozen 10,000-record world.

### 1C. Certified between-tick events — completed in 0.3

Delivered:

- reduced exact rationals;
- closed rational interval arithmetic;
- finite continuous relation expressions;
- affine trajectory point/interval evaluation;
- endpoint sign-change existence certificates;
- derivative-interval monotonicity/uniqueness certificates;
- exact affine root times;
- conservative support and compatibility gating;
- simultaneous exact-root event sets;
- total deterministic event ordering;
- atomic per-field transition merge and conflict rejection;
- an independent `Fraction` baseline; and
- TOMAGI integer-anchor comparison.

### 1D. Piecewise validated dynamics and event transactions — next

Implement **World & Query Kernel 0.4** with these acceptance criteria:

1. Piecewise-affine trajectories whose segments are immutable content-addressed records.
2. Validated-step envelopes for selected nonlinear updates, with explicit local truncation/error intervals rather than hidden floating-point tolerances.
3. An interval-time index that prunes relation/segment candidates while returning byte-identical semantic certificates to exhaustive enumeration.
4. Event-set transaction commits that bind the pre-world commit, event certificates, merged transition, post-state, new trajectory segment, and lineage.
5. Post-event continuation: a query can cross an event-set commit and continue on the successor trajectory.
6. Deterministic handling of two event sets at the same time when their transition fields are conflict-free; explicit rejection otherwise.
7. Independent trusted piecewise baseline and corruption/replay tests.
8. A benchmark with at least 1,000 trajectory segments, 10,000 relations, and multiple simultaneous event sets.

### 1E. Stable World & Query Kernel 1.0

Freeze a public API only after 0.4 proves event transactions and post-event continuation. Required native calls should include:

```text
definition_at
verify_definition
state_at
trace
next_event
next_event_set
events_in_support
compatible
commit_event_set
reconstruct
audit
```

The 1.0 release should publish semantic certificate schemas, exhaustive/indexed equivalence rules, resource limits, recovery procedures, and a large clean-replay corpus.

## Stage 2 — TOM Learner

The learner is the first major missing AGI component. It should not mutate authoritative definitions directly. It should operate through a proposal/test/commit cycle:

```text
observation
-> candidate entities and relations
-> candidate executable definitions
-> predictions
-> held-out tests and counterexamples
-> uncertainty and provenance record
-> accept/reject decision
-> content-addressed commit
```

### Learner 0.1: supervised rule induction

Start with finite symbolic and numerical domains where ground truth is available. The learner should infer affine relations, support bounds, compatibility predicates, and transition patches from demonstrations.

Acceptance criteria:

- train/validation/test separation is explicit and hashed;
- induced definitions compile without host special cases;
- held-out prediction exceeds a declared baseline;
- false rules remain hypotheses and are not committed as verified definitions;
- every accepted rule has provenance and counterexample history;
- replay produces identical candidate and decision records.

### Learner 0.2: active experiment selection

The learner chooses observations that maximally distinguish competing hypotheses under explicit deterministic acquisition criteria. It must record alternatives, expected information gain or elimination score, actual result, and posterior hypothesis set.

### Learner 0.3: compositional transfer

Test whether learned definitions can be reused in unseen combinations and domains without retraining the entire substrate.

## Stage 3 — memory architecture

Hashes and lineage provide identity but not cognitive memory. Build four explicit stores:

- semantic memory: verified facts, concepts, and rules;
- episodic memory: time-indexed event and observation histories;
- procedural memory: compiled skills and plans;
- working memory: bounded goals, hypotheses, and intermediate results.

Required operations include retrieval by support, relation, provenance, recency, causal ancestry, and goal relevance. Consolidation must create new derived definitions without deleting source episodes. Forgetting should mean policy-controlled retrieval suppression or archival, never silent identity mutation.

## Stage 4 — planner and agent loop

A TOM agent needs an explicit closed loop:

```text
goal
-> retrieve world state and relevant definitions
-> generate candidate plans
-> simulate predicted events and event sets
-> score costs, constraints, and uncertainty
-> choose an action requiring permitted capability
-> execute through a sandboxed adapter
-> record observation
-> update hypotheses/world
-> replan
```

Planner 0.1 should begin with deterministic finite tasks and exact simulators. Planner 0.2 should handle uncertain intervals and contingent branches. Planner 0.3 should learn reusable procedural definitions.

The planner must not hide action policy inside TOMAGI opcode semantics. Goals, costs, permissions, and approval conditions are typed records.

## Stage 5 — grounded perception

Perception adapters translate raw modalities into observations and hypotheses. They are not automatically authoritative.

Recommended order:

1. text and structured documents;
2. simple 2D synthetic vision with exact scene ground truth;
3. audio event streams;
4. multimodal temporal scenes;
5. physical sensors in a sandbox.

Each adapter should emit:

```text
source bytes/hash
observation time interval
entities and properties
spatial/temporal relations
confidence or measurement interval
candidate definition links
provenance
```

The deterministic substrate processes uncertainty explicitly; it must not pretend that a probabilistic detector output is an exact fact.

## Stage 6 — metacognition and governance

Build visible, auditable control rather than a hidden runtime safety mode:

- capability permissions;
- resource and time budgets;
- human approval gates;
- action scopes;
- rollback and branch selection;
- contradiction alerts;
- uncertainty thresholds declared in policy records;
- audit queries and signed release manifests;
- shutdown authority outside the agent's mutable world.

TOMAGI can remain no-failsafe at the transition algebra while deployment is constrained by explicit external enforcement and typed governance programs.

## Stage 7 — broad capability evaluation

Only after learner, memory, planner, perception, and governance exist should the project evaluate broad generality.

A credible evaluation program needs:

- unseen domains;
- long-horizon tasks;
- compositional transfer;
- contradiction and correction;
- tool use;
- grounded interaction;
- resource-limited planning;
- adversarial and out-of-distribution cases;
- independent baselines;
- ablations showing which TOM layers matter;
- complete replay artifacts.

Passing a small deterministic benchmark is evidence for that benchmark, not AGI.

## Immediate 0.4 work plan

### Workstream A — piecewise trajectory records

Define segment schemas, continuity conditions, domain partitioning, source-program binding, and exact state selection at shared boundaries.

### Workstream B — validated nonlinear step profile

Choose a narrow first profile, such as polynomial discrete updates with interval Jacobian bounds. Prove enclosures against high-precision independent calculations. Do not introduce unrestricted floating-point tolerances.

### Workstream C — interval candidate index

Index by active-time interval, support bounds, relation field dependencies, and trajectory segment. Indexed and exhaustive query certificates must have equal semantic event sets.

### Workstream D — event-set transactions

Commit:

```text
parent world hash
pre-state certificate
ordered event-set certificate
transition merge certificate
post-state
successor trajectory segment
lineage and provenance
```

### Workstream E — benchmark and falsification

Generate a literal benchmark with simultaneous roots, near misses, incompatible roots, interval overestimation cases, tangent contacts, conflicting transitions, corrupted segments, and recovery cases.

## Exit condition before learner work

Begin the learner only when the world kernel can:

- represent observations and hypotheses;
- query exact and interval events;
- atomically commit event sets;
- continue trajectories after events;
- retrieve/audit ancestry;
- reject corruption and transition conflicts; and
- reproduce exhaustive and indexed semantics from a clean archive.

At that point the substrate will be sufficiently complete for a learner to change world knowledge without bypassing the deterministic authority chain.

## Honest status after 0.3

| Closure | Status |
|---|---|
| Seed-to-program-to-bytes | Complete for Genesis profile |
| Persistent world and exact-discrete queries | Implemented |
| Immutable indexing/checkpoints/audit | Implemented |
| Exact affine interval crossing | Implemented |
| Exact-root simultaneous event sets | Implemented |
| Event-set persistent transaction and continuation | Missing; 0.4 |
| Autonomous knowledge acquisition | Missing |
| Cognitive memory | Missing |
| General planner/agent | Missing |
| Grounded multimodal perception | Missing |
| AGI evidence | Not established |

The correct next move is to complete 0.4, then start a narrowly falsifiable learner. The core machine should remain frozen unless those workloads expose a concrete irreducible defect.
