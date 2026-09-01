# Next Experiments After 0.2

## Experiment 1 — Certified bracket and rational event time

Use a trajectory whose residual moves from -2 to +3 without visiting zero. Produce a certificate containing the two exact states, residual bracket, declared interpolation rule, rational event-time interval, solver status, and error bound. Compare with an independent baseline.

## Experiment 2 — Simultaneous event set

Create several relations triggering at one logical tick. Specify priority, compatible commutation, conflicting transitions, and event-set hashing before execution. Prove invariance under record insertion order.

## Experiment 3 — Jitter interval preservation

Add explicit relation intervals and a deterministic one-bit perturbation bound. Verify that the interval cannot change event class or ordering, as required by the TOM-SRS acceptance conditions.

## Experiment 4 — One-million-record index profile

Generate a frozen content-addressed million-record source capsule with hierarchical transaction sharding. Preserve indexed/exhaustive semantic samples while avoiding a million-file packaging model. Publish deterministic I/O and candidate work counts separately from wall-clock measurements.

## Experiment 5 — Candidate-definition learner 0.1

Provide finite input/output examples for integer expressions. Enumerate a bounded expression grammar, store every candidate and counterexample, use held-out tests, and commit only the unique surviving definition as a hypothesis or verified rule.

## Experiment 6 — Contradiction and supersession

Commit incompatible factual definitions with source evidence. Add explicit contradiction records and a policy that does not silently select either. Verify historical queries before and after a superseding commit.

## Experiment 7 — Goal-directed planner

Define a small deterministic environment with actions and costs. Implement breadth-first or A* search as explicit query and definition records, execute through a sandbox adapter, observe outcomes, and replan after a declared action failure.

## Experiment 8 — Controlled-language grounding

Parse a synthetic language into observations and candidate relations with exact source spans. Keep outputs as hypotheses until evidence checks commit them. Measure extraction precision and replay stability.
