# Roadmap to v0.6

The next release gate is exactness and mesh integration, not additional substrate metaphors.

1. Replace floating-point cubic root acceptance with interval arithmetic or exact-predicate root isolation.
2. Add robust degenerate feature classification: persistent coplanarity, collinearity, shared vertices, zero-area faces, and zero-length edges.
3. Build a half-edge mesh adapter, adjacency filtering, self-collision exclusions, and deterministic broad-phase feature extraction.
4. Add rotating rigid-body feature trajectories or conservative screw-motion bounds.
5. Compare against at least two established CCD implementations on complete public corpora.
6. Implement CPU/GPU differential replay using identical certificates and failure semantics.
7. Add manifold construction and a separately verified constrained response layer.
8. Seek independent reproduction before raising the conformance level.
