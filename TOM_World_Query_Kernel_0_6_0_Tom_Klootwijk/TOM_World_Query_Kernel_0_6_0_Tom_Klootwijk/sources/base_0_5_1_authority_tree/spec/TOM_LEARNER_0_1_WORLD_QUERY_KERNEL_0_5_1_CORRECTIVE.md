# TOM Learner 0.1 / World & Query Kernel 0.5.1 — Corrective Authority Profile

**Normative profile:** `TOM-LEARNER-0.1-CORRECTIVE`  
**Implementation release:** `0.5.1`  
**Seeded compilation profile:** `TOM-SEEDED-COMPILATION-1.0`  
**Underlying machine:** TOMAGI ABI 1.0  
**Canonical root:** `TOM_seed_genome_2026-09-01.txt`

## 1. Status and correction

This document is the normative integration profile for the corrected finite
affine learner. It supersedes the authority assignment in
`TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5.md`.

Version 0.5.0 placed the learner algorithm in the host package
`tom_learner05`. Its benchmark was deterministic and well tested, but that
placement violated the repository requirement that domain behavior be an
executable literal TOMAGI input. Passing the old tests did not cure that
authority defect.

In 0.5.1 the authoritative computation is:

```text
canonical seed bytes and token registry
+ content-addressed seeded definition graph
+ 19 content-addressed literal observation documents
+ content-addressed bounded formal learner program
-> validated dependency evaluation
-> deterministic Cell48 lowering
-> TOMAGI execution
-> ordered authenticated EMIT records
-> canonical learner-result bytes
```

The Python package `tom_learner05` MAY be used as an independent oracle and as
the append-only proposal/evidence store. It MUST NOT be treated as the causal
authority for the corrected learner result.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHOULD**, and
**MAY** are normative.

## 2. Incorporated source-to-byte specification

`TOM_SEEDED_COMPILATION_1_0.md` is incorporated here by reference and is
normative in full. It specifies:

- the 244-byte seed grammar and exact token registry;
- finite canonical JSON and content hashing;
- seeded-document and definition schemas;
- strict field, kind, domain, codomain, phase, dependency, parameter,
  provenance, and limit validation;
- the complete generic operation registry;
- bounded exact formal-expression evaluation;
- deterministic definition ordering and value encoding;
- `Cell48`, header, state, flags, byte packing, and EMIT ordering;
- authenticated trace materialization;
- rejection conditions and resource limits; and
- the determinism and replay theorem.

An implementation claiming this corrective learner profile MUST conform to
both specifications. An implementation that only reproduces the final JSON by
calling `tom_learner05.learn` does not conform.

## 3. Corrective inheritance boundary

The inherited base is identified by:

```text
TOM-LITERAL-HANDOFF-0.4.2
sha256:3d2b46cfd33ba6e5cf0a13697fb59e374a64ad30450fdd3c256c98a04ebc474b
```

The corrective overlay is:

```text
sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json
content hash: the verified `content_hash` field in that record
```

Before generated evidence is read, a conforming build MUST verify:

1. all 44 unchanged inherited files against the 0.4.2 handoff;
2. each of the three replacement paths against its new byte length and hash;
3. each preserved prior copy against the old 0.4.2 byte length and hash;
4. every declared corrective addition;
5. the overlay content hash; and
6. the exact seed bytes, including the absence of a trailing newline.

The replaced paths are only:

```text
src/python/tomagi/canonical.py
src/python/tomagi/compiler.py
src/python/tomagi/materialize.py
```

The old bytes MUST remain available below
`sources/base_0_4_2_replaced/` at their original relative paths.

## 4. Literal learner authority

The formal program is the static file:

```text
examples/learner05/learner05_affine_authority.formal.json
file sha256:007a10013ca4d9aff4344736468ea6fab75efcfb03d6ca7a65ab7a3a4add194b
content hash: sha256:dd710388744a71861c90c15ef63bd85411f0652a2077f6f9ef9421997d626b28
```

The seeded definition graph is:

```text
examples/learner05/learner05_formal_authority.literal.json
file sha256:9bb103aca371da06b24c7dc1e8f9f23f1ba72e38820872238a2d2c6a6c4bc418
```

The graph MUST load the formal program and all 19 observation-set documents
using `source.json`. Every such input binds its normalized relative path, byte
length, SHA-256, UTF-8 decoding, top-level object shape, canonical-JSON-plus-LF
encoding, and internal content hash. A mismatch MUST reject compilation.

The graph MUST use only generic seeded operations. In particular:

