# Changelog

## 0.1.0 — 2026-09-01

- Added exact verification of the canonical 244-byte TOM seed.
- Added `tom_world`, a dependency-free Python package over the retained TOMAGI 1.0 runtime.
- Added content-addressed world records, blobs, snapshots, commits, and atomic local HEAD publication.
- Added typed records for definitions, instances, relations, supports, compatibility, transitions, event specifications, grammars, observations, hypotheses, goals, events, and lineage.
- Added a bounded side-effect-free signed-64-bit query expression language.
- Implemented `definition_at`, `verify_definition`, `state_at`, `trace`, `next_event`, `events_in_support`, `compatible`, and `reconstruct`.
- Added exact discrete support/compatibility-gated event scanning and atomic transition certificates.
- Added event and lineage commits with byte-equal reconstruction from the source commit.
- Added finite branch-selected grammar expansion with depth, symbol, stack, and bit budgets.
- Added generic literal-byte definition compilation to TOMAGI `EMIT` chains without changing the TOMAGI ABI.
- Added full JSON trace output to the C99 CLI.
- Added the executable counter world and positive/negative compatibility examples.
- Added a TOMAGI-materialized 28,156-byte roadmap artifact produced by 7,039 EMIT cells, with exact Python/C trace equality.
- Expanded validation to 47 Python tests while retaining the original 24 TOMAGI tests.
- Added a clean generated-output-free rebuild and byte-boundary comparison.
- Added the detailed AGI roadmap, implementation status, architecture, query API, gap matrix, next experiments, schemas, and normative world/query profile.
