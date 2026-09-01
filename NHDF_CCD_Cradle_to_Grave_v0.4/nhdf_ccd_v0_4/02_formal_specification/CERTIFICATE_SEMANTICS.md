# Certificate semantics

- `HIT`: a supported backend found contact in the step. Exact solvers return a point TOI; iterative solvers return a conservative bracket.
- `NO_HIT`: the backend certified positive separation throughout the interval under its stated contracts.
- `INITIAL_OVERLAP`: separation is negative at the start. The caller must use depenetration or rollback policy; CCD alone does not resolve it.
- `INCONCLUSIVE`: a possible contact could not be safely classified within numerical, iteration, or interval bounds.
- `UNSUPPORTED`: no valid backend exists for the declared pair/motion.
- `INVALID_INPUT`: a contract, tolerance, value, or bound is invalid.
- `CAPACITY_EXCEEDED`: a bounded resource limit was reached before complete classification.

Only `NO_HIT` permits unconstrained advancement through the full step. `HIT` permits advancement no later than the conservative upper TOI. Every other status requires caller policy and must be visible in telemetry.
