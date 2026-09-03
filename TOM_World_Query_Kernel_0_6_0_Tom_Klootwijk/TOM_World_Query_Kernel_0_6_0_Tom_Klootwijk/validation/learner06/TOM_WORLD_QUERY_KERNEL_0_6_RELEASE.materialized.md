# TOM Learner 0.2 / World & Query Kernel 0.6

## Finite typed hypothesis-family authority

Release: **0.6.0**  
Validation revision: **2026-09-03**  
Authority root: `TOM_seed_genome_2026-09-01.txt`

## Result

WQK 0.6 continues from the repaired 0.5.2 transaction-authority boundary. It does not bypass the CODEX kernel corrections and it does not move a semantic winner into host Python. The formal authority now evaluates a finite registry containing four typed hypothesis families, records ambiguity instead of silently breaking ties, checks supersession against pinned prior definitions, and publishes accepted or rejected outcomes through the repaired parent-bound 0.5.2 promotion transaction.

The exact chain is:

```text
canonical 244-byte TOM seed
-> CODEX-repaired 0.5.2 kernel boundary
-> content-addressed family registry and exact data sets
-> static bounded formal learner
-> independent fractions.Fraction oracle
-> ambiguity / counterexample / contradiction / regression records
-> static formal promotion continuation
-> deterministic Cell48 lowering
-> equal Python/C TOMAGI execution
-> replay-authenticated EMIT materialization
-> same-host locked immutable publication
-> reconstructed terminal HEAD
```

## Kernel repairs retained

The release regression-tests the six corrective requirements received with the 0.5.2 repair handoff:

1. C arithmetic uses defined wider intermediates and explicit `wrap32` lowering.
2. Python and C reject every nonzero value in the six reserved TOMAGI header words.
3. Publication locking spans expected-HEAD read, immutable verification, and atomic replacement.
4. Recursive formal values and fold accumulators are checked before parent consumption.
5. Packaging excludes inherited inventory products and volatile transcripts and requires reproducible clean builds.
6. The public `audit-store` command uses `SOURCE STORE` argument order.

The store lock coordinates threads and processes on one supported host. It is not a distributed consensus protocol.

The validation revision additionally closes rehashed formal-authority bypasses,
enforces declared partition order and exact promotion-context bindings, makes
formal JSON equality type-strict, validates direct and loaded programs against
the same fixed-width contracts, and aligns extreme-value GPU source equations
with the CPU definition. Canonical JSON is now strictly JSON-native, and string
limits cover parameters, provenance, and generated cell identifiers while
decoded byte literals remain governed by the output-byte budget. Durable GPU
evidence is limited to source-level contract assertions plus Python/C
extreme-vector conformance; it is not a claim of physical GPU dispatch.

## Four finite families

| Family | Typed search space | Candidates |
|---|---|---:|
| Exact polynomial | Rational coefficients, degree at most two | 34 |
| Piecewise affine | One exact breakpoint, two affine branches, left-inclusive boundary | 21 |
| Transition table | Complete `A/B/C` to `red/green/blue` tables | 27 |
| Expression tree | Depth-two bounded trees over a declared operation registry | 39 |
| **Total** |  | **121** |

The registry is itself content-addressed:

```text
sha256:06952f2ff0d961ca6a92d20c00d3996916009e35e47d903659893a48630d65a4
```

Every family declares a semantic version, domain and codomain, finite candidate
list, complexity data, and a maximum-candidate budget. The expression-tree
family additionally declares its closed operation vocabulary. Search
termination is recorded per data set.

## Evidence isolation and decision semantics

Each data set contains explicit train, validation, and holdout partitions. Candidate evaluation and survivor selection use only training observations. Validation and holdout evidence may reject the train-derived proposal but may not generate candidates, reorder the train survivors, or select coefficients.

The decision profile is:

```text
zero train survivor       -> reject: no-exact-train-candidate
one train survivor        -> validation gate -> holdout audit -> regression gate
multiple distinct survivors -> reject: ambiguous-train-survivors
```

An ambiguity record contains every surviving candidate hash, family identity, survivor count, and the explicit resolution `reject-without-hidden-tie-break`. No host-side stable-sort winner is promoted.

## Supersession and regression impact

A proposed definition may name one existing authoritative definition to supersede. Before acceptance, the formal learner evaluates the proposed replacement against every pinned regression case in the prior authority set. The regression-impact certificate records the tested definition hashes, replacement identity, every case result, and the aggregate decision.

A proposal that changes pinned prior behavior is rejected even when it exactly fits its own train, validation, and holdout observations.

## Canonical benchmark

```text
families:          4
candidates:      121
data sets:        16
accepted:          9
rejected:          7
ambiguities:       3
false promotions:  0
```

