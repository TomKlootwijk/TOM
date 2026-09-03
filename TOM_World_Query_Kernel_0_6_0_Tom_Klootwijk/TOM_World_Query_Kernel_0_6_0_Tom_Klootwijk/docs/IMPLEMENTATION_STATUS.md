# TOM World & Query Kernel 0.6 — Implementation status

## Frozen substrate and repaired kernel

| Layer | Status | Evidence |
|---|---|---|
| Canonical seed | Preserved | Exact 244 bytes and fixed SHA-256 |
| TOMAGI ABI | Preserved | 128-byte header, 64-byte state, 48-byte cell, 16 opcodes |
| C wrap semantics | Repaired and tested | Extreme signed-32 operands agree with Python without C signed-overflow dependence |
| Reserved header words | Repaired and tested | Python and C reject every one of six nonzero reserved words |
| Formal intermediate budgets | Repaired and tested | Every recursive result and fold accumulator is bounded before parent use |
| Publication CAS | Repaired and tested | Same-host thread/process lock covers read, verify, write, and atomic `HEAD` replacement |
| Packaging authority | Repaired | Pinned source boundary, internal inventory, two builds, deterministic ZIP, final replay |

## Query and world layers retained

WQK 0.1 through corrected 0.4.1 remain included: content-addressed worlds, immutable indexes, exact state and event queries, exact rational interval crossing, simultaneous event sets, corrected open-segment continuation, event journals, and lineage reconstruction.

## Learner 0.1 authority retained

WQK 0.5.1 places exact affine proposal, train-only selection, validation/holdout gates, contradictions, and counterexamples in a static formal program. WQK 0.5.2 places acceptance/rejection, evidence enumeration, parent binding, snapshot, transaction, commit, and publication order in a second static formal program.

## Learner 0.2 delivered

| Capability | Status |
|---|---|
| Exact polynomial family | 34 finite candidates, degree at most two |
| Piecewise-affine family | 21 candidates, one breakpoint and two branches |
| Finite transition tables | 27 complete symbolic tables |
| Bounded expression trees | 39 candidates under explicit depth/complexity limits |
| Train-only search | Implemented in formal authority |
| Validation and holdout gates | Implemented without candidate generation leakage |
| Contradictions/counterexamples | Content-addressed records |
| Ambiguity | Explicit rejection record; no hidden tie-break |
| Supersession | Explicit target hash |
| Regression impact | All twelve pinned prior definitions checked |
| Independent oracle | Separate `fractions.Fraction` implementation; all outcomes equal |
| Promotion continuation | Sixteen publications, sequence 20 through 35 |
| Immutable reconstruction | Nine accepted and seven rejected sessions reconstructed |

Canonical benchmark:

```text
families 4 | candidates 121 | data sets 16
accepted 9 | rejected 7 | ambiguities 3 | false promotions 0
```

Core validation records 283 passing tests, eighteen checks after the release and
validation-handoff artifacts are included, twenty deterministic rejection
cases, and exact Python/C trace and EMIT equality for both formal authority
programs.

## Current partial or missing layers

- interval-valued/noisy observations and declared measurement models;
- calibration, coverage, distribution shift, and robust finite scoring;
- semantic, episodic, procedural, and working-memory policies;
- goal decomposition, planning, tool permissions, action, and replanning;
- grounded text/image/audio/sensor adapters;
- multi-host consensus for concurrent publication;
- physical GPU execution evidence for the learner;
- broad unseen-domain generalization or AGI evidence.
