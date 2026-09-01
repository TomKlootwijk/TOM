# Architecture: TOM World & Query Kernel 0.1

## 1. Layering

```text
canonical seed
    |
    v
content-addressed world records and TOMAGI blobs
    |
    v
immutable snapshot + commit lineage
    |
    v
query kernel
  definition_at / verify_definition
  state_at / trace
  support / compatibility
  next_event / events_in_support
  transition / event / lineage
  reconstruct
    |
    v
query certificates and optional literal EMIT artifacts
```

TOMAGI remains the deterministic state-transition engine. The world kernel stores definitions and context, selects exact program/state inputs, evaluates typed gates and relations, and returns content-addressed certificates.

## 2. TOM-SRS world-object mapping

| TOM-SRS component | 0.1 representation |
|---|---|
| `D` definitions | `definition` records |
| `X` instances/state seeds | `instance` records plus `.tmg` blobs |
| `G` finite grammar | `grammar` records and expansion certificates |
| `R` relations | `relation` records with bounded expressions |
| `S` support | `support` records |
| `C` compatibility | `compatibility` records |
| `H` hinges/connectors | TOMAGI HINGE cells or explicit transition records; no separate high-level hinge engine yet |
| `E` verified events | event certificates and committed `event` records |
| `T` transitions | `transition` records |
| `I` invariants | definition payload metadata; enforcement is partial in 0.1 |
| `L` lineage/novelty | commit ancestry and `lineage` records |
| `P` phase pipelines | dependencies plus query order; no general pipeline planner yet |
| `g,h_g` root | exact seed bytes and fixed hash in every store/transaction |

## 3. Store layout

```text
store/
  store.json                     content-addressed store descriptor
  seed.bin                       exact 244 canonical bytes
  HEAD                           mutable pointer to one immutable commit
  objects/<sha256>.json          immutable records
  blobs/<sha256>.bin             immutable `.tmg` or other bytes
  snapshots/<sha256>.json        ID -> object/blob hash maps
  commits/<sha256>.json          parent, sequence, transaction, snapshot
```

Only `HEAD` is mutable. A commit writes and verifies all immutable objects, the snapshot, and the commit before atomically replacing `HEAD`.

## 4. Query order

For each candidate relation at each exact discrete state:

```text
state replay
-> support decisions
-> compatibility decisions
-> relation residual/interval
-> zero/entry/crossing trigger
-> event certificate
-> atomic transition
-> optional event + lineage transaction
```

Candidates are ordered by integer priority and then relation ID. The first passing candidate at the earliest state index is `next_event`.

## 5. Host-code boundary

Generic host mechanics include hashing, immutable storage, dependency validation, expression evaluation, TOMAGI replay, event scanning, transition application, and certificate serialization.

The counter target, relation, support window, topology requirement, output token, and grammar productions are all literal records in `examples/world_counter/world_source.json`; they are not branches hard-coded in `QueryEngine`.
