# TOM WQK 0.5.2 — Transaction Authority Completion

## Why this release exists

The CODEX 0.5.1 correction moved the affine learner itself into a static,
content-addressed formal program executed inside the seeded TOMAGI chain. It
also explicitly warned not to broaden the learner until the remaining
promotion and evidence-transaction semantics were removed from the host-side
learner store.

Version 0.5.2 follows that instruction exactly. It does not add polynomial,
piecewise, transition-table, or expression-tree learning. It makes the
promotion boundary literal first.

## Authority before and after

### Corrected 0.5.1

```text
literal observations
-> formal affine learner
-> addressed proposal/result
-> host learner store decides and publishes evidence transaction
```

### 0.5.2

```text
literal observations
-> formal affine learner
-> formal promotion/evidence authority
-> addressed publication plan
-> generic immutable writer + CAS HEAD
```

The host no longer decides whether a proposal is accepted, which record becomes
an authoritative definition, which rejection lineage is retained, or which
evidence hashes belong to a transaction.

## New files

```text
examples/learner052/promotion_authority.formal.json
examples/learner052/promotion_authority.literal.json
examples/learner052/promotion_context.json
examples/learner052/authority_inputs/
src/python/tomagi/immutable_store.py
src/python/tom_learner052/oracle.py
src/python/tom_learner052/cli.py
spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_2_TRANSACTION_AUTHORITY.md
spec/tom_learner_promotion_authority_0_5_2.schema.json
tests/test_learner052_transaction_authority.py
tools/build_learner052_promotion_authority.py
```

## Exact result

The formal program creates one genesis publication and nineteen parent-bound
session publications. It yields twelve promoted affine relation definitions and
seven explicit rejection lineages.

```text
formal promotion steps:     32,900
publication count:              20
unique planned records:        535
accepted definitions:           12
rejection lineages:              7
terminal head:
sha256:a3bd8ecd8578b28158b96a3dce814910beb3d627068159dc668a682c85b85448
```

The complete plan is emitted through 242,749 TOMAGI `Cell48` records and
materializes to 970,993 canonical JSON bytes. Direct formal evaluation,
independent Python oracle, Python TOMAGI execution, C TOMAGI execution, and
store reconstruction agree.

## Rule carried into 0.6

Future learner-family work must obey four non-negotiable conditions:

1. domain search and selection semantics are static formal definitions;
2. promotion semantics are static formal definitions;
3. host persistence remains generic and parent-bound;
4. every new family has an independently implemented baseline and a regression
   impact certificate over previously promoted authority.
