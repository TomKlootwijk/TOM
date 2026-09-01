# GPU port plan

## Rule zero

The GPU backend is an acceleration of the CPU semantics, not a new definition of CCD. It must reproduce certificates within declared tolerance and preserve every failure state.

## Pipeline

1. Structure-of-arrays body state and swept bounds.
2. Deterministic or high-throughput broad phase.
3. Candidate compaction with prefix sums; overflow bit and required count are always returned.
4. Backend bucketing by pair/motion type.
5. Batched exact primitive solvers.
6. Work-queue conservative advancement or inclusion-based mesh CCD.
7. Earliest-TOI reduction with deterministic tie policy.
8. Certificate and telemetry emission.

## NHDF-specific placement

- Log-polar bins may group queries by separation/approach direction to reduce divergence.
- Parity may be a low-cost corruption/anomaly signal but cannot replace CRC/ECC or a collision predicate.
- Golden-ratio interval splitting is an optional queue-shaping experiment; midpoint and earliest-first baselines remain mandatory.
- Matrix units may accelerate batched transforms or learned broad-phase proposals, but integer parity and geometric predicates use their matching instruction paths.

## Acceptance gate

- Zero false negatives on exact datasets for supported profiles.
- CPU/GPU classification equivalence and bounded TOI error.
- Reproducible overflow behavior.
- No silent fast-math changes to predicate signs.
- Measured speed, power, memory, and thermal behavior on the actual target.
