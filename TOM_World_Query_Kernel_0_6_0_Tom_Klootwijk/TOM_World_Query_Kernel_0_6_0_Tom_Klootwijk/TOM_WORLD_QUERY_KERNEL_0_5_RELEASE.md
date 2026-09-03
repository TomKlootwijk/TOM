# TOM World & Query Kernel 0.5.0

## TOM Learner 0.1: observations, hypotheses, evidence, and promotion

Version 0.5 starts the learning layer without changing the frozen TOMAGI machine or treating a generated candidate as automatically authoritative.

The implemented chain is:

```text
canonical TOM seed
-> verified 0.4.2 literal-only handoff
-> exact rational observations
-> deterministic ID-only train/validation/holdout split
-> train-only affine candidate induction
-> train-only selection
-> validation and holdout gates
-> contradiction and counterexample records
-> learning certificate
-> parent-bound promotion transaction
-> append-only learner-overlay commit
```

## Corrected inheritance

The source line is pinned to the 0.4.1 corrective rebuild and corrected V0.3 interval implementation. Before learner construction, 47 inherited authority files are checked by exact path, length, and SHA-256. Generated V0.4 evidence, journals, traces, and artifacts are excluded from authority.

The directly supplied 0.4.2 ZIP was not exposed to the implementation runtime and therefore was not silently trusted or used. The package contains an independently reconstructed literal-only handoff from the verified 0.4.1 source archive. This distinction is recorded so the trust chain does not compound an unavailable archive.

## Learning profile

The first hypothesis family is deliberately small:

```text
y = a*t + b
```

All values are reduced exact rationals. Candidates are generated from every distinct-input unordered training pair. Validation and holdout values cannot influence coefficients or training rank.

Split assignment hashes only:

```text
canonical seed hash
observation-set ID
split-policy hash and salt
observation ID
```

It never hashes the target value. Same-ID mutations in validation and holdout preserve split membership, fit-input identity, and selected coefficients while changing the final acceptance result.

## Benchmark result

The canonical suite contains 19 literal data sets:

| Class | Count | Result |
|---|---:|---:|
| Exact affine, integer/rational coefficients | 12 | 12 recovered exactly |
| Training outlier | 1 | rejected |
| Validation outlier | 1 | rejected |
| Holdout outlier | 1 | rejected |
| Piecewise change | 1 | rejected |
| Contradictory exact observations | 1 | rejected |
| Constant-input underdetermination | 1 | rejected |
| Excessive literal complexity | 1 | rejected |

Recorded aggregate:

```text
accepted:                    12
negative cases rejected:      7
false promotions:             0
coefficient recovery errors:  0
independent baseline mismatches: 0
```

The independent baseline is a separate standard-library `fractions.Fraction` implementation of split, fit, rank, gates, and contradictions.

## Authoritative promotion

A learning certificate is only a proposal. Authority changes only through an append-only promotion store. Every transaction declares the expected parent commit and the complete ordered list of literal and derived evidence hashes. A stale parent rejects. An accepted session publishes one learned `SDF0@Def` relation; a rejected session publishes no definition but retains its candidates, residuals, counterexamples, and rejection lineage.

The canonical benchmark store records:

```text
20 commits: 1 genesis + 19 learning sessions
12 accepted definitions
7 rejected sessions
659 immutable evidence objects
strict audit: valid
orphans: 0
```

## Validation

Validation covers:

- exact canonical seed identity;
- all 47 handoff file pins;
- inherited V0.4.1 semantic/validation identities;
- absence of `continuation_until` and the superseded namespace;
- strict schema and nested hash validation;
- deterministic label-independent splits;
- train-only fit and selection;
- same-ID validation/holdout leakage probes;
- exact positive recovery and zero false promotions;
- independent baseline agreement;
- contradiction, counterexample, and rejection retention;
- stale-parent rejection;
- complete evidence enumeration in transactions;
- strict and permissive orphan policy;
- immutable byte corruption detection;
- append-only reconstruction;
- all inherited TOMAGI/world tests; and
- clean generated-output-free replay.

This release document is itself packaged as literal bytes in a seeded TOMAGI definition, compiled to `Cell48` EMIT records, executed by Python and C, and generically materialized byte-identically.

## Current boundary

This is not AGI. It is the first evidence-disciplined learner profile: one exact hypothesis family, explicit holdout isolation, falsifiable rejection, and an authoritative promotion transaction. The next milestone is a finite typed hypothesis-family registry with polynomial and piecewise candidates, uncertainty records, and cross-domain selection tests—without weakening the authority boundary.
