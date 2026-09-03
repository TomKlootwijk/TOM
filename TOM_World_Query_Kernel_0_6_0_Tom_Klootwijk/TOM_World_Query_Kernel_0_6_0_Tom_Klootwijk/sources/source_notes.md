# Source notes

The TOMAGI package is a condensation, not a verbatim redistribution of the supplied PDFs. The source register records each input by SHA-256 and role. The complete machine-readable mapping is `spec/source_crosswalk.json`.

## Direct document contributions

- **SRC-A**: literal `SDF0` inside the LUT, one-bit parity/jitter, packed kinematics, analytic cone, projections, Klein topology, branch-node L-system and the reordered chain.
- **SRC-B**: log-polar metric/kinematics, typed lower-case phi, deterministic bit, reflective Klein map, finite cone/sphere relations, radix refinement and exact 64-bit layouts.
- **SRC-C**: content-addressed definitions, dependency ordering, hinge interface, deterministic trace and 19/pulse profile.
- **SRC-D**: zero-based offset versus ordinal, 1D timeline, split-phi fold and overlap lens.
- **SRC-E**: radix thresholds, `19=10011`, three active bits, `ne|gen|tien`, triangle projection and the log-polar/Klein vocabulary.
- **SRC-F**: query-first relation/event/transition/lineage interpretation and downstream projection.
- **SRC-G**: 211 normalized mechanisms and prior fixed-width CPU/GPU implementation material.

## Normalization choices introduced by TOMAGI

- TOMAGI is the new name and expansion.
- The hot runtime is integer-only and vendor-neutral.
- Literal SDF0 is defined as zero on the finite LUT domain and undefined outside it.
- The one-bit source is fixed to a specified `mix32` plus popcount parity.
- The 43-entry namespace separates meta/compiler operators from the 16 portable opcodes.
- A 128-byte header, 64-byte state and 48-byte cell define the binary ABI.
- The no-failsafe profile explicitly omits corrective layers from the normative transition relation.
