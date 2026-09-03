# TOM Learner 0.1 / World & Query Kernel 0.5.2

## Formal Promotion and Evidence Transaction Authority

**Normative profile:** `TOM-LEARNER-0.1-PROMOTION-AUTHORITY`  
**Implementation release:** `0.5.2`  
**Corrective parent:** TOM Learner 0.1 / WQK 0.5.1  
**Seeded compilation profile:** `TOM-SEEDED-COMPILATION-1.0`  
**Underlying machine:** TOMAGI ABI 1.0  
**Canonical seed:** `TOM_seed_genome_2026-09-01.txt`

## 1. Status

This profile continues the corrective 0.5.1 learner without broadening the
hypothesis family. Version 0.5.1 moved affine induction out of the host learner
and into a content-addressed bounded formal program executed during seeded
TOMAGI compilation. Its corrective handoff explicitly identified one remaining
authority gap: promotion and evidence-transaction semantics were still assigned
to the host learner store.

Version 0.5.2 closes that gap before the roadmap proceeds to Learner 0.2. The
formal authority now covers both:

```text
exact observations -> affine proposal/result
                    -> acceptance or rejection decision
                    -> complete evidence list
                    -> parent-bound promotion certificate
                    -> snapshot + transaction + commit
                    -> immutable publication plan
```

The host filesystem layer is generic. It validates addressed records, writes
canonical immutable bytes, verifies required hashes, and performs compare-and-
swap publication of `HEAD`. It does not decide whether a learner proposal is
accepted, which definition is promoted, which evidence is authoritative, or
what rejection lineage is recorded.

## 2. Corrective inheritance

The source parent is the user-supplied corrective handoff archive:

```text
TOM_World_Query_Kernel_0_5_1_Corrective_Handoff_Tom_Klootwijk.zip
bytes:   27,022,938
SHA-256: 0f3bf159536b726fc68fc3e0ff7c1ff896c3bdf1e63a7449d5b507f67f043601
```

Before 0.5.2 artifacts are built, the 0.5.1 verifier MUST confirm:

- 44 unchanged inherited authority files;
- the three corrected implementations of canonicalization, seeded compilation,
  and authenticated materialization;
- preserved old bytes for each corrected implementation;
- seven corrective additions;
- the corrective overlay content hash; and
- the exact canonical 244-byte seed.

The authoritative 0.5.1 corrective overlay is:

```text
sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json
content hash:
sha256:53951284853681ce239d07ce2ce783250ea78b3457fd221a43d88bd90344f4bf
```

Version 0.5.2 MUST NOT restore the superseded pattern in which a host learner
both proposes and authoritatively commits its own conclusions.

## 3. Authority allocation

### 3.1 Authoritative components

The following literal files are authoritative:

```text
examples/learner052/promotion_authority.formal.json
examples/learner052/promotion_authority.literal.json
examples/learner052/promotion_context.json
examples/learner052/authority_inputs/*
```

The promotion formal-program identity is:

```text
content hash:
sha256:f1030e332b5f7358c43603096a64ebca7f9268aaaf2fbbe16dbebc972daa8bdd

file SHA-256:
e8ddb14f88b24d54a2d3da4e80d1d8e7c6e7853b4c8d32b734a15b5b1de9a3a9
```

The corrected affine learner remains the separate formal program:

```text
sha256:dd710388744a71861c90c15ef63bd85411f0652a2077f6f9ef9421997d626b28
```

The seeded definition graph MUST evaluate the affine learner first and then
feed its addressed result, together with the literal evidence and corrective
bindings, to the promotion program. A host-generated learner result MUST NOT be
substituted into the authoritative chain.

### 3.2 Non-authoritative components

`tom_learner052.oracle` is an independently written ordinary Python oracle. It
MAY compare its result to the formal value. It MUST NOT be treated as the
promotion authority.

`tomagi.immutable_store` is a generic append-only publication mechanism. Its
schema names publication, store, snapshot namespace, transaction namespace,
commit namespace, required hashes, and compare-and-swap head behavior. It MUST
NOT import learner semantics or inspect affine coefficients, acceptance gates,
observation targets, or relation meanings.

