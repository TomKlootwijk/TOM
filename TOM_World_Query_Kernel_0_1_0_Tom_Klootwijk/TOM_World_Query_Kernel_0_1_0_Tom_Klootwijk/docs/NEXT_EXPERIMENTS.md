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
