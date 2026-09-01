# TOM World & Query Kernel 0.2 — Implementation Status

## Delivered

| Layer | Status | Evidence |
|---|---|---|
| Canonical seed | Complete for TOM-SRS 1.0 | Exact 244 bytes and fixed SHA-256 |
| TOMAGI ABI | Preserved | 128-byte header, 64-byte state, 48-byte cell, 16 opcodes |
| Content-addressed records/blobs | Implemented | Objects and blobs verified by SHA-256 |
| Exact stored transactions | Implemented | Each 0.2 commit names the committed transaction body |
| Snapshots and ancestry | Implemented | Immutable snapshots/commits and atomic `HEAD` |
| Immutable secondary indexes | Implemented | 13 index projections with deterministic bytes |
| Index rebuilding | Implemented | Deleted index recreated with exact declared hash/bytes |
| Deterministic query plans | Implemented | Indexed and exhaustive modes; stage and work certificates |
| `definition_at`, `verify_definition` | Implemented | Exact record retrieval and dependency verification |
| `state_at`, `trace` | Implemented | Exact TOMAGI transition-count replay |
| Root-derived checkpoints | Implemented | Complete State64 plus instance/program/source bindings |
| `next_event`, `events_in_support` | Implemented for exact discrete states | Support/compatibility/trigger certificates |
| `compatible` | Implemented | Pairwise typed predicate certificates |
| Event/lineage commit and reconstruction | Implemented | Byte-equal certificate replay from source commit |
| Bounded grammar | Implemented starter profile | Depth, symbols, stack, branch-bit budgets |
| Stable batch query | Implemented | Declared-order length-prefixed semantic reduction |
| Full ancestry audit | Implemented | Transactions, indexes, objects, blobs, parents, orphans |
| 10,000-record benchmark | Implemented | Exact population and `10000→9600→96→6→2` plan |
| Literal documentation artifacts | Implemented | Markdown definitions→TMG→Python/C→EMIT→bytes |
| Python/C artifact execution | Implemented | Complete trace equality on shipped artifact programs |

## Demonstrated quantitative work reduction

| Query | Baseline | Indexed/checkpoint path | Preserved semantic result |
|---|---:|---:|---|
| relation candidates | 10,000 records | 2 final relation candidates | yes, indexed/exhaustive byte equality |
| `state_at(...,999)` | 999 root transitions | 99 transitions from checkpoint 900 | yes, byte equality |

These are deterministic operation counts. They are not hardware-independent wall-clock performance claims.

## Partial

| Capability | Current boundary |
|---|---|
| Time intervals | Used for record filtering; event time is still an integer transition index |
| Uncertainty | Expression language can represent intervals, but no calibrated propagation framework exists |
| Query planning | Fixed deterministic stage order; no learned or cost-based optimizer |
| Persistence | Local single-writer atomic `HEAD`; no distributed consensus or multi-writer merge protocol |
| Memory | Semantic/episodic records exist; retrieval learning, consolidation, forgetting, and contradiction repair remain absent |
| GPU | Shared TOMAGI kernels retained; no new 0.2 device-dispatch evidence |

## Missing for later milestones

- certified bracket and rational/interval event-time solving;
- simultaneous-event sets and conflict/commutation rules;
- observation-to-definition candidate learner;
- contradiction, supersession, and evidence weighting;
- semantic/episodic/procedural/working-memory policy;
- goal decomposition, plan search, tool/action adapters, and replanning;
- grounded text/image/audio/sensor interfaces;
- explicit permissions and external capability enforcement;
- broad unseen-domain capability evaluation;
- AGI evidence.
