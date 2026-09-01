# TOMAGI q4 vertex-face CCD bridge profile 1.0

## 1. Status and scope

This document is normative for `ccd_vf_q4.source.json`. It specializes the
TOM Seeded Compilation Profile 1.0 and TOMAGI ABI 1.0 shipped at
`<repository-root>/TOM_Genesis_1_0_Tom_Klootwijk.zip` to one exact, stationary-face,
zero-thickness vertex-face query on a four-tick grid. The inherited profile and
ABI govern anything not redefined here.

This profile is not a general continuous root solver. “Exact” below means exact
fixed-width execution for the declared q4 fixture.

## 2. Authoritative inputs

The compiler SHALL consume:

1. `<repository-root>/TOM_seed_genome_2026-09-01.txt`, exactly 244 bytes with SHA-256
   `d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5`;
2. `ccd_vf_q4.source.json`, whose definitions SHALL carry valid canonical
   content hashes;
3. `token_registry_1_0.json`, canonical content hash
   `sha256:b14140cf9800e186701557ed982d692931966ea957e5790c1e6b4989e854c609`;
4. the Genesis runtime archive with SHA-256
   `ca5214eb9691f4f1e8b9a8e025fa3eb0b7d6003fcb55c0364d9e874be3483152`.

The seed grammar is the exact Genesis grammar: the `TOM1` prefix, bracketed
profile, pipe-delimited attribution/date/version fields, and the ordered
operator expression ending in `support>compatibility>guard>event>transition>lineage`.
No Unicode normalization, whitespace insertion, or terminal newline is allowed.

## 3. Canonical definitions and dependency evaluation

A definition hash is SHA-256 over UTF-8 JSON after removing `content_hash` and
serializing with keys sorted, no insignificant whitespace, and unescaped
Unicode. The hash is encoded as lowercase `sha256:<64 hex digits>`.

Definitions form a finite DAG. IDs and `(phase, ordinal)` pairs SHALL be unique;
all dependencies SHALL exist and precede dependants; inputs SHALL name declared
dependencies of compatible evaluated types; every definition SHALL be reachable
from `program:root`. Evaluation follows the unique topological phase schedule.

## 4. Fixture and State64 interpretation

Let `T = tick/4`. The closed triangle and moving vertex are:

```text
A=(0,0,0), B=(1,0,0), C=(0,1,0)
P(T)=(1/4,1/4,3/4-T), 0 <= T <= 1
```

The q4 State64 mapping is:

```text
rho   = 4 * signed separation from z=0
theta = 4 * x
phi   = 4 * y
tick  = 4 * T
vrho  = -1
vtick = 1
```

Initial runtime cells set `(rho,theta,tick,phi,vrho,vtick)` to
`(3,1,0,1,-1,1)`.

## 5. Formal runtime operations

The selected definition graph SHALL lower the following operations to literal
Cell48 records:

1. `SET` constructs the declared q4 state.
2. `KIN2` applies `rho := rho + vrho` and `tick := tick + vtick` with TOMAGI
   fixed-width semantics.
3. `CONE(0,0,1,1)` sets its branch only when `rho=0` and `theta` is in `[0,2]`.
4. `SPHERE(0,0,1,1)` sets its branch only when `rho=0` and `phi` is in `[0,2]`.
5. The conjunction of those support regions is contained in the declared right
   triangle because `0<=x<=1/2` and `0<=y<=1/2` imply `x+y<=1`.
6. `RADIX(14)` selects packed tick bit 2; under the maintained `tick<=4`
   invariant this distinguishes the terminal quarter-grid horizon.
7. A successful support branch enters the HIT byte-EMIT chain. Reaching the
   horizon or failing the second support guard enters the MISS chain.

For the authoritative fixture, three KIN2 steps SHALL produce `rho=0,tick=3`,
so the selected certificate SHALL state `HIT` at `3/4`.

## 6. Lowering, packing, and materialization

`tomagi.cell` definitions lower to fixed-width Cell48 records. Canonical JSON
certificate records lower through `json.canonical_bytes` and
`tomagi.emit_bytes`. Each EMIT payload contains one to four consecutive artifact
bytes packed little-endian; its flags encode the byte count. Keys are unique and
sorted in the `.tmg` cell table. Execution begins at `cell:set-rho`.

The generic materializer SHALL inspect only executed byte-mode EMIT records,
decode their payload byte counts, and concatenate bytes in execution order. It
SHALL NOT interpret CCD or JSON semantics. The last selected EMIT SHALL halt.

## 7. Rejection conditions and limits

Compilation or validation SHALL reject a wrong seed length/hash/grammar, token
registry mismatch, invalid definition hash, unknown/cyclic dependency,
ambiguous schedule, unreachable definition, type mismatch, invalid Cell48
successor/key/opcode, exceeded declared budget, non-byte executed EMIT, missing
halt, certificate/State64 tick disagreement, reference-solver disagreement, or
any unequal isolated rebuild boundary.

The binding limits are those in `ccd_vf_q4.source.json`: at most 64 definitions,
32 dependencies per definition, 4,096 literal/output bytes, 512 cells/ticks,
16,384 operation steps, 4,096 sequence items, one repeat, and zero recursion.

## 8. Provenance and replay theorem

`ccd_vf_q4.proof.json` records the hashes and sizes of the definition source,
normative profile, validator, root seed, token registry, Genesis runtime,
reference-solver sources, and every reproducible output boundary. It also
records the Python/NumPy oracle environment. The v0.5 floating-point solver is
an independent oracle only; it is not used to construct the `.tmg` or emitted
certificate.

Replay theorem: given byte-identical authoritative inputs and a conforming
Genesis compiler/runtime, canonical hashing fixes the definition DAG; typed
evaluation fixes every Cell48 plan; canonical key sorting fixes the `.tmg`;
deterministic State64 transition semantics fix the selected branch and trace;
and ordered byte-mode EMIT decoding fixes the certificate bytes. Therefore two
conforming builds and replays produce byte-identical `.tmg`, manifest, trace,
EMIT records, and materialized certificate.
