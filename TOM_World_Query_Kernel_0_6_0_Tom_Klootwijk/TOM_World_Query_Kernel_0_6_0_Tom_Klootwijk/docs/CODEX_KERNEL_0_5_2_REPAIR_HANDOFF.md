# CODEX handoff — TOM WQK 0.5.2 kernel repair

Date: 2026-09-02

## Authority and scope

The authoritative root remains `TOM_seed_genome_2026-09-01.txt`. This handoff
is itself a literal TOMAGI artifact:

```text
canonical seed
-> examples/learner052/kernel_repair_handoff.literal.json
-> examples/learner052/kernel_repair_handoff.tmg
-> equal Python/C execution traces
-> authenticated ordered EMIT records
-> validation/learner052/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF.materialized.md
```

The repair does not broaden the learner. The valid claim remains exact finite
affine proposal plus literal parent-bound promotion and evidence authority.

## Implemented repairs

1. C runtime arithmetic now uses defined mathematical intermediates and
   explicit `wrap32` lowering. Extreme signed 32-bit operands produce the same
   state and branch decisions as Python without C signed-overflow undefined
   behavior.
2. Python and C loaders reject any nonzero value in the six reserved TOMAGI
   header words.
3. Store publication holds a same-host inter-thread and inter-process lock from
   the expected-HEAD read through immutable verification and atomic HEAD
   replacement. Concurrent contenders cannot both report success.
4. Every recursive formal-expression result is checked against value-node and
   canonical-byte limits before a parent expression consumes it. Fold
   accumulators are therefore bounded at every iteration.
5. Release packaging verifies and extracts the exactly pinned 0.5.1 corrective
   ZIP, removes parent inventory products and volatile host transcripts, and
   applies only the content-addressed 0.5.2 continuation overlay. Two
   independent builds must agree on declared boundaries, the promotion-store
   tree, and final ZIP bytes. Obsolete 0.5.2 evidence/store aliases are
   rejected.
6. The documented `audit-store` argument order now matches the public CLI.

## Acceptance commands

Run from the package root on a host with Python 3.10+, GNU Make, a C99 compiler,
`jsonschema`, and the pinned 0.5.1 corrective ZIP beside the 0.5.2 package:

```bash
make validate-learner052
make package-learner052
```

Then require all of the following:

- `validation/learner052/validation_report.json` has `status: pass` and no
  failed checks;
- `validation/learner052/clean_rebuild.json` reports equality for every
  declared file boundary, source boundary, and promotion-store record;
- the external release manifest's `archive_replay` record reports two clean
  builds and `package_byte_reproducible: true`;
- `checksums/PACKAGE_MANIFEST.json`, `checksums/SHA256SUMS.txt`, and the external
  SHA-256 inventory all verify against the delivered bytes.

## Regression locations

- `tests/test_tomagi.py`: extreme-`i32` Python/C equality and all reserved
  header words;
- `tests/test_learner052_transaction_authority.py`: deterministic thread and
  process CAS races plus abnormal publisher exit;
- `tests/test_tomagi_formal.py`: intermediate node/byte-budget rejection;
- `tests/test_learner052_packaging.py`: volatile-file, forged-manifest,
  noncanonical-path, and link/reparse rejection;
- `tools/package_learner052_release.py`: two-clean-build ZIP proof and package
  inventory validation.

## Remaining explicit boundaries

- Publication locking coordinates processes on one host using local NT or
  POSIX filesystem semantics. Simultaneous writers from different hosts, or
  mixed Windows and WSL writers addressing one shared store, are unsupported.
- GPU source mappings remain retained evidence; this release does not claim
  physical GPU execution of the promotion authority.
- No noisy, open-domain, planning, perception, autonomous-action, general
  intelligence, or AGI claim is made.

## Instructions to the receiving Codex task

Treat the generated validation report and external release manifest as the
result records; do not infer success from this narrative. Preserve the fixed
TOMAGI ABI and all literal-source hashes. If this document changes, deliberately
refresh its literal definition, rebuild its `.tmg`, replay both backends, and
update the proof before making a new package claim.