Accepted cases include exact quadratic, affine-supersession, constant polynomial, two piecewise-affine relations, two transition tables, absolute-value expression, and square-plus-one expression.

Rejected cases cover a validation counterexample, within-family piecewise ambiguity, symbolic contradiction, expression-tree ambiguity, cross-family ambiguity, failed supersession regression, and a polynomial outside the finite search space.

The independent `fractions.Fraction` oracle agrees with all sixteen formal outcomes.

## Formal learner execution

```text
formal program content hash:
sha256:a07d27c1fe88b75b56f19d1e623a170da6ee3271c3638836f7badf079ec170c3

formal result content hash:
sha256:f083b793cf3d38061f900935a13f9d5d29c8aefcc5245b6c89a21252475041ce

compiled .tmg:
32,880 Cell48 records
1,578,368 bytes
sha256:5feac19609ed9577688990e1e5adeb7caa81c05d9e26da559ec93be45899c3cf

materialized result:
131,517 bytes
sha256:4e59666a7ccdc2505d94fe760f5d317f5302f8766a6bd8f1b022912890e5844a
```

Python and C produce equal complete 32,880-step traces, equal EMIT sequences, and equal result bytes.

## Formal promotion continuation

The promotion plan begins at the repaired 0.5.2 terminal head:

```text
initial HEAD:
sha256:a3bd8ecd8578b28158b96a3dce814910beb3d627068159dc668a682c85b85448
```

It contains forty-one addressed base records and sixteen publications numbered 20 through 35. Each publication carries its expected head, replacement commit, complete required-evidence set, immutable writes, decision, accepted definition or rejection lineage, and content hash.

```text
formal promotion program content hash:
sha256:0132cd7aee9e143d0c5479edb396aa85e22f7c1ced346571a946db51171e79d6

publication-plan content hash:
sha256:335b3349591e489af6c67c16b563547997f5e7cb29d4a1e685476b1cff69510c

compiled .tmg:
157,014 Cell48 records
7,536,800 bytes
sha256:fe32d60b54a8fc38e0bf07f3ad7311af01d485ccf342488a880d69bc455a0b6b

materialized promotion value:
628,055 bytes
sha256:9e1d55a17bf45db48cc22588a4a7168ae2dc10720f2edb557130c3ad80318663

terminal HEAD:
sha256:f52198541544eff90df272327236af75c4dd729b77cdf75628b0bad0bf17502e
```

The generic immutable store contains 176 files and 597,515 bytes after publication. Its deterministic tree hash is:

```text
sha256:d125c28b7570cd2edae109747557cdc07573ec28ac141fe50f9059250eaa4787
```

Audit and reconstruction report sixteen commits, nine accepted definitions, seven rejected sessions, no missing required record, and no unplanned record.

## Validation

Before clean-build and final-package replay, the core validation records:

```text
complete tests:           283 passed
core validation checks:    18 passed, 0 failed
rejection cases:           20 passed
TOMAGI ABI:                128-byte header / 64-byte State64 / 48-byte Cell48 / 16 opcodes
```

The rejection capsule covers registry and exact-budget mutations, undeclared
expression operations, malformed candidate and supersession identities,
unresolved partitions, failed repair proof, stale promotion context and
continuation ancestry, missing base evidence, noncontiguous publication order,
unavailable evidence, stale same-host publication, forged traces, nonzero
reserved headers, non-finite canonical JSON, intermediate formal-value
overflow, ambiguity promotion, and regression-impact promotion.

The final release record additionally requires two generated-output-free builds, equal declared boundaries, equal promotion-store trees, deterministic package bytes, internal manifest and checksum verification, and a clean replay from the finished ZIP.

## Commands

```bash
make learner06
make test-learner06
make validate-learner06
make package-learner06
```

Public CLI examples:

```bash
PYTHONPATH=src/python python3 -m tom_learner06 oracle \
  examples/learner06/family_registry.json \
  examples/learner06/prior_authority.json \
  examples/learner06/datasets/*.json

PYTHONPATH=src/python python3 -m tom_learner06 validate-plan \
  validation/learner06/promotion_authority.direct.json

PYTHONPATH=src/python python3 -m tom_learner06 audit-store \
  validation/learner06/promotion_authority.direct.json \
  examples/learner06/promotion_store
```

## Boundary and next milestone

This release demonstrates exact finite search over four literal families. It does not claim noisy inference, open-domain concept learning, memory, planning, perception, autonomous action, physical GPU execution, general intelligence, or AGI.

The next roadmap milestone is **TOM Learner 0.3 / WQK 0.7**: typed interval-valued observations, a finite noise-family registry, explicit calibration and coverage records, distribution-shift evidence, ambiguity-preserving robust scoring, and unchanged parent-bound promotion authority. Confidence must remain typed evidence and may not become an invisible TOMAGI control path.
