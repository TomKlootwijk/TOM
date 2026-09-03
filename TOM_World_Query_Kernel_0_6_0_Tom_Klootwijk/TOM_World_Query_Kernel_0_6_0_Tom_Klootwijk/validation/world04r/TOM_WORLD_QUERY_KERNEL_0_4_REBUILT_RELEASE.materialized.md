# TOM World & Query Kernel 0.4.1 — Corrective Rebuild

## Trust-reset release from corrected 0.3

This package replaces the previous 0.4.0 line. The old 0.4 package is not used as source or validation evidence.

The rebuild begins with the corrected 0.3 archive:

```text
SHA-256 a7103ec92596fd54198e4a902f078712cf8eafcdf1e45320bbdc02dd53947278
```

and pins the corrected interval implementation:

```text
src/python/tom_world03/interval.py
ea7b3ff2127e8ee7a696eb45e84ae9efdbca7c10c532617c51888fb13cd39f6d
```

The rejected pre-correction hash is recorded as:

```text
d6bef5b9704a3e5444d86b76e73f6b90a51fdbbf624a6c4705ed0bc7cdef9d4b
```

## The compounding problem that was removed

The superseded design allowed a relation to supply `continuation_until`, then used that supplied value as the segment end and successor start. That is circular: the value that `next_event` should discover was already present as source metadata. If it is wrong, each later segment inherits the wrong start and compounds the error.

Version 0.4.1 forbids that field. Every segment begins as an exact affine continuation open to the fixed world horizon. The corrected 0.3 event solver discovers the next exact root. Only then is the current segment sealed and a successor created.

```text
open [start,horizon]
→ certified next exact event
→ atomic simultaneous transition
→ immutable realized seal [start,event]
→ successor [event,horizon]
→ once-fired relation exclusion
→ repeat
```

## Canonical result

The fixture contains 1,208 relations: eight causal relations and 1,200 decoys. It discovers four simultaneous event sets at exact times:

```text
2, 5, 7, 9
```

The realized rate sequence is:

```text
x' = 1, 2, -3, 1/2, 0
```

and the exact state at the horizon is:

```text
clock=10
counter=34
mode=5
output=90
x=3
```

Semantic-chain identity:

```text
sha256:9fd4f3e1ae8550ae3ca99e27e7bf61b22a4935fe764fd443723abfdb3804f226
```

The indexed path processes 796 aggregate candidates; exhaustive enumeration processes 12,046. Both produce the same semantics. A separate `fractions.Fraction` baseline, importing neither the corrected 0.3 kernel nor the new 0.4.1 kernel, produces the same semantic hash.

## Persistent proof

The journal contains one genesis commit, four event commits, and one explicit horizon-finalization commit. It records 19 reachable immutable objects and six transactions. Strict audit returns no error or orphan. Reconstruction reproduces the direct semantic-chain hash.

## TOMAGI compatibility

The underlying 128-byte header, 64-byte `State64`, 48-byte `Cell48`, and sixteen opcodes remain unchanged. A 15-cell TOMAGI anchor program matches all eleven integer trajectory points and yields byte-equal canonical Python/C full traces.

## Validation

The release validates:

- the corrected 0.3 archive and pinned inherited source hashes;
- full rational interval sign classification;
- strict world schema and nested content hashes;
- absence and rejection of `continuation_until`;
- exact solver-derived event boundaries;
- indexed/exhaustive/baseline semantic equality;
- conflict-checked atomic transitions;
- once-only event firing;
- complete journal audit and reconstruction;
- corruption, missing-object, orphan, stale-state, unresolved-relation, and budget rejection;
- unchanged TOMAGI ABI and equal Python/C traces; and
- clean generated-output-free archive replay.

The full normative definition is `spec/TOM_WORLD_QUERY_KERNEL_0_4_REBUILT.md`. The trust reset is documented in `docs/TRUST_RESET_0_4.md`.

## Current boundary

This release does not claim arbitrary nonlinear dynamics or AGI. It repairs and completes the exact piecewise-affine continuation milestone. The next stage is a learner prototype in which observations may propose definitions, but only explicit content-addressed verification and promotion transactions can make a proposal authoritative.
