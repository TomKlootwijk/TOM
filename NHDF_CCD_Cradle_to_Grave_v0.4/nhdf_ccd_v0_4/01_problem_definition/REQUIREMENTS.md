# NHDF-CCD v0.4 requirements

## Functional requirements

- **FR-001** Determine the earliest contact time in a closed interval or return an explicit non-hit/failure certificate.
- **FR-002** Detect initial overlap separately from a future hit.
- **FR-003** Support conservative broad-phase candidate generation without false-negative pruning for declared shape/motion profiles.
- **FR-004** Dispatch to a declared narrow-phase backend and never treat an unsupported pair as collision-free.
- **FR-005** Preserve a lower and upper TOI bound when an iterative solver is used.
- **FR-006** Separate collision detection from collision response.
- **FR-007** Bound candidate, branch, trace, iteration, and workspace capacities.
- **FR-008** Produce deterministic telemetry and a trace digest under deterministic mode.
- **FR-009** Keep NHDF parity/log-polar/golden-ratio signals outside the safety authority unless independently proven equivalent.

## Non-functional requirements

- **NFR-001 Correctness before speed.** No optimization may change supported outcomes outside declared tolerance.
- **NFR-002 Failure preservation.** Numerical failure, exhausted budget, invalid oracle, unsupported geometry, and capacity exhaustion are visible statuses.
- **NFR-003 Reproducibility.** A release includes reference vectors, tests, benchmark seed, source, build instructions, and hashes.
- **NFR-004 Portability.** The semantic core has no vendor-specific dependency.
- **NFR-005 Privacy and governance.** The runtime does not require personal identifiers; public-safety adapters require lawful purpose, auditability, minimization, and human oversight.

## Supported v0.4 profile

- Translational linear motion: exact sphere-sphere, sphere-plane, AABB-AABB.
- Translational quadratic motion: conditional conservative advancement where a valid separation oracle and speed bound exist.
- Point/sphere against a true or conservatively biased SDF under translation.

## Deliberately unsupported in the executable v0.4 profile

Rotating polyhedra, triangle meshes, deformable self-collision, articulated motion, non-rigid topology changes, neural SDFs without certified error bounds, contact response, friction, and production GPU execution.
