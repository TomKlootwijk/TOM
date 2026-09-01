# Maintenance and retirement

A release is maintainable only while its inputs, dependencies, tests, corpora, tolerances, and manifests remain reproducible. Any change to root handling, tolerance defaults, status semantics, or corpus parsing is a compatibility-relevant change.

Retirement triggers include an unbounded false-negative defect, an incompatible schema change, loss of third-party license provenance, non-reproducible release hashes, or replacement by a stronger independently reproduced implementation. Retirement requires a final archive, migration note, known-defect register, and a machine-readable marker stating that the implementation must not be selected by default.
