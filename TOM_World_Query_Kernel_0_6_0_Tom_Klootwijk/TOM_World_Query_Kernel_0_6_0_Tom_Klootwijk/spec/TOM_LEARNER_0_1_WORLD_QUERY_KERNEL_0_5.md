# TOM Learner 0.1 / World & Query Kernel 0.5

> **Superseded authority notice (0.5.1):** This 0.5.0 profile described the
> learner as a host service above TOMAGI and is retained only as historical
> input/reference documentation. It is not the authority for the corrected
> learner execution. Conforming continuation MUST use
> `TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md` together with
> `TOM_SEEDED_COMPILATION_1_0.md` and the literal formal program.

## Deterministic exact-rational observation-to-definition induction

**Normative profile:** `TOM-LEARNER-0.1`  
**Implementation release:** `0.5.0`  
**Base world:** TOM World & Query Kernel 0.4.1 corrective rebuild  
**Literal handoff:** `TOM-LITERAL-HANDOFF-0.4.2`  
**Underlying machine:** TOMAGI ABI 1.0  
**Canonical root:** `TOM_seed_genome_2026-09-01.txt`

## 1. Status

This document specifies the first learning layer above the corrected deterministic TOM world/query kernel. It does not rename deterministic execution as intelligence. It defines one falsifiable, bounded learning profile:

```text
literal exact observations
-> label-independent deterministic split
-> train-only candidate generation
-> train-only candidate selection
-> validation acceptance gate
-> holdout final audit
-> contradiction and counterexample records
-> non-authoritative learning certificate
-> parent-bound promotion transaction
-> authoritative learner-overlay commit
```

The terms **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHOULD**, and **MAY** are normative.

The supported hypothesis family in this release is exactly:

```text
y = a*t + b
```

where all values are canonical exact rational numbers. This is a deliberately narrow first learner. It establishes evidence isolation, explicit rejection, and authoritative promotion semantics before broader hypothesis families are attempted.

## 2. Trust reset and inheritance boundary

Version 0.5 MUST NOT inherit generated V0.4 evidence as source authority. Its allowed inheritance is pinned by `sources/TOM_LITERAL_HANDOFF_0_4_2.json`.

The handoff:

- binds the exact 244-byte canonical seed;
- binds the corrected V0.3 rational interval implementation;
- binds the V0.4.1 corrective source namespace `tom_world04r`;
- binds the V0.4.1 strict schema and literal piecewise world;
- excludes build products, validation output, continuation journals, package inventories, and artifacts as authority; and
- declares no semantic change to V0.4.1.

Before reading inherited generated evidence, a conforming 0.5 build MUST verify every path, byte length, and SHA-256 in the handoff.

Pinned identities:

```text
canonical seed
sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5

corrected V0.3 archive
sha256:a7103ec92596fd54198e4a902f078712cf8eafcdf1e45320bbdc02dd53947278

corrected interval implementation
sha256:ea7b3ff2127e8ee7a696eb45e84ae9efdbca7c10c532617c51888fb13cd39f6d

V0.4.1 semantic chain
sha256:9fd4f3e1ae8550ae3ca99e27e7bf61b22a4935fe764fd443723abfdb3804f226

V0.4.1 validation record
sha256:57be1528d1759c5469259a71daa6f0118b006a1f6a38f9d205f29d3230308391

literal handoff
sha256:3d2b46cfd33ba6e5cf0a13697fb59e374a64ad30450fdd3c256c98a04ebc474b
```

The superseded relation-authored field `continuation_until` remains forbidden. The superseded `tom_world04` namespace remains absent.

## 3. Non-change to TOMAGI

This learning profile adds no TOMAGI opcode and changes no hot transition equation.

| Boundary | Value |
|---|---:|
| `.tmg` header | 128 bytes |
| `State64` | 64 bytes |
| `Cell48` | 48 bytes |
| opcodes | 16 |
| ABI version | `0x00010000` |

TOMAGI remains the deterministic execution engine. Learning is a content-addressed query and promotion service above it.

## 4. Canonical exact rational values

A rational value is:

```json
{"num": integer, "den": positive-integer}
```

It MUST be reduced to lowest terms, the denominator MUST be positive, and zero MUST be encoded as `{"num":0,"den":1}`. Addition, subtraction, multiplication, division, comparison, prediction, and residual evaluation are exact. Binary floating point is not part of the certified path.

## 5. Literal observation records

An observation has schema `TOM-EXACT-OBSERVATION-0.1` and fields:

```text
id
t
y
provenance
content_hash
```

Its content hash is SHA-256 over canonical JSON with the top-level `content_hash` removed. An observation set has schema `TOM-AFFINE-OBSERVATION-SET-0.1` and MUST bind:

- profile `TOM-LEARNER-0.1`;
- the canonical seed hash;
- the corrected V0.4.1 base-world hash;
- the literal-handoff hash;
- exact-rational input and output field names;
- a sorted, unique, nonempty observation array;
- one split policy;
- one hypothesis-family record;
- one acceptance-policy record; and
- provenance and content hash.

