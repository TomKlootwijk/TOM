# Change control

Every algorithmic change must include:

1. requirement or defect reference;
2. mathematical impact statement;
3. new or modified tests;
4. differential benchmark results;
5. CPU/GPU equivalence results when applicable;
6. migration and rollback plan;
7. updated risk register and documentation;
8. semantic version decision.

A performance optimization that changes a predicate, tolerance, floating-point mode, queue ordering, or broad-phase bound is a correctness change, not a cosmetic refactor.
