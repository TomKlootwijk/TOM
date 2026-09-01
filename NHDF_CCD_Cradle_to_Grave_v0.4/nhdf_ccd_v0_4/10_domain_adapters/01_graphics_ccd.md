# Graphics and game-engine adapter

## Literal mapping

The event boundary is the geometric separation function between moving bodies. The v0.4 executable directly supports a small primitive subset and supplies the architecture for robust mesh/SDF backends.

## Required production additions

- triangle-mesh broad and narrow phases with exact or inclusion-based predicates;
- rigid rotation and deformable trajectories;
- adjacency filters and self-collision policy;
- simultaneous-contact grouping;
- contact response, friction, restitution, sleeping, stacking, and rollback;
- GPU replay and engine-specific determinism.

## NHDF disposition

Log-polar bins may organize scale and approach direction. Local zero sets become pairwise contact manifolds. The bounded BST becomes a candidate/refinement queue. Parity and golden-ratio splits remain ablations. A Klein-bottle chart is only relevant for explicitly non-orientable simulated topology and is not part of ordinary contact correctness.
