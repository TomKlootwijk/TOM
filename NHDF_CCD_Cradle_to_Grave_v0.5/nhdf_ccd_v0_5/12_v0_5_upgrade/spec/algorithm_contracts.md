# Algorithm contracts

## Vertex–face

Inputs are four linearly moving points over normalized time `t ∈ [0,1]`: one vertex and three triangle vertices. The primary candidate equation is the cubic signed-volume polynomial

`f(t) = (p(t)-a(t)) · ((b(t)-a(t)) × (c(t)-a(t)))`.

Every admissible real root is checked against the closed moving triangle through a closest-point witness. A root is a contact only when the point–triangle distance is at most the declared contact thickness plus geometric tolerance.

When the polynomial is identically zero or numerically ill-conditioned, the implementation does not infer a miss. It invokes a distance-rate-bounded interval fallback. An interval may be pruned only when a Lipschitz lower bound proves separation.

## Edge–edge

The edge query uses the corresponding cubic coplanarity polynomial for four moving endpoints and tests each root with the closed segment–segment distance and parameters. Persistent coplanarity is routed to the same conservative fallback principle.

## Certificates

A contact certificate contains a normalized TOI interval, witness points, normal, barycentric or edge parameters, tolerances, method, termination reason, candidate count, condition indicator, and deterministic digest. A miss certificate states why all candidates or intervals were rejected. Unresolved computation remains unresolved.

## Limits

Floating-point polynomial roots may be inaccurate for clustered/multiple roots and extreme scale separation. The present code is a reference architecture and benchmarkable hypothesis. It is not a substitute for exact predicates, interval root isolation, or a production CCD library.
