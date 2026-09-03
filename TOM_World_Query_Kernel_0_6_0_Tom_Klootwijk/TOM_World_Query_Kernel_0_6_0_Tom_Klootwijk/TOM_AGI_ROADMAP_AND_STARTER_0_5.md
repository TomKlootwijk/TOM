# TOM AGI Roadmap — status through World & Query Kernel 0.5

> **0.5.1 correction:** Treat this file as historical 0.5.0 planning context.
> Any continuation must first follow
> `docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md` and the two normative 0.5.1
> specifications. Learner semantics belong in content-addressed literal formal
> definitions executed during seeded TOMAGI compilation, not in a bespoke host
> learner.

## Current implemented stack

```text
TOMAGI 1.0
  fixed 128/64/48-byte deterministic execution ABI

TOM Seeded Compilation / Genesis
  executable content-addressed definitions -> Cell48 -> EMIT bytes

World & Query Kernel 0.1
  persistent world, native state/event queries, lineage

World & Query Kernel 0.2
  immutable indexes, plans, checkpoints, audit, 10,000-record fixture

World & Query Kernel 0.3
  exact rational interval relations and certified simultaneous event sets

World & Query Kernel 0.4.1 corrective rebuild
  solver-derived piecewise continuation, common-prestate transitions,
  immutable seals, journal reconstruction

World & Query Kernel 0.5 / TOM Learner 0.1
  exact observations -> isolated evidence splits -> affine hypotheses
  -> counterexamples -> explicit acceptance -> parent-bound promotion
```

The canonical root remains the exact 244-byte TOM seed. The TOMAGI ABI remains frozen.

## Why learning starts narrowly

The substrate can execute declared definitions deterministically, but AGI requires a mechanism for adding defensible new definitions. The dangerous shortcut would be:

```text
model proposes rule -> rule becomes truth
```

Version 0.5 instead establishes:

```text
observations
-> immutable evidence identity
-> label-independent split
-> train-only induction
-> validation gate
-> untouched holdout audit
-> contradictions and counterexamples
-> proposal certificate
-> explicit parent-bound promotion
```

This is cognitive infrastructure, not broad intelligence. It proves that a learned proposal can be kept separate from authority and rejected without erasing its lineage.

## Completed milestone: Learner 0.1

Delivered:

- canonical exact-rational observations;
- strict observation-set schema and nested content hashes;
- deterministic ID-only train/validation/holdout partition;
- exact affine `y=a*t+b` candidate enumeration from training pairs;
- train-only deterministic rank and selection;
- explicit validation, holdout, contradiction, and complexity gates;
- exact residual evidence and counterexample records;
- independent `fractions.Fraction` baseline;
- learned `SDF0@Def` relation records;
- append-only accepted/rejected session store;
- stale-parent protection, corruption audit, and reconstruction;
- 19-case benchmark with 12 exact recoveries and 7 correct rejections;
- zero false promotions in the declared suite.

## Next milestone: Learner 0.2 / WQK 0.6

### Purpose

Generalize from one affine family to a finite, typed hypothesis-family registry while preserving evidence isolation and deterministic authority.

### Candidate families

1. exact polynomial models under explicit degree and coefficient budgets;
2. piecewise-affine models with change-point candidates derived from training evidence;
3. finite transition tables over typed symbolic inputs;
4. small bounded expression trees over declared operators.

### Required records

- hypothesis-family definition and version;
- search-space budget;
- training derivation certificate;
- validation selection/gate certificate;
- holdout audit;
- ambiguity record when multiple candidates survive;
- minimal counterexample set;
- supersession and contradiction relation to earlier definitions;
- promotion impact report over all previously accepted tests.

### Exit criteria

- no target leakage under same-ID validation/holdout mutation probes;
- exact agreement with independent baselines for each family;
- zero false promotion on adversarial negative fixtures;
- deterministic ambiguity rather than hidden tie breaking;
- bounded search termination;
- accepted definitions reproduce held-out predictions and do not invalidate pinned prior behavior;
- clean archive replay of every promoted/rejected session.

## Later milestones

### Learner 0.3 — noisy evidence and explicit uncertainty

Add exact interval/noise models, calibration records, confidence as typed evidence, and acceptance rules that remain visible. No hidden confidence threshold may alter TOMAGI opcode behavior.

### Memory 0.1

Build semantic, episodic, procedural, and working-memory indexes over content-addressed definitions and lineage. Add contradiction-aware retrieval, consolidation, and provenance-preserving supersession.

### Planner 0.1

Represent goals, costs, resources, preconditions, effects, candidate plans, simulation certificates, action permissions, and replanning after observed outcomes.

### Perception adapters

Translate raw text, image, audio, and sensor streams into typed observation proposals. Perception output remains non-authoritative until grounded, cross-checked, and promoted.

### Agent integration

Combine learner, memory, planner, tools, observations, and governance. Evaluate transfer, novelty handling, long-horizon behavior, metacognition, and safe action under independent benchmarks.

## AGI claim gate

No AGI claim is supported by deterministic replay alone. A general-agent claim requires broad empirical evidence across unseen domains, learning, memory, planning, perception, action, self-correction, and governance. The current achievement is a stronger substrate boundary: new knowledge can now be proposed, tested, rejected or promoted through explicit reproducible evidence.
