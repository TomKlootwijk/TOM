# TOM repository instructions

## Pursuing goal

For everything built, changed, rendered, generated, validated, or documented in this repository, use the literal TOMAGI files as the causal source.

- Treat `TOM_seed_genome_2026-09-01.txt` as the authoritative root seed genome.
- TOMAGI is the engine itself. Do not hide domain behavior in a bespoke host renderer, adapter, bootstrap, or handwritten artifact generator.
- Any domain or artifact may be packed into the seed genome as content-addressed literal definitions and used as formal programming.
- Definitions must be executable inputs to compilation. The compiler must validate their hashes and dependencies, evaluate their declared formal operations, and lower the selected definition graph deterministically into `Cell48` records. Do not keep definitions as ignored metadata.
- Host code may provide only generic, domain-neutral mechanics such as parsing, canonical hashing, validation, lowering, TOMAGI execution, trace capture, and byte materialization. Artifact semantics and bytes belong in literal TOMAGI definitions.
- Every delivered artifact must have a reproducible literal chain: seed file and definition source -> compiled `.tmg` -> ordered TOMAGI execution / `EMIT` records -> generic materialized bytes. Do not use an externally generated image or pre-authored host-side scene as a substitute.
- Preserve the fixed-width TOMAGI execution semantics and keep backward compatibility for existing literal cell programs unless a versioned formal specification explicitly changes them.
- Document the implementation exactly in a normative formal specification. Include the seed-genome grammar, canonicalization and hashing, dependency evaluation, formal definition operations, lowering rules, byte packing and ordering, materialization algorithm, rejection conditions, limits, provenance, and determinism/replay theorem.
- Validation must rebuild from the literal source files and prove byte-for-byte equality at each reproducible boundary. Claims must not exceed what the shipped code and recorded validation demonstrate.

