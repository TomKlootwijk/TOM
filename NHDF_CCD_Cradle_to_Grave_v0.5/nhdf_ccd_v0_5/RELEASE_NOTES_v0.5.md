# Release notes — NHDF-CCD v0.5

Release date: 2026-09-01

## Advancement

v0.5 moves from primitive-only continuous collision detection toward a mesh-feature reference. It adds affine vertex–face and edge–edge queries, cubic coplanarity candidates, geometric witness checks, a conservative distance-rate fallback for persistent or ill-conditioned coplanarity, rigid-motion speed bounds, deterministic interval event grouping, and an intentionally restricted response example.

The evidence layer now includes a rational-coordinate parser and complete evaluation of two locally vendored public Sample-Queries CSV files. Their original README and MIT license are preserved. Per-query statuses and digests are retained in CSV; mismatches and inconclusive outcomes are not filtered.

## Post-validation TOMAGI bridge

`14_tomagi_ccd_bridge/` adds a literal, seed-bound q4 vertex-face fixture. Its
definition graph constructs executable State64/Cell48 kinematics and support
guards, compiles to `.tmg`, selects the runtime HIT route, and reconstructs the
certificate from ordered byte-mode EMIT records. Two isolated rebuilds and
replays are required to match byte-for-byte. This is a bounded integration
proof, not a claim of general root isolation or arbitrary-mesh CCD.

## Executed release checks

- Python unit and property-style tests.
- Seeded synthetic vertex–face and edge–edge tunnelling benchmarks.
- Public-corpus parser and solver evaluation.
- Rigid-motion inequality audit.
- Momentum/energy/sign audit of the limited impulse routine.
- Deterministic event grouping benchmark.
- C++17 compilation and smoke test.
- Parser fuzz exercise.
- LaTeX build, PDF structural checks, text extraction, font inventory, and representative-page rasterization.
- ZIP integrity and SHA-256 manifests.

## Non-conformance notices

The CUDA file is a translation skeleton and was not granted conformance. The algebraic feature solver uses floating-point roots and is not a robust exact-predicate implementation. The response routine is not a production contact solver. The package does not validate universal-substrate, medical, quantum, optical, chemical, biological, or cosmological claims.