The strict JSON schema is `spec/tom_learner_affine_0_5.schema.json`.

## 6. Deterministic data split

The only supported strategy is:

```text
sha256-id-order-largest-remainder
```

The split policy declares positive integer ratios, minimum counts, and a nonempty salt. The split names and their order are:

```text
train, validation, holdout
```

### 6.1 Counts

Let `n` be the number of observations and `m_s` the minimum for split `s`. Let:

```text
remaining = n - sum(m_s)
```

If `remaining < 0`, the split rejects. Additional counts are allocated by the declared ratios using integer floor division. Leftover records are assigned by descending remainder, with the fixed split order as tie break.

### 6.2 Assignment digest

For observation ID `o`, the assignment digest is:

```text
SHA256(canonicalJSON({
  seed_sha256,
  observation_set_id,
  split_policy_hash,
  salt,
  observation_id: o
}))
```

The digest MUST NOT contain `t`, `y`, an observation content hash, or any target-derived statistic. Observations are ordered by `(digest, observation_id)` and sliced into the computed counts. IDs within each split are then sorted.

Changing an observation value while preserving its ID, observation-set ID, policy, and salt MUST preserve the split membership and `assignment_basis_hash`.

## 7. Hypothesis family

The sole 0.1 family is:

```text
model: y = a*t + b
candidate source: all distinct-t unordered training pairs
```

For every unordered pair of training observations `(i,j)` with `t_i != t_j`:

```text
a = (y_j - y_i) / (t_j - t_i)
b = y_i - a*t_i
```

Semantically equal coefficient pairs are deduplicated. Supporting observation-pair IDs remain recorded. Candidate generation rejects if the number of distinct candidates exceeds `max_candidates`.

No validation or holdout value may influence coefficient generation.

## 8. Candidate identity and complexity

A candidate identity is derived from canonical model name and exact coefficients. Each candidate records:

```text
observation_set_id
hypothesis_family_hash
split_certificate_hash
fit_input_hash
fit_uses_splits = ["train"]
coefficients
supporting_pairs
complexity
content_hash
```

For exact rational `q=n/d`, literal complexity is:

```text
sign_bit(n) + max(1, bit_length(abs(n))) + bit_length(d)
```

Model complexity is the sum of coefficient complexities plus one indicator for each nonzero coefficient.

## 9. Residual evidence

For candidate `(a,b)` and observation `(t,y)`:

```text
prediction = a*t + b
residual   = y - prediction
```

Every candidate receives a content-addressed residual record for all three splits. Per-split metrics include:

```text
count
zero_count
nonzero_count
max_abs_residual
sum_abs_residual
sum_squared_residual
exact
```

Each residual row retains observation ID/hash, exact input, observed value, predicted value, and exact residual.

## 10. Train-only selection

Candidates are ranked using only training evidence by:

```text
(nonzero_count,
 max_abs_residual,
 sum_abs_residual,
 model_complexity,
 a,
 b,
 candidate_id)
```

An exact training candidate has zero residual on every training observation. Selection behavior is:

1. no candidates: reject selection;
2. no exact training candidate: reject selection;
3. more than one semantically distinct exact candidate while uniqueness is required: reject selection;
4. otherwise select the first exact candidate in the deterministic training rank.

Validation and holdout evidence MUST NOT appear in selection rank or coefficient generation.

## 11. Validation, holdout, and contradiction gates

After train-only selection, the explicit acceptance policy checks:

- minimum split sizes;
- existence of the selected exact training candidate;
- model-complexity budget;
- exact training residuals;
- exact validation residuals when required;
- exact holdout residuals when required; and
- absence of contradictions when required.

Validation is an acceptance gate only. Holdout is a final acceptance audit only. Neither can change the selected coefficients.

A contradiction exists when one exact input `t` is associated with more than one exact output `y`. Every contradiction record contains all implicated observation IDs, hashes, and distinct outputs. A contradictory data set may not be promoted under the normative policy.

Every nonzero residual of the selected or best available candidate produces a counterexample record. Rejected candidates, counterexamples, and contradictions remain append-only evidence; rejection is not deletion.

## 12. Learning certificate

A learning certificate binds:

```text
observation set and base authority
split certificate and assignment basis
candidate enumeration and fit-input hash
train-only selection
selected residual evidence
contradictions and counterexamples
acceptance decision
phase trace
```

The certificate is a proposal. It is not authoritative world state.

The normative phase trace is:

```text
parse-observations
-> deterministic-id-only-split
-> fit-train-only
-> select-train-only
-> validation-gate
-> holdout-audit
-> contradiction-gate
-> candidate-certificate
```

## 13. Learned definition

An accepted candidate produces a content-addressed definition with schema `TOM-LEARNED-AFFINE-DEFINITION-0.1`. It exposes:

```text
relation_interface = SDF0@Def
residual = y - (a*t + b)
zero locus: y = a*t + b
```

