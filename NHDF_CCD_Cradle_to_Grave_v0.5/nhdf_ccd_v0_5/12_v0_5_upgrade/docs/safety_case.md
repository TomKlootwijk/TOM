# Safety case fragment

## Claim

Within its declared linear feature profile, the reference implementation exposes sufficient evidence to prevent an engine from silently interpreting numerical uncertainty as a guaranteed miss.

## Evidence

- explicit status enumeration;
- normalized TOI intervals rather than a single unqualified scalar;
- witness geometry and termination reason;
- deterministic ordering and hashing;
- finite interval and event budgets;
- preserved corpus labels and per-query records;
- unit, synthetic, external-corpus, inequality, and conservation audits.

## Defeaters

- floating-point root loss or inaccurate clustered roots;
- tolerance dependence and scale sensitivity;
- persistent coplanar intervals that exceed the fallback budget;
- unsupported rotating/deforming geometry;
- host engine dropping non-conclusive statuses;
- response instability outside the limited impulse example.

## Operational rule

An `INCONCLUSIVE`, `RESOURCE_EXHAUSTED`, or numerical-failure result is not equivalent to `MISS`. A safety-oriented host must stop, substep, enlarge conservatism, route to a stronger solver, or otherwise follow an explicit degraded-mode policy.
