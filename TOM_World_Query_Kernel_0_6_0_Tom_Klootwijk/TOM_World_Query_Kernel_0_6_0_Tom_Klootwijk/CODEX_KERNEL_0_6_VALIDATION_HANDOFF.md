# CODEX World & Query Kernel 0.6 validation handoff

Date: 2026-09-03  
Authority root: `TOM_seed_genome_2026-09-01.txt`  
Canonical seed SHA-256: `d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5`

## Disposition

The WQK 0.6 kernel has been adversarially audited, repaired, rebuilt from its
literal TOMAGI sources, and prepared for deterministic replay.  The final
release claim is exactly the one recorded by
`validation/learner06/validation_report.json`; this handoff does not broaden it.

## Repairs made

1. The Learner 0.2 formal authority now validates the complete executable
   registry, family, candidate, rational, observation, data-set, partition,
   prior-authority, and repair-proof contracts before evaluating any data set.
   Rehashed semantic mutations no longer pass merely because their outer hash
   is internally consistent.
2. Partition resolution follows each declared ordered ID list. Missing,
   duplicate, overlapping, uncovered, or multiply resolved IDs are rejected.
   Observation-array order can no longer replace the literal partition order.
3. Expression trees use a closed operation grammar. Unknown operations cannot
   fall through to multiplication, and nested candidate/family/registry hashes,
   depth, complexity, canonical rationals, literal order, and exact finite
   candidate budgets are checked by the formal program.
4. The formal program is a separate evaluator dependency and is no longer
   smuggled into its own input sequence. Direct replay resolves the actual
   `sequence.construct` dependency order, matching seeded compilation.
5. Promotion is bound to the exact learner program, exact named input-set hash,
   exact learner result, repaired 0.5.2 parent, registry, partition policy,
   repair proof, data-set bundle, context, row order, and source data-set hashes.
6. Formal equality is type-strict for JSON values, while exact numeric equality
   remains rational. Booleans can no longer compare equal to integers through
   Python coercion.
7. Direct `Program` construction and persisted `.tmg` loading now agree on
   opcode/successor validity and fixed-width integer normalization. Seeded
   state, legacy cell arguments, and tick counts are range-checked before a
   program can reach a late serialization failure.
8. GPU opcode arithmetic and RADIX-domain handling now use the same declared
   fixed-width equations as the CPU at extreme values. The durable release
   evidence is source-level contract assertions plus Python/C extreme-vector
   conformance, not physical GPU dispatch.
9. Test-log capture suppresses interpreter warnings at process startup and
   canonicalizes line endings, removing Python-version-dependent orphan warning
   context from reproducible validation evidence.
10. Canonical hashing now accepts only JSON-native arrays and string-keyed
    objects. Definition parameters, provenance, and generated cell identifiers
    obey their effective string limits; encoded byte-literal carriers are
    correctly governed by the decoded output-byte limit instead.

## Required evidence

The handoff is complete only when all of these addressed records report pass:

- `validation/learner06/learner_authority_proof.json`
- `validation/learner06/promotion_authority_proof.json`
- `validation/learner06/rejection_capsule.json`
- `validation/learner06/validation_report.json`
- `validation/learner06/clean_rebuild.json`
- `validation/learner06/learner06_release_artifact.proof.json`
- `validation/learner06/kernel06_validation_handoff.proof.json`
- `checksums/PACKAGE_MANIFEST.json`
- `checksums/SHA256SUMS.txt`

The authoritative commands are:

```text
make validate-learner06
make package-learner06
```

They must prove the full conformance suite, Python/C full-trace and ordered-EMIT
equality, direct/materialized byte equality, independent-oracle agreement,
parent-bound immutable-store reconstruction, two generated-output-free equal
builds, deterministic ZIP bytes, safe archive inventory, and final archive
replay.

## Literal artifact chain

This document is itself delivered through the required causal chain:

```text
TOM_seed_genome_2026-09-01.txt
  + CODEX_KERNEL_0_6_VALIDATION_HANDOFF.md
  -> examples/learner06/kernel06_validation_handoff.literal.json
  -> examples/learner06/kernel06_validation_handoff.tmg
  -> authenticated Python/C EMIT traces
  -> validation/learner06/CODEX_KERNEL_0_6_VALIDATION_HANDOFF.materialized.md
```

The materialized bytes must equal this authored source byte for byte. The proof
record named above pins every boundary.

## Preserved boundary and residual limitation

The binary ABI remains the version-1 128-byte header, 64-byte `State64`,
48-byte `Cell48`, and sixteen opcodes. No compatibility-breaking budget field
was inserted into that format.

Consequently, a caller that directly executes an authenticated legacy program
whose graph intentionally loops over non-halting `EMIT` cells may materialize
more repeated bytes than the source compiler's `max_output_bytes` budget. That
source budget is not serialized in the version-1 `.tmg`, and deriving a ceiling
from unique cell payloads would incorrectly reject legitimate legacy loops. All
delivered artifact graphs halt on their final EMIT cell and are bounded. A hard
runtime materialization ceiling requires a versioned header/profile field or an
explicit caller-supplied policy; it must not be retrofitted by changing version-1
execution semantics.

## Next action

Consumers should begin from `TOM_CONTINUATION_HANDOFF_0_6.json`, verify the
canonical seed and every referenced content hash, replay the package validation,
and retain the terminal promotion head as the only permitted parent for the next
versioned milestone. Do not treat generated Markdown, a host-side oracle, or an
unpublished learner proposal as authority.