The definition binds its source observation-set hash, candidate hash, learning-certificate hash, base-world hash, and literal-handoff hash. Creation of this record does not by itself change authority.

## 14. Promotion store

The append-only learner overlay has:

```text
store.json
seed.bin
HEAD
objects/<hash>.json
snapshots/<hash>.json
transactions/<hash>.json
commits/<hash>.json
```

Only `HEAD` is mutable.

### 14.1 Genesis

Initialization verifies the exact canonical seed and writes a descriptor, empty snapshot, genesis transaction, genesis commit, then atomically publishes `HEAD`.

### 14.2 Promotion transaction

A promotion requires the caller to provide the expected parent commit. A mismatch rejects as stale. The transaction binds:

- parent commit and parent snapshot;
- base world and literal handoff;
- observation set and complete ordered evidence-hash list;
- learning certificate and decision;
- accepted/rejected status;
- learned-definition hash or rejection-lineage hash;
- new snapshot; and
- the explicit authority rule.

All literal and derived evidence objects MUST be written and verified before the transaction. The transaction, snapshot, and commit MUST be immutable before atomic `HEAD` replacement.

An accepted session adds one learned definition to the overlay. A rejected session adds no definition but remains in rejected lineage.

## 15. Store audit and reconstruction

Audit MUST verify:

- descriptor and exact seed;
- contiguous commit sequence and parent links;
- transaction/snapshot bindings;
- every evidence object named by every promotion transaction;
- every accepted/rejected session named by snapshots;
- object content hashes, filenames, canonical JSON bytes, and one terminal LF;
- absence of orphans under strict mode.

Permissive mode may report orphans as warnings without treating the store as valid authority for strict publication.

Reconstruction returns commit-ordered sessions, the accepted-definition map, terminal snapshot, and one semantic hash.

## 16. Independent baseline

The release contains a separate `fractions.Fraction` implementation that does not import the learner's split, model, fitting, selection, or residual modules. It independently implements:

- split counts and ID-only assignment;
- pair-derived exact affine candidates;
- train-only rank and exact selection;
- validation and holdout gates;
- contradiction detection; and
- semantic reduction.

A benchmark case passes baseline comparison only when split membership, selected coefficients, and acceptance status are equal.

## 17. Canonical benchmark

The literal benchmark plan contains 19 data sets:

- 12 exact affine positive cases, including integer and noninteger rational coefficients;
- one training outlier;
- one validation outlier;
- one holdout outlier;
- one piecewise change;
- one exact-input contradiction;
- one constant-input underdetermined case; and
- one exact but policy-excessive complexity case.

The normative acceptance policy requires exact train, validation, and holdout residuals, unique exact training selection, no contradiction, and bounded complexity.

Required benchmark results are:

```text
positive cases recovered exactly: 12 / 12
negative cases rejected:           7 / 7
false promotions:                  0
independent baseline mismatches:   0
same-ID validation/holdout leakage probes: pass
```

This is a controlled exact-rational benchmark, not evidence of general scientific induction.

## 18. Deterministic rejection conditions

A conforming implementation rejects at least:

- wrong seed, base-world, or handoff binding;
- bad content hash at any nested level;
- duplicate or unsorted observation IDs;
- noncanonical or invalid rationals;
- absent observations;
- unsupported split strategy or hypothesis family;
- split minima exceeding data count;
- fewer than two training observations;
- candidate-budget overflow;
- stale promotion parent;
- duplicate committed observation-set session;
- missing or corrupted evidence object;
- noncanonical immutable object bytes;
- commit cycles or sequence gaps;
- transaction/snapshot mismatch; and
- strict audit with any orphan.

## 19. Determinism theorem

For fixed canonical seed, literal handoff, observation-set bytes, policies, budgets, base commit, and implementation profile, every conforming implementation produces equal:

```text
split IDs
candidate coefficient set
training rank
selected candidate
residual tables
contradiction/counterexample records
acceptance decision
learning certificate
promotion transaction
snapshot
commit
reconstruction semantic hash
```

This follows because all inputs are content-addressed, split assignment is an exact hash order over IDs, arithmetic is exact rational, pair and candidate ordering are total, acceptance gates are explicit, serialization is canonical JSON, and commit publication is parent-bound.

## 20. Evidence boundary

Version 0.5 demonstrates exact affine induction over finite exact-rational observations. It does not demonstrate:

- noisy statistical regression or calibrated uncertainty;
- polynomial, piecewise, differential-equation, causal-graph, program, language, or multimodal induction;
- automatic ontology discovery;
- autonomous experiment design;
- semantic memory consolidation;
- general planning or tool use;
- grounded perception;
- physical GPU learner execution; or
- AGI.

The next milestone should add a typed finite family registry and one non-affine hypothesis family while retaining strict data-split isolation, independent baselines, counterexample retention, and parent-bound promotion.

---

**End of normative TOM Learner 0.1 / World & Query Kernel 0.5 specification.**
