# Adversarial CCD case catalog

The following cases are mandatory for the next validation stage:

1. Tangential contact with a repeated polynomial root.
2. Near-parallel edge-edge motion and nearly coplanar vertex-face motion.
3. Contact exactly at `t=0` and `t=1`.
4. Initial overlap with zero or ambiguous normal.
5. Degenerate triangles, duplicate vertices, zero-length edges, and coincident features.
6. Extremely small and large coordinate scales in the same scene.
7. Rotational motion whose closest feature changes discontinuously.
8. Accelerated motion with a loose speed bound that exhausts iteration budget.
9. Approximate or neural SDF that overestimates distance.
10. Broad-phase integer overflow, NaN/Inf propagation, queue overflow, and deterministic tie handling.
11. Multiple simultaneous impacts and contact islands.
12. Self-collision adjacency filtering for deformable meshes.