```text
seed.bytes
seed.tokens
source.json
sequence.construct
formal.evaluate
canonical.encode
hash.sha256
literal
state64.construct
emit.graph
assert.equal
program.construct
```

Host code MAY parse, validate, hash, evaluate the declared formal operation,
lower, execute, capture traces, and materialize bytes. Host code MUST NOT
replace the formal learner with a special affine-learning branch.

## 5. Exact bounded learner semantics

The formal program consumes the observation-set sequence in declared order and
returns one result row per set. For each set it MUST perform the following
declared operations:

1. validate and allocate train, validation, and holdout counts by the
   largest-remainder rule;
2. assign observations using SHA-256 over identifiers and policy data only;
3. form every unordered training pair with distinct input values;
4. compute exact reduced-rational coefficients `a` and `b` for `y=a*t+b`;
5. deduplicate semantically equal candidates;
6. rank and select using training evidence only;
7. calculate the specified signed-numerator/denominator bit complexity;
8. evaluate validation, holdout, complexity, underdetermination, and exact
   contradiction gates;
9. record deterministic acceptance/rejection reasons and evidence; and
10. construct an addressed executable `SDF0@Def` relation for each accepted
    hypothesis.

Binary floating point, clock input, random input, filesystem enumeration,
network input, ambient locale, and unordered-map iteration MUST NOT affect the
formal result.

The formal evaluator limits for this authority are:

```text
max_steps             2,000,000
max_depth                   192
max_collection_items     20,000
max_value_nodes        2,000,000
max_canonical_bytes    8,000,000
```

The recorded accepted evaluation uses 131,478 formal steps. Exhausting any
limit MUST reject; it MUST NOT return a partial learner result.

## 6. Lowering and execution identities

For the literal sources shipped in this release, compilation and execution
MUST reproduce:

```text
compiled program: examples/learner05/learner05_formal_authority.tmg
cells:            19,540
program bytes:    938,048
program SHA-256:  ffb4bdfa6939e81124f65165236004c547c1c1b019ac3080c06375b0413029ea

materialized result bytes:   78,160
materialized result SHA-256: dd9a0c20c8f721c764580f6655bb509001a7ef59000d0cd1bd5826971b72cb82
formal result content hash:  14c5e5e0dd4bc49d40eb8b8f3d86fbdb7bad4d86c872dbeea9799a5aeb92dd12
```

The emitted result is canonical JSON followed by exactly one LF. Its wrapper
MUST verify its own content hash. It MUST contain 19 result rows, 12 accepted
rows, 7 rejected rows, and zero coefficient-recovery errors against the
independent exact-rational oracle.

The Python and C TOMAGI interpreters MUST produce identical complete states and
trace rows for the compiled program. Materialization MUST first authenticate
the supplied trace as the exact canonical initial-state execution prefix. A
reordered, duplicated, omitted-middle, forged, or noncanonical row MUST reject.

## 7. Compatibility

TOMAGI ABI 1.0 remains unchanged:

| Boundary | Value |
|---|---:|
| header | 128 bytes |
| `State64` | 64 bytes |
| `Cell48` | 48 bytes |
| opcodes | 16 |
| ABI version | `0x00010000` |

The corrective compiler MUST reproduce the three previously shipped seeded
programs byte-for-byte. Existing valid literal cell programs retain their
prior meaning. The correction tightens rejection at compiler and
materialization boundaries; it does not add a runtime opcode.

## 8. Validation and replay requirements

A release validation claim MUST be based on a generated-output-free copy. It
MUST rebuild the formal artifact, old release-document artifact, benchmark
fixture/store, tests, validation report, and clean-rebuild certificate. It MUST
compare every declared boundary byte-for-byte with the packaged tree.

Cache files, bytecode, VCS metadata, build executables, elapsed durations, and
host-specific temporary paths MUST NOT enter reproducible hashes. A package
claim MUST independently construct a second deterministic ZIP and require the
two ZIP byte streams to be equal.

Evidence records MUST state failure rather than silently refreshing a pinned
literal authority. Updating the formal program or seeded definition graph is a
semantic change and requires new hashes and a versioned corrective overlay.

## 9. Claim boundary

This profile proves deterministic exact affine induction over the 19 shipped
finite exact-rational observation sets under the stated resource bounds. It
does not prove learning outside that profile. It makes no claim of noisy or
open-domain learning, natural-language understanding, perception, planning,
autonomous goal formation, physical GPU learner execution, or AGI.

**End of normative corrective learner profile.**
