# NHDF-CCD v0.5 — Feature Contact, Events, and Corpus Validation

This directory is the cumulative v0.5 upgrade over the preserved v0.4 cradle-to-grave release. It advances the literal computer-graphics/physics-engine CCD profile in five bounded steps:

1. linearly moving vertex–face and edge–edge feature queries;
2. rigid-motion speed and rotational-sweep bounds;
3. deterministic interval-overlap grouping of simultaneous contacts;
4. a deliberately limited frictionless translational impulse reference;
5. a parser and evaluation harness for rational-coordinate public CCD sample queries.

The implementation returns auditable result objects rather than a naked Boolean. `HIT`, `MISS`, `INITIAL_OVERLAP`, `INCONCLUSIVE`, `RESOURCE_EXHAUSTED`, and numerical failure remain distinct. The algebraic feature solver is floating-point reference code, not an exact-predicate production library.

## Reproduce

```bash
cd 12_v0_5_upgrade
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python benchmarks/run_validation.py
PYTHONPATH=src python examples/feature_ccd_demo.py
```

The release report is built from the recorded JSON/CSV evidence; it does not contain manually invented benchmark values.

## Deliberate exclusions

No claim is made for validated rotating triangle meshes, deformables, self-collision, exact arithmetic, GPU equivalence, frictional manifold stabilization, or safety certification. The non-CCD NHDF materials remain separately testable adapters and are not treated as evidence for the CCD core.
