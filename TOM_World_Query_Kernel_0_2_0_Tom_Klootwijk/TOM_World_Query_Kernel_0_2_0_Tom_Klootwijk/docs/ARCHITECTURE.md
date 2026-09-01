# TOM World & Query Kernel 0.2 Architecture

## Layering

```text
canonical 244-byte TOM seed
          |
          v
content-addressed record and blob layer
          |
          v
transaction -> snapshot -> immutable indexes -> commit -> HEAD
          |
          +-------------------+
          |                   |
          v                   v
indexed planner        exhaustive planner
          |                   |
          +---------+---------+
                    v
         exact query semantics
   State64 replay / relations / gates
                    |
                    v
     semantic certificate and lineage
```

Indexes and checkpoints are accelerators over immutable authority. They cannot silently change a semantic certificate.

## Store objects

- **Record object:** one typed definition, instance, relation, gate, transition, grammar, event, lineage, observation, hypothesis, goal, policy, or checkpoint.
- **Blob:** exact binary data such as a `.tmg` program.
- **Transaction:** exact input record/blobs, base commit, sequence, message, provenance.
- **Index:** deterministic projection of one snapshot's record map.
- **Snapshot:** sorted maps from logical IDs to content hashes, plus the index hash.
- **Commit:** parent, sequence, transaction, snapshot, index, message, provenance.
- **HEAD:** only mutable store pointer.

## Index projection

The indexer loads every snapshot record, validates its hash and ID mapping, and emits sorted postings. It indexes only explicit typed payload fields. It does not parse narrative `meaning` fields.

The interval array supports deterministic overlap selection. Compound generative addresses use canonical-JSON SHA-256 keys and retain original values for collision verification.

## Planner

`QueryPlanner` is bound to one immutable commit and one mode:

- indexed plans intersect immutable posting lists;
- exhaustive plans read records and apply the same semantic predicates.

A plan is content-addressed and includes stage counts, selected IDs, selected-ID hash, and work counters. The semantic query engine consumes the selected IDs and returns the same result regardless of mode.

## Checkpoint replay

Checkpoint creation always uses a checkpoint-free engine. A query can consume only a checkpoint bound to the current instance hash and program blob hash whose source commit is in the current ancestry. The nearest tick not after the target is selected. Remaining steps execute in the unmodified TOMAGI runtime.

## Event scan

The event engine preserves 0.1 ordering:

```text
TOMAGI state step
-> active interval
-> relation residual
-> support predicates
-> compatibility predicates
-> zero/trigger test
-> event candidate
-> priority and ID order
-> optional transition
-> certificate
```

The planner determines which relations are considered; it does not change relation equations or event ordering.

## Batch

Batch execution is sequential in the declared request array order. Semantic results are canonicalized and length-prefixed before hashing. A batch certificate contains each individual plan and semantic result hash.

## Audit

Audit bypasses prior caches, walks every commit to the root, validates exact transaction/snapshot/index/object/blob bytes, rebuilds indexes, verifies dependencies, and reports orphans. It uses no clock or host identity, so its certificate is reproducible.

## Host-code boundary

Host code provides only generic mechanics: canonicalization, content addressing, typed validation, deterministic indexing/planning, exact TOMAGI replay, finite expression evaluation, transaction publication, trace capture, audit, and generic emitted-byte materialization. Domain equations, support/compatibility rules, world records, benchmark relations, and documentation bytes are literal source data.
