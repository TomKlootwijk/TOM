# Engine integration contract

A simulation step should follow this order:

1. Predict motion over `[t_n, t_n + dt]` without committing positions.
2. Run broad-phase CCD and all required narrow phases.
3. Reduce to the earliest conservative TOI and form a simultaneous-contact group within a declared time tolerance.
4. Advance only to the permitted time.
5. Invoke a separate contact-response solver.
6. Update velocities/constraints.
7. Re-run CCD for the remaining substep or terminate at a bounded event count.
8. Commit state and telemetry.

## Collision response is separate

Flipping a velocity sign bit is not a general response law. A response adapter must use contact normals, masses/inertias, restitution, friction, constraints, and stacking policy. Fragmentation and plasticity require their own material/failure models.

## Caller policy for non-success statuses

- `INITIAL_OVERLAP`: rollback, depenetrate, or invoke a dedicated overlap solver.
- `INCONCLUSIVE`: reduce the step, switch backend/precision, or fail safe.
- `UNSUPPORTED`: route to a supported backend or reject the scene.
- `CAPACITY_EXCEEDED`: enlarge bounded resources offline or reduce workload; never reinterpret as no-hit.
