# Acceptance criteria for this release

The v0.4 artifact is accepted as a **reference scaffold** when:

1. All bundled Python tests pass.
2. The C++ smoke test builds and passes.
3. Reference-vector generation is deterministic.
4. The included random benchmark reports zero false negatives for the supported sphere-sphere test distribution when compared with the exact solver.
5. Unsupported and capacity-exceeded cases remain explicit.
6. The PDF renders without clipping or missing glyphs.

These criteria do not certify the package for production or safety-critical use.
