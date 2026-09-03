# TOM World & Query Kernel 0.2 validation

Status: **pass**

Checks: 19 passed; 0 failed. Python tests: 172.

| Check | Status | Detail |
|---|---|---|
| canonical seed identity | pass | Exact 244-byte TOM-SRS root with no terminal line feed. |
| TOMAGI ABI unchanged | pass | Indexes, plans, checkpoints, batches, and audit add no opcode and do not alter the TOMAGI 1.0 fixed-width records. |
| original TOMAGI regression | pass | The original polar loop remains binary-format compatible and reaches its recorded terminal state. |
| 0.1 counter-world compatibility | pass | The starter world, native exact-discrete queries, event commit, and lineage reconstruction remain reproducible under 0.2. |
| native query and bounded grammar regression | pass | definition/state/event/support/compatibility/trace/reconstruction and bounded grammar behavior matches the 0.1 starter certificates. |
| Python/C counter trajectory trace | pass | The complete eight-step TOMAGI trace and final State64 are equal. |
| frozen 10,000-record world | pass | One immutable two-commit world contains exactly 10,000 validated records and one TOMAGI program blob. |
| immutable secondary-index postings | pass | The content-addressed index exposes exact type, instance, support, interval, topology, address, and checkpoint postings. |
| indexed/exhaustive event-plan equivalence | pass | Fixed-stage immutable index intersection reduces 10,000 records to two relation candidates while returning byte-identical semantic event results. |
| exact ancestry-bound checkpoint replay | pass | The nearest valid tick-900 checkpoint reproduces state_at(999) with 99 transitions instead of 999, saving 900 steps without changing semantic bytes. |
| stable ordered batch equivalence | pass | Four requests reduce semantic result bytes in declared array order; indexed and exhaustive planner modes have one semantic reduction hash. |
| index deletion and exact reconstruction | pass | After deletion, the immutable index is rebuilt from the snapshot's authoritative record map to the exact declared bytes. |
| full commit-ancestry and reachability audit | pass | Both commits, exact transactions, snapshots, indexes, records, dependencies, and blobs validate with no unreachable immutable objects. |
| disk corruption detection | pass | A copied store with one mutated immutable object is rejected by an uncached disk audit. |
| stored transaction/snapshot/index lineage | pass | Every commit preserves the exact transaction body and binds one immutable snapshot and index to its parent sequence. |
| roadmap literal EMIT artifact | pass | The primary roadmap is byte-equal to its source after content-addressed definition compilation and equal Python/C TOMAGI execution. |
| 0.2 release documentation EMIT artifact | pass | The 0.2 completion document is itself reconstructed from an executable literal TOMAGI program with equal Python/C full traces. |
| conformance tests | pass | 172 tests passed, including the original TOMAGI suite and 0.2 index/plan/checkpoint/audit tests. |
| static specifications, sources, and schemas | pass | Normative profiles, source PDFs, schemas, all benchmark records, immutable indexes, plans, batches, audit, and artifact sources passed static verification. |

## Benchmark headline

- Frozen records: 10,000.
- Indexed event candidate path: `10,000 -> 9,600 -> 96 -> 6 -> 2`.
- Event ticks: `5, 21`; indexed/exhaustive semantic bytes equal.
- State at tick 999: checkpoint replay 99 steps versus root replay 999; 900 steps saved.
- Full audit: two commits, zero errors, zero orphans.

## Evidence boundary

This release executes Python and C99 and preserves the TOMAGI 1.0 ABI. GPU mappings are retained but no new physical GPU dispatch is claimed. Event queries remain exact over whole discrete transitions; they do not yet certify a relation crossing between samples or resolve simultaneous event sets. No autonomous learner, planner, grounded perception layer, or AGI is claimed.

Validation report content hash: `sha256:c9690a7a9d05971efb7ec1506e4424e9a6e5578086dd4ea593d03e6d2d0dbc40`
