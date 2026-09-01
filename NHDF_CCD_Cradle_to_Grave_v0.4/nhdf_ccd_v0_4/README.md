# NHDF-CCD v0.4 - Cradle-to-Grave Validation Package

This release turns the NHDF roadmap toward a single falsifiable center: **Continuous Collision Detection (CCD)**. It contains a typed specification, an executable CPU reference, tests, benchmark scaffolding, a GPU port plan, operational checklists, retirement criteria, and explicitly separated domain adapters.

## What is implemented

- Exact linear CCD for sphere-sphere, sphere-plane, and axis-aligned box pairs.
- Contract-driven conservative advancement for supported separation oracles.
- Point/Sphere versus a true or conservatively bounded signed-distance field under translational motion.
- Conservative swept-AABB broad phase with deterministic sweep-and-prune.
- Bounded interval-refinement fallback with midpoint or golden-ratio split as an **ablation**, not a correctness premise.
- Collision certificates, failure states, deterministic trace digests, and telemetry.
- A Python test and benchmark suite plus a small C++17 parity implementation.

## What is not implemented

- Production-grade triangle-triangle CCD, deformable-mesh self-collision, rigid-body rotation, robust exact predicates for all degeneracies, contact response, friction, or a verified GPU backend.
- Optical, quantum, chemical, biological, medical, SAR, or cosmological execution. Those are mapped as research adapters with explicit evidence gates.

## Quick start

```bash
python -m pip install -e .
pytest
python 05_benchmarks/run_benchmarks.py
python 03_reference_implementation/python/examples/run_demo.py
```

C++ smoke build:

```bash
cmake -S 03_reference_implementation/cpp -B build/cpp
cmake --build build/cpp
ctest --test-dir build/cpp --output-on-failure
```

Full verification, including benchmark regeneration, C++ smoke testing, PDF rebuild, and package hashing:

```bash
python -m pip install -e '.[test,report]'
bash scripts/run_all.sh
```

The report build also requires a LaTeX installation with `pdflatex` and `biber`. The CUDA file is a source skeleton and is not part of the passing build because this environment has no CUDA compiler or GPU.

## Package map

The numbered directories follow the lifecycle from provenance and requirements through retirement. The main report is in `11_report/` and is also copied to the package root for convenience. `00_provenance/source_material/` contains mounted copies of supplied sources S1-S3; the separate S4 whole-substrate attachment is registered but is not reconstructed when its raw byte stream is unavailable.
