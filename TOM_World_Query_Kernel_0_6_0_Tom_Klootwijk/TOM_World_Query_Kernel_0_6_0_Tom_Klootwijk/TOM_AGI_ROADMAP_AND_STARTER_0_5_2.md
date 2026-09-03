# TOM AGI Roadmap — status through WQK 0.5.2

## Current stack

```text
TOMAGI 1.0
  frozen deterministic 128/64/48-byte ABI

TOM Genesis
  executable seeded definitions -> Cell48 -> authenticated EMIT bytes

WQK 0.1-0.4.1
  persistent query world, indexes, exact events, corrected piecewise continuation

TOM Learner 0.1 / WQK 0.5.1
  affine induction moved into a static bounded formal program

WQK 0.5.2
  acceptance, evidence transaction, promotion, snapshot, commit, and parent-bound
  publication moved into a second static bounded formal program
```

## Corrective roadmap discipline

Capability expansion is subordinate to authority closure. A new cognitive
layer may not count as implemented when its domain decisions are hidden in host
Python while TOMAGI merely transports the final bytes.

Each future milestone must separate:

```text
formal authority
independent oracle
mechanical host services
```

The formal authority contains domain law. The oracle can falsify it. Mechanical
host services may validate, hash, compile, execute, persist immutable records,
and perform explicit compare-and-swap publication, but may not silently decide
semantic acceptance or rewrite authority.

## Completed: Learner 0.1 authority closure

### 0.5.1 — proposal authority

- exact-rational observations;
- label-independent evidence splits;
- train-only affine candidate generation and selection;
- validation and holdout gates;
- contradiction and counterexample evidence;
- accepted `SDF0@Def` relations;
- static formal learner executed by seeded TOMAGI.

### 0.5.2 — promotion authority

- complete verification of learner, result, policies, observations, and rows;
- explicit acceptance decision or rejection lineage;
- ordered unique evidence-hash set;
- parent-bound promotion certificate;
- immutable snapshot, transaction, commit, and publication records;
- generic append-only store and CAS `HEAD`;
- formal/direct/oracle/Python/C/store agreement.

## Next milestone: TOM Learner 0.2 / WQK 0.6

### Purpose

Generalize from the single exact affine family to a finite typed hypothesis-
family registry without weakening the corrected authority boundary.

### Candidate families

1. bounded exact polynomials;
2. bounded piecewise-affine models;
3. finite transition tables over typed symbolic inputs;
4. small bounded expression trees over a declared operation registry.

### Mandatory records

- family definition and semantic version;
- finite search budget and termination certificate;
- train-only derivation evidence;
- validation gate and untouched holdout audit;
- ambiguity record when multiple distinct candidates survive;
- counterexample and contradiction records;
- supersession relation to existing authority;
- regression-impact certificate over all pinned promoted definitions;
- formal promotion transaction under the 0.5.2 authority profile.

### Exit criteria

- every family implemented as static content-addressed formal definitions;
- no target leakage under same-ID validation/holdout mutation probes;
- exact independent-baseline agreement;
- bounded search termination;
- deterministic ambiguity instead of hidden tie-breaking;
- no false promotion on adversarial fixtures;
- stale-parent, missing-evidence, and regression-impact rejection;
- clean source and final-ZIP replay.

## Later milestones

### Learner 0.3 — noisy evidence

Add typed intervals, noise assumptions, calibration and confidence records.
Confidence remains explicit evidence and must not silently modify TOMAGI
opcodes.

### Memory 0.1

Build semantic, episodic, procedural and working-memory indexes with explicit
retrieval certificates, contradiction-aware supersession and provenance.

### Planner 0.1

Represent goals, costs, preconditions, effects, candidate plans, simulations,
action permissions and replanning certificates.

### Perception adapters

Convert text, image, audio and sensor streams into non-authoritative observation
proposals with grounding and source provenance.

### Agent integration

Combine learner, memory, planner, perception, tools and governance under broad
unseen-domain evaluation.

## AGI claim gate

No AGI claim follows from deterministic replay or one learner family. A general
agent claim requires independent empirical evidence for broad transfer,
learning, memory, planning, perception, action, metacognition, self-correction
and governance. Version 0.5.2 is narrower and more important: it ensures that
future learned knowledge cannot become authoritative through an unexamined host
shortcut.
