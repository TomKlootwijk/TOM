# Engine integration contract

The engine owns the world step, body state, broad phase, object lifetime, and policy. The v0.5 library owns only feature-query evaluation, certificates, event grouping, and a pedagogical translational impulse example.

## Required ordering

1. Freeze a monotonically identified input snapshot.
2. Build conservative swept broad-phase candidates.
3. Expand candidates into supported primitive or feature queries.
4. Execute CCD and retain all non-miss results, including inconclusive and resource-exhausted results.
5. Sort by `(toi_lower, toi_upper, pair_id, query_type, feature_ids)`.
6. Group overlapping intervals with a declared merge tolerance.
7. Advance no farther than the earliest safe upper bound permitted by engine policy.
8. Build/manifold contacts in the host engine.
9. Resolve or conservatively halt; do not treat an unresolved result as free motion.
10. Record certificate digests, capacities, timing, and fallback counts for replay.

## Safety boundary

The bundled impulse routine is not a complete rigid-body contact solver. It excludes angular impulse, friction, stacking, stabilization, constraint regularization, warm starting, and simultaneous nonlinear solve. Production integration must use a separately validated response system.
