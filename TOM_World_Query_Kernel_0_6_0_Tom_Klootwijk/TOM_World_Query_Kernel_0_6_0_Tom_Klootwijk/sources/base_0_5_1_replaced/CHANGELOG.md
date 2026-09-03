# Changelog

## 0.5.1 — seeded-authority corrective handoff

- Corrected the 0.5.0 authority violation: the affine learner is now a content-addressed formal program evaluated during seeded compilation, rather than domain behavior implemented only in `tom_learner05` host Python.
- Added generic, bounded, exact formal evaluation and the seeded operations `source.json`, `sequence.construct`, `formal.evaluate`, and `canonical.encode`.
- Made the compiler validate the seed token registry, definition hashes, dependency types/order, operation contracts, budgets, source bytes/hashes, provenance, and finite canonical JSON before deterministic `Cell48` lowering.
- Made materialization authenticate the supplied trace as an exact deterministic execution prefix; reordered, duplicated, forged, or noncanonical rows reject.
- Added a normative seeded compilation specification and strict schema.
- Added a corrective overlay that preserves the prior bytes of all three replaced 0.4.2 files and verifies every unchanged inherited authority.
- Added a 19-dataset seeded formal learner artifact: 19,540 cells, 131,478 formal steps, 12 exact acceptances, 7 exact rejections, and zero coefficient errors.
- Added byte-identical Python/C trace checks, environment-independent clean-copy replay, timing/cache normalization, and independent byte-for-byte ZIP re-encoding.
- Preserved the frozen TOMAGI ABI and legacy literal-cell program bytes.
- Retained `tom_learner05` only as an independent reference oracle and append-only evidence-store implementation; it is not the authority for the corrected learner result.

## 0.5.0 — TOM Learner 0.1

- Independently revalidated the V0.4.1 corrective source line before continuation.
- Added a 47-file literal-only `0.4.2` handoff manifest and verification command.
- Recorded that the conversation-supplied 0.4.2 ZIP was unavailable to the build filesystem and was not used as authority.
- Added strict exact-rational observation, split-policy, hypothesis-family, and acceptance-policy records.
- Added a target-value-independent SHA-256 split into train, validation, and holdout evidence.
- Added exact affine `y=a*t+b` candidate induction from training pairs.
- Added train-only rank and selection, validation gate, holdout audit, complexity gate, and contradiction gate.
- Added exact residual evidence, counterexample records, rejection lineage, and learned `SDF0@Def` definitions.
- Added an independent `fractions.Fraction` baseline implementation.
- Added an append-only learner overlay with complete evidence enumeration, parent-bound transactions, stale-parent rejection, canonical-byte audit, and reconstruction.
- Added a 19-case benchmark: 12 exact recoveries, 7 correct rejections, zero false promotions, and same-ID data-leakage probes.
- Added `tom-learner05` CLI, strict JSON schema, normative specification, updated roadmap, validation, clean replay, deterministic packaging, and a TOMAGI-emitted release document.
- Kept TOMAGI ABI 1.0 unchanged.

## 0.4.1 — corrective rebuild

- Rebuilt piecewise continuation from the corrected V0.3 source line.
- Removed relation-authored continuation endpoints and the superseded `tom_world04` namespace.
- Derived segment boundaries only from certified earliest-event solving.
