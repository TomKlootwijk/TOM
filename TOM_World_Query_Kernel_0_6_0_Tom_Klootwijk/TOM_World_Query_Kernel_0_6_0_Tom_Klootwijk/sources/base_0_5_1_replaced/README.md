# TOM World & Query Kernel 0.5.1 corrective handoff

## TOM Learner 0.1 — seeded TOMAGI authority

This corrective release moves the finite affine learner into the literal seeded
TOMAGI compilation chain:

```text
canonical seed + content-addressed literal definitions
-> verified literal observation sources
-> bounded exact formal learner evaluation
-> deterministic Cell48 lowering
-> equal Python/C TOMAGI execution traces
-> ordered EMIT records
-> generic byte materialization
```

The older `tom_learner05` Python implementation remains an independent reference
oracle and evidence-store implementation. It is not the causal authority for the
corrected result. This release does not change TOMAGI ABI 1.0 and does not claim
AGI.

## Trust boundary

`sources/TOM_LITERAL_HANDOFF_0_4_2.json` pins the inherited 47-file base.
`sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json` then declares the semantic change,
verifies all 44 unchanged files, verifies both the preserved old bytes and new
bytes of the three replacements, and pins the new formal authority sources.

Run:

```bash
PYTHONPATH=src/python python3 -m tom_learner05 verify-corrective-handoff .
```

Pinned corrective handoff hash:

```text
sha256:53951284853681ce239d07ce2ce783250ea78b3457fd221a43d88bd90344f4bf
```

## What is implemented

- exact rational observation records and strict nested content hashes;
- a static content-addressed formal learner program used as compilation input;
- strict seed, token-registry, schema, definition, dependency, type, provenance,
  budget, and source-byte validation;
- deterministic `train / validation / holdout` split using only IDs and declared policy;
- exact affine family `y = a*t + b`;
- candidate generation from all distinct-input unordered training pairs;
- train-only deterministic rank and selection;
- validation and holdout acceptance gates that cannot alter coefficients;
- exact residual metrics, counterexamples, and contradiction records;
- independent standard-library `fractions.Fraction` baseline;
- accepted learned definitions with `SDF0@Def` residual semantics;
- rejected-candidate lineage;
- append-only learner overlay with expected-parent promotion transactions;
- complete evidence hash enumeration, strict audit, corruption detection, and reconstruction;
- command-line interface `tom-learner05`;
- a 19-case exact benchmark;
- causal TOMAGI/EMIT production of the learner result and release documents;
- authenticated trace materialization and byte-identical Python/C execution.

## Benchmark result

```text
Datasets:                    19
Exact positive cases:       12 / 12 recovered
Negative cases:              7 / 7 rejected
False promotions:            0
Coefficient recovery errors: 0
Independent baseline:        equal for all 19
Leakage probes:              pass
Formal evaluation steps:     131478
Compiled Cell48 records:     19540
Materialized result SHA-256:  dd9a0c20c8f721c764580f6655bb509001a7ef59000d0cd1bd5826971b72cb82
```

The negative cases include train, validation, and holdout outliers; a piecewise change; contradictory exact observations; constant-input underdetermination; and excessive model complexity.

## Authority model

The seeded formal program is the authority for learner computation. A learning
certificate remains only a proposal. It becomes visible in the append-only
learner overlay only through:

```text
expected parent commit
+ complete immutable evidence set
+ explicit acceptance decision
+ accepted definition or rejection lineage
-> promotion transaction
-> snapshot
-> commit
-> atomic HEAD update
```

A stale parent rejects. Rejected sessions retain all candidate, residual, counterexample, contradiction, and decision records.

## Reproduce

```bash
# Build and validate the corrected learner, inherited stack, formal artifact,
# strict store audit, and clean source-capsule replay.
make validate-learner05

# Produce the deterministic release ZIP and independently replay it.
make package-learner05

# Inspect a data set.
PYTHONPATH=src/python python3 -m tom_learner05 validate-dataset \
  examples/learner05/datasets/dataset_clean_half.json

# Learn one proposal.
PYTHONPATH=src/python python3 -m tom_learner05 learn \
  examples/learner05/datasets/dataset_clean_half.json

# Audit the append-only overlay.
PYTHONPATH=src/python python3 -m tom_learner05 audit \
  examples/learner05/learner_store
```

## Package map

- `sources/TOM_LITERAL_HANDOFF_0_4_2.json` — literal-only inherited base.
- `sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json` — explicit old/new corrective boundary.
- `sources/base_0_4_2_replaced/` — preserved prior bytes for all replacements.
- `spec/TOM_SEEDED_COMPILATION_1_0.md` — normative source-to-byte semantics.
- `spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md` — learner integration corrigendum.
- `docs/LATEST_TURN_VALIDATION_0_4_1.md` — independent latest-turn validation and exact unavailable-upload limitation.
- `spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5.md` — superseded 0.5.0 profile retained for history.
- `spec/tom_learner_affine_0_5.schema.json` — strict observation-set schema.
- `src/python/tomagi/formal.py` — generic bounded exact formal evaluator.
- `examples/learner05/learner05_affine_authority.formal.json` — executable learner semantics.
- `examples/learner05/learner05_formal_authority.literal.json` — seeded definition graph.
- `examples/learner05/learner05_formal_authority.tmg` — compiled 19,540-cell program.
- `src/python/tom_learner05/` — model, split, affine learner, independent baseline, store, audit, CLI.
- `examples/learner05/benchmark_plan.json` — literal benchmark semantics.
- `examples/learner05/datasets/` — 19 content-addressed input data sets.
- `examples/learner05/learner_store/` — 20-commit accepted/rejected overlay.
- `validation/learner05/` — benchmark, leakage, baseline, audit, reconstruction, test, clean-replay, and release-artifact evidence.
- `TOM_WORLD_QUERY_KERNEL_0_5_RELEASE.md` — release overview.
- `TOM_AGI_ROADMAP_AND_STARTER_0_5.md` — updated roadmap.

## Evidence boundary

This release demonstrates deterministic exact affine rule induction from 19
finite exact-rational data sets under one fixed bounded profile. It does not
demonstrate noisy or open-domain learning, broad program synthesis,
natural-language learning, multimodal perception, autonomous planning, physical
GPU learner execution, or AGI.