## 4. Inputs to the promotion formal program

The formal binding `promotion_inputs` is a finite sequence of exactly 25
addressed records in this order:

1. promotion formal program;
2. corrected affine learner formal program;
3. freshly evaluated affine learner result;
4. through 22. the 19 observation sets in canonical filename order;
23. promotion context;
24. 0.5.1 corrective handoff record; and
25. canonical token registry.

Flattening the 19 datasets is normative. It allows the strict corrected seeded
compiler to construct one record-only sequence without weakening the compiler's
operation type contract.

The promotion program verifies the content address of every input. It also
reconstructs and verifies the known formal-program, formal-result, learner-value,
result-row, policy, observation, and accepted-relation bodies instead of merely
copying their supplied hash strings.

## 5. Formal promotion semantics

### 5.1 Shared evidence

Every session is bound to these shared objects:

```text
promotion program
corrected affine learner program
fresh affine learner execution
fresh affine learner semantic value
promotion context
corrective handoff
canonical token registry
```

Their content hashes MUST be unique.

### 5.2 Genesis publication

Publication sequence zero creates:

- a generic immutable-store descriptor;
- an empty learner-promotion snapshot;
- a genesis transaction;
- a genesis commit;
- immutable writes for all shared authority objects; and
- a publication record with `expected_head = null`.

The genesis commit becomes the first head only after all required objects are
present.

### 5.3 Session fold

The nineteen learner result rows are processed in their declared order. For
each row, the formal program MUST:

1. resolve exactly one literal observation set by ID;
2. verify the row's dataset hash;
3. reject a duplicate session ID;
4. verify split policy, hypothesis family, acceptance policy, and every
   observation content address;
5. verify the addressed learner result row;
6. require an addressed learned relation exactly when `accepted = true`;
7. create an addressed rejection-lineage record exactly when
   `accepted = false`;
8. create an addressed promotion decision;
9. construct the ordered complete evidence-hash sequence;
10. require all evidence hashes to be unique;
11. create an addressed promotion certificate bound to the current parent;
12. derive a new immutable snapshot;
13. create a transaction that enumerates every evidence hash and binds the
    expected parent, new snapshot, decision, and promoted definition or
    rejection lineage;
14. create the next commit; and
15. create a publication whose `expected_head` equals the previous commit and
    whose `replacement_head` equals the new commit.

### 5.4 Accepted and rejected paths

An accepted transaction MUST have:

```text
published_definition_hash != null
rejection_lineage_hash     = null
```

A rejected transaction MUST have:

```text
published_definition_hash = null
rejection_lineage_hash     != null
```

No rejected session adds a learned definition to the snapshot. Rejection is
still authoritative evidence and therefore advances the append-only lineage.

### 5.5 Complete evidence order

The source context declares the semantic evidence order:

```text
promotion program
learner program
learner execution
learner summary
promotion context
corrective handoff
token registry
observation set
split policy
hypothesis family
acceptance policy
observations in source order
formal result row
acceptance decision
published definition or rejection lineage
promotion certificate
```

The transaction MUST enumerate this evidence by content hash. A missing,
duplicate, mutated, or unaddressed evidence object invalidates publication.

## 6. Publication plan

The final addressed plan has schema:

```text
TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.0
```

It contains a descriptor, twenty publications, and a terminal head. The
publication sequences MUST be contiguous from zero. For publication `i > 0`:

```text
publication[i].expected_head
    = publication[i-1].replacement_head
```

The final replacement MUST equal `terminal_head`.

For the shipped fixture:

```text
plan content hash:
sha256:07b1607745e37c1f3ac7d61a47db96a3d01c884682432c91f1d77568045337e8

terminal head:
sha256:a3bd8ecd8578b28158b96a3dce814910beb3d627068159dc668a682c85b85448

publications: 20
sessions:     19
accepted:     12
rejected:      7
```

## 7. Generic immutable store

The store has four declared immutable namespaces:

```text
commits
objects
snapshots
transactions
```

Records are stored as canonical JSON plus one LF under their SHA-256 digest.
The mutable `HEAD` file contains one content hash and one LF.

A conforming publication performs this order:

