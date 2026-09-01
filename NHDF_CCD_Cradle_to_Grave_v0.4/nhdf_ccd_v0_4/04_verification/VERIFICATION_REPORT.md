# Bundled verification report

Release: 0.4.0

- Python: **22 tests passed**.
- C++17: **1 smoke test passed** after CMake configure/build.
- Deterministic reference vectors: **4 certificates generated**.
- Random sphere-sphere differential benchmark: **5,000 queries**, exact solver as ground truth.
- Exact hits: **2,502**.
- Endpoint-only discrete checks missed **2,500** of those hits.
- Conservative advancement false negatives: **0** in this generated distribution.
- Conservative advancement false positives: **0**.
- Inconclusive results: **0**.
- Maximum observed conservative TOI upper-bound error: approximately **1.79e-8** in normalized step time.

These results validate only the bundled profiles and generated distribution. They are not evidence for triangle-mesh completeness, production performance, GPU equivalence, or safety certification.
