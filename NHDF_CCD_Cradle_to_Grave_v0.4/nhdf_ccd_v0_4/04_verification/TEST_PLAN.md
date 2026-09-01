# Verification and validation plan

## Layer A - mathematical/unit tests

- Exact roots: sphere-sphere, sphere-plane, swept AABB.
- Initial contact and initial overlap.
- No-hit and moving-away cases.
- High-speed tunneling missed by endpoint-only discrete checks.
- Conservative advancement against a true SDF.
- Quadratic translational motion using a conservative speed bound.
- Invalid Lipschitz/tolerance contracts.

## Layer B - architecture/property tests

- Broad phase retains a real collision and prunes distant pairs.
- Candidate capacity exhaustion is explicit.
- Unsupported shape pairs remain explicit.
- NHDF hint enable/disable does not change the classification.
- Midpoint and golden-ratio interval policies agree on the tested hit class.
- Deterministic inputs produce identical trace digests.

## Layer C - differential testing required before v1.0

- Run millions of vertex-face and edge-edge cases from an exact TOI dataset.
- Compare with at least two independent robust implementations, such as Tight Inclusion and IPC Toolkit.
- Include near-coplanar, grazing, parallel, duplicate-vertex, zero-area, and scale-extreme cases.
- Test broad and narrow phases together; a correct narrow phase cannot repair a false-negative broad phase.
- Use sanitizers, multiple compilers, multiple floating-point modes, and CPU/GPU replay.

## Layer D - application validation

A renderer, robot, simulator, or manufacturing tool must define its own missed-contact cost, false-positive cost, latency, memory, determinism, and recovery policy. A domain adapter does not inherit correctness by analogy.
