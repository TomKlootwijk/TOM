# Release validation log — NHDF-CCD v0.4.0

Validation date: 2026-09-01 UTC  
Declared maturity: **G3 deterministic CPU reference for the bundled primitive profile only**

## Reproducible command

```bash
python -m pip install -e '.[test,report]'
TERM=dumb bash scripts/run_all.sh
```

The command was executed from the package root in the release environment recorded by `ENVIRONMENT.json` and `VALIDATION_SNAPSHOT.json`.

## Results

- Python verification: **22 passed, 0 failed**.
- C++17 smoke verification: **1 passed, 0 failed** after CMake configure/build.
- Deterministic reference-vector generation: **4 collision certificates**.
- Seeded differential benchmark: **5,000 sphere-sphere queries**, seed `20260831`.
- Exact linear solver hits: **2,502**.
- Endpoint-only discrete method missed **2,500** of the exact hits, demonstrating tunnelling in this constructed distribution.
- Conservative advancement: **0 false negatives, 0 false positives, 0 inconclusive results** in the bundled benchmark distribution.
- Conservative advancement maximum iterations: **43**; mean iterations: **7.332**.
- Maximum observed TOI upper-bound error: **1.7885707470632894e-08** normalized step time.
- Mean observed TOI upper-bound error: **3.3615497023321673e-10** normalized step time.
- Timings are retained in `05_benchmarks/benchmark_summary.json` but are machine-specific and are not product-performance claims.

## PDF release checks

- Main dossier: `NHDF_CCD_Cradle_to_Grave_v0.4.pdf`.
- Pages: **70**, A4.
- Openable: **yes**; encrypted: **no**; XFA: **no**; likely scanned: **no**.
- Outline items: **142**; annotations: **220**.
- Fonts reported by `pdffonts` are embedded.
- Root and `11_report/` copies are byte-identical at release validation time.
- PDF SHA-256: `d5f383a5470cdc8ebfa39e21f35a6f0ddbfb48a750f20370f8ffeec88cfee6fb`.
- All 70 pages were raster-rendered and visually reviewed through contact sheets; no clipping, unreadable lifecycle diagram, or blank-content defect was observed.

## Source and build boundary

- Mounted source copies S1-S3 are present in `00_provenance/source_material/`.
- S4, the separate spherical/Cartesian whole-substrate extension, is registered and mapped in the report but its raw attachment byte stream was unavailable to the build environment, so it was not reconstructed or silently substituted.
- The CUDA backend is a semantics-first source skeleton. It was **not compiled or executed** because the release environment has no CUDA compiler or GPU.

## Scope boundary

This release validates the bundled linear sphere-sphere, sphere-plane, AABB, conservative signed-distance, broad-phase, interval-refinement, certificate, and failure-state profiles only. It does not establish production triangle-mesh or deformable CCD, rigid-body rotational completeness, simultaneous-contact correctness, CPU/GPU equivalence, safety certification, or validation of the optical, quantum, SAR, AI, chemical, biological, medical, fabrication, or cosmological adapters.
