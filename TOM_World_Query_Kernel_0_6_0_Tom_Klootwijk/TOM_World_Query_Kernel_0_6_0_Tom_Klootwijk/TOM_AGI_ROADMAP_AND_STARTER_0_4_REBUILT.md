# TOM AGI roadmap — corrected through World & Query Kernel 0.4.1

## Trust status

The previous 0.4.0 line is superseded. This roadmap continues only from corrected WQK 0.3, archive SHA-256:

```text
a7103ec92596fd54198e4a902f078712cf8eafcdf1e45320bbdc02dd53947278
```

The corrected interval source hash is:

```text
ea7b3ff2127e8ee7a696eb45e84ae9efdbca7c10c532617c51888fb13cd39f6d
```

No old 0.4 code or fixture is an authority for the corrected line.

## Completed foundation

| Milestone | Delivered capability | Status |
|---|---|---|
| TOMAGI 1.0 | Fixed 128/64/48-byte deterministic machine, sixteen opcodes, Python/C execution | frozen |
| TOM Genesis | Canonical seed, executable definitions, deterministic lowering, generic emitted bytes | complete for declared profile |
| WQK 0.1 | Content-addressed world, native discrete state/event queries, lineage | complete |
| WQK 0.2 | Immutable indexes, query plans, checkpoints, batch queries, 10,000-record benchmark | complete |
| corrected WQK 0.3 | Exact rational intervals, certified affine crossings, simultaneous event sets, independent baseline | complete and pinned |
| WQK 0.4.1 | Solver-derived open-segment continuation, atomic state/rate changes, append-only journal, reconstruction | complete corrective release |

## Corrected 0.4.1 invariant

Future segment boundaries are not source data. The world declares only a final horizon. Each successor trajectory is generated from one accepted event certificate and remains open to that horizon until the next query discovers a root.

This invariant must remain in every later learner, planner, and action layer:

```text
proposal is not authority
expected result is not query input
event certificate precedes transition
transition precedes successor
hash-verified promotion precedes world authority
```

## Next milestone: TOM Learner 0.1 / WQK 0.5

### Goal

Build the first deterministic observation-to-hypothesis pipeline without allowing inferred rules to become authoritative silently.

### Required object types

```text
observation
observation set
train/validation/holdout assignment
hypothesis family
candidate relation
candidate transition
fit certificate
residual certificate
counterexample
contradiction
acceptance policy
promotion transaction
rejected-candidate lineage
```

### First supported hypothesis family

Begin with exact rational affine and piecewise-affine relations because 0.3/0.4.1 already provide trusted certification and continuation semantics.

Given observations `(t_i, y_i)`, the learner may propose:

```text
y(t) = a*t + b
```

or a finite piecewise partition. Coefficients must be exact reduced rationals. The learner must publish:

- the deterministic data split;
- candidate enumeration order;
- exact residuals on train, validation, and holdout;
- complexity cost;
- competing candidates;
- counterexamples and contradictions;
- an explicit acceptance decision; and
- a promotion transaction whose parent world hash is current.

### Nonnegotiable acceptance conditions

1. A held-out set must not influence candidate fitting or boundary selection.
2. Candidate boundaries may not be copied from expected events.
3. Every accepted candidate must replay through the corrected event solver.
4. Promotion must be atomic and content-addressed.
5. Failed candidates and counterexamples remain in lineage.
6. Repeating the same observation set, policy, seed, and budget must reproduce all candidate and promotion bytes.
7. A separate baseline must reproduce the selected coefficients and residuals.
8. A mutation or stale-parent promotion must reject.

### Starter benchmark

Use several exact rational trajectories with hidden affine coefficients, controlled outliers, and one genuine change point. Required reports:

```text
exact recovery rate
holdout residuals
false promotion count
counterexample detection
indexed versus exhaustive candidate work
promotion replay hash
```

The benchmark must include unseen trajectories; reproducing a source-authored fixture is insufficient evidence of learning.

## Later stages

### TOM Memory 0.1

Add semantic, episodic, procedural, working, source, and counterfactual memory as typed world records. Retrieval plans must be explicit and independently checkable.

### TOM Planner 0.1

Add goals, candidate actions, preconditions, effects, costs, resources, and bounded search. Plans are proposals until verified by a simulation certificate and approved action transaction.

### TOM Perception adapters

Convert text, image, audio, or sensor streams into observations with provenance and uncertainty. Adapters remain outside the authoritative substrate until their outputs are promoted through explicit policies.

### TOM Agent 0.1

Combine goals, planning, tools, working memory, observation feedback, and replanning. Permissions and action boundaries must be external and explicit; the frozen TOMAGI transition core remains no-failsafe.

### Broad capability evaluation

AGI claims require transfer to unseen domains, continual learning, contradiction handling, planning, tool use, grounded feedback, and robust governance. None is established by WQK 0.4.1.

## Recommended immediate work order

1. Freeze and independently archive the corrected 0.4.1 release.
2. Add observation and hypothesis schemas without changing TOMAGI.
3. Implement exact affine coefficient induction and a completely separate baseline.
4. Add deterministic split and promotion policies.
5. Prove stale-parent, data leakage, overfit, and contradiction rejection.
6. Run an unseen holdout benchmark.
7. Only then extend to piecewise candidate induction.

The central rule for the next stage is:

> Learning may propose. Only a verified, content-addressed, parent-bound promotion transaction may change the authoritative world.
