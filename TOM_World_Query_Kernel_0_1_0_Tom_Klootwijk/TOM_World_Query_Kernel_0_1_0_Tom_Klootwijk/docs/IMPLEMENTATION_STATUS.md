# TOM World & Query Kernel 0.1 — Implementation Status

## Delivered and executable

| Capability | Status | Concrete file/API |
|---|---|---|
| Canonical seed verification | Complete for exact TOM-SRS 1.0 seed | `tom_world.seed` |
| Canonical JSON/content hashes | Complete for JSON-compatible values | `tom_world.canonical` |
| Persistent immutable objects/blobs | Complete starter | `tom_world.store.WorldStore` |
| Snapshot and commit hashes | Complete starter | `snapshots/`, `commits/`, `HEAD` |
| Atomic local commit publication | Complete starter | immutable writes, then atomic HEAD replace |
| Record types | Complete starter set | `tom_world.records` |
| Bounded expression evaluator | Complete 0.1 integer profile | `tom_world.expression` |
| `definition_at` | Implemented | `QueryEngine.definition_at` |
| `verify_definition` | Implemented | `QueryEngine.verify_definition` |
| `state_at` | Exact discrete replay implemented | `QueryEngine.state_at` |
| `trace` | Full TOMAGI trace implemented | `QueryEngine.trace` |
| `next_event` | Exact discrete finite-horizon scan implemented | `QueryEngine.next_event` |
| support gate | Implemented | content-addressed support expressions |
| compatibility gate | Implemented | event and pairwise compatibility expressions |
| `events_in_support` | Implemented | interval `(start,end]` |
| `compatible(q1,q2)` | Implemented | pairwise State64 expression |
| atomic transition | Implemented starter set/add/xor profile | event certificate post-state |
| event and lineage persistence | Implemented | `commit_event` |
| `reconstruct(lineage)` | Byte-equal certificate replay implemented | `QueryEngine.reconstruct` |
| bounded grammar | Implemented starter L-system profile | `GrammarEngine.expand` |
| literal artifact EMIT chain | Implemented | `tom_world.artifact` |
| Python/C TOMAGI agreement | Tested for counter trajectory and original examples | `build/tomagi-c --trace-json` |

## Explicitly partial

| Area | 0.1 boundary |
|---|---|
| Query planning | Exhaustive deterministic scan; no secondary indexes yet |
| Event solving | Integer state after whole TOMAGI transitions; no continuous root isolation |
| Intervals | Expression language can construct intervals, but no general interval trajectory solver |
| Transactions | Single-writer local directory lock; no distributed consensus or merge |
| Checkpoints | Replay begins at program initial state; no state checkpoint index |
| Grammar | Finite parallel rewrite with explicit bits; no grammar-to-Cell48 compiler yet |
| Uncertainty | Stored as explicit records/fields; no calibration or propagation framework |
| Learning | Observation and hypothesis record classes only; no autonomous inducer |
| Planning | Goal records only; no search or action executor |
| Perception/action | Not implemented |
| GPU | Original mappings retained; no new physical device dispatch claimed |

## Demonstrated benchmark

The counter world contains a one-cell TOMAGI trajectory. `KIN2` preserves `vrho=1` and `vtick=1`, so the exact discrete replay has `rho=tick=n` after `n` transitions.

A relation exposes residual:

```text
R(q) = q.rho - 5
```

It is gated by:

```text
support:       0 <= rho <= 10
compatibility: orientation = 0 and sheet = 0
```

The earliest event after index 0 is certified at index 5. The transition sets output to 5 and branch to 1 and updates lineage. The resulting event and lineage are committed in the shipped world store and reconstructed byte-for-byte from their source commit.
