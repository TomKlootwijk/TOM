# Changelog

## 0.2.0 — 2026-09-01

- Added immutable content-addressed secondary indexes attached to each new snapshot.
- Added exact stored transaction bodies for every 0.2 commit.
- Added indexes by record type, dependency, relation instance/support/compatibility, event-spec relation, generative address, time interval, topology sheet, definition/content hash, and checkpoint instance.
- Added deterministic indexed and exhaustive query planners with stage candidate counts, selected-ID hashes, and work counters.
- Added active/time interval and topology-sheet indexing for records and relations.
- Added root-derived complete-State64 checkpoint records with instance, program, source-commit, and state-certificate bindings.
- Added checkpoint-aware `state_at` and event-scan replay while preserving checkpoint-free semantic certificate bytes.
- Added stable declared-array-order batch query certificates with length-prefixed semantic reduction hashes.
- Added exact index deletion/rebuild verification from immutable snapshots.
- Added uncached full commit-ancestry audit over transactions, snapshots, indexes, records, dependencies, blobs, and orphans.
- Added in-process immutable-object caching for scalable planner comparison; audits explicitly clear caches.
- Added CLI commands for index postings, interval lookup, index rebuilding, audit, checkpoints, planned queries, and batches.
- Added a frozen two-transaction 10,000-record benchmark with 9,600 relations.
- Demonstrated the exact indexed candidate path `10000 -> 9600 -> 96 -> 6 -> 2`, with events at ticks 5 and 21 and byte-equal exhaustive semantics.
- Demonstrated checkpoint replay of tick 999 from checkpoint 900 using 99 instead of 999 TOMAGI transitions with byte-equal semantic state.
- Added index, plan, batch, audit, and state-certificate JSON schemas.
- Added the normative 0.2 profile, benchmark documentation, checkpoint/audit profile, updated roadmap/status/API/gap documentation, and a TOMAGI-emitted 0.2 release artifact.
- Expanded the conformance suite from 47 to at least 60 tests while retaining all TOMAGI and 0.1 query tests.

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
- Added a TOMAGI-materialized roadmap artifact with exact Python/C trace equality.
- Expanded validation to 47 Python tests while retaining the original TOMAGI tests.
- Added a clean generated-output-free rebuild and byte-boundary comparison.