1. validate the publication and current descriptor;
2. require `expected_head` to equal the current head;
3. write every immutable record, rejecting byte collisions;
4. rescan and verify all addressed stored records;
5. require every `required_hash` to be available;
6. require `replacement_head` to exist in the commit namespace; and
7. atomically replace `HEAD`.

A stale expected head MUST reject. There is no hidden retry, automatic merge,
last-writer-wins policy, or silent refresh.

## 8. Seeded TOMAGI execution chain

The seeded source evaluates both formal programs, encodes the addressed
promotion result as canonical JSON plus LF, lowers those bytes into one to four
byte `EMIT` payloads, and creates a TOMAGI program.

The shipped identities are:

```text
literal source SHA-256:
64e28185c506821d8935bf79c12505ac74fb9f2f464cdefea1a18b81c87ced71

Cell48 count / execution steps / EMIT records:
242,749 / 242,749 / 242,749

program bytes:
11,652,080

program SHA-256:
f6eacc1e90f63d90b2487d0230fc1a10ecdfe571124dbd317efc12f7dcb93821

materialized result bytes:
970,993

materialized SHA-256:
2d6bc5b206545042e13faa5e9b4d9a0ec6b0ccf4929755c01025746b8ab4523c
```

The materialized bytes MUST equal a direct bounded evaluation of the formal
promotion program. Python and C TOMAGI runtimes MUST produce equal complete
traces and equal materialized bytes. The corrected materializer MUST replay and
authenticate every trace row before consuming any `EMIT` payload.

## 9. Independent validation

A separately written oracle reconstructs the same plan using ordinary Python
records and an independent canonicalization function. The oracle output MUST be
byte-equivalent to the formal semantic value, but the oracle does not grant
runtime authority.

The generic store MUST apply the plan from an absent or empty directory and
produce a valid strict audit. Reconstruction from the terminal commit MUST
recover twenty commits, nineteen sessions, twelve accepted definitions, and
seven rejection lineages.

## 10. Rejection conditions

In addition to all 0.5.1 compiler/materializer rejections, 0.5.2 rejects:

- an input sequence with a count or order other than the normative 25 records;
- a promotion, learner, execution, value, context, corrective-handoff, registry,
  dataset, policy, observation, result-row, or relation hash mismatch;
- dataset/result count or order mismatch;
- duplicate dataset or session identity;
- accepted/rejected relation-shape mismatch;
- duplicate supporting-evidence or required hashes;
- missing promotion decision or certificate evidence;
- noncontiguous publication sequence;
- a broken expected-head chain;
- a replacement head not written in the commit namespace;
- a missing required immutable object;
- an immutable byte collision;
- a stale current head;
- noncanonical stored record bytes;
- an unexpected extra record under strict audit; and
- a forged, reordered, omitted, or mutated execution-trace row.

## 11. Determinism and authority theorem

For fixed canonical seed, corrected compiler/materializer bytes, formal learner
program, promotion program, nineteen literal datasets, context, corrective
handoff, token registry, and declared budgets:

```text
affine learner result
= promotion input result
= promotion decision sequence
= evidence hash sequence
= publication plan
= terminal commit
= materialized result bytes
```

for every conforming implementation.

The proof follows from exact source hashing, finite formal evaluation, fixed
record order, canonical JSON, explicit parent chaining, immutable addressed
writes, compare-and-swap publication, fixed-width TOMAGI execution, and
authenticated ordered byte materialization.

## 12. Roadmap position and claim boundary

Version 0.5.2 is an authority-boundary completion, not a wider learner. It keeps
the roadmap on course by satisfying the corrective prerequisite before
introducing more hypothesis families.

The next permitted capability milestone is Learner 0.2 / WQK 0.6: a finite
typed hypothesis-family registry with bounded polynomial, piecewise-affine,
finite transition-table, and small expression-tree candidates, plus ambiguity,
supersession, and regression-impact certificates.

This profile proves only exact finite affine promotion and evidence-transaction
authority for the shipped benchmark. It does not prove noisy learning, open-
domain induction, memory, planning, perception, autonomous action, physical GPU
learner execution, general intelligence, or AGI.

**End of normative profile.**
