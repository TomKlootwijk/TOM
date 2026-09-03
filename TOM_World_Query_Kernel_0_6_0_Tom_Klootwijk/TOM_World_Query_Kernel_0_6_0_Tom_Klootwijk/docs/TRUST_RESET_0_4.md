# TOM 0.4 trust reset

## Why 0.4.0 is superseded

The previous 0.4.0 package is not used as an upstream source for this release. Review found two independent trust problems:

1. its inherited `src/python/tom_world03/interval.py` was not byte-identical to the corrected 0.3 release; and
2. its continuation architecture allowed the next segment boundary to be supplied in relation metadata (`continuation_until`) and then required the event solver to agree with that supplied boundary.

The second pattern is circular. A boundary copied into a relation is not independently discovered by `next_event`; making the successor segment begin at that same value can propagate a wrong assumption through every later segment. Validation against fixtures authored with the same values can self-confirm the error.

## Authoritative corrected base

This release starts from only this corrected 0.3 archive:

```text
TOM_World_Query_Kernel_0_3_0_Tom_Klootwijk.zip
bytes       22,217,713
entries     10,291
SHA-256     a7103ec92596fd54198e4a902f078712cf8eafcdf1e45320bbdc02dd53947278
ZIP CRC     pass
```

The inherited critical-file inventory is pinned in `sources/CORRECTED_V0_3_BASELINE_PIN.json`.

The corrected interval implementation is:

```text
src/python/tom_world03/interval.py
SHA-256 ea7b3ff2127e8ee7a696eb45e84ae9efdbca7c10c532617c51888fb13cd39f6d
```

The superseded pre-correction implementation hash is recorded and rejected:

```text
d6bef5b9704a3e5444d86b76e73f6b90a51fdbbf624a6c4705ed0bc7cdef9d4b
```

The relevant correction compares exact rational values to `Q(0)` rather than checking numerator fields as an implementation shortcut. The complete corrected source file—not only that line—is pinned and tested.

## New causal rule

Version 0.4.1 uses an open continuation segment:

```text
[start_time, world_horizon]
```

A relation may declare only its own active interval and zero relation. It may not declare `continuation_until` or another successor boundary.

The causal sequence is now:

```text
open segment
→ index supplies a complete candidate set
→ corrected 0.3 certifier proves exact roots
→ solver selects the earliest exact root
→ event set is content-addressed
→ atomic transition reads one common pre-state
→ current segment is sealed at the solver-produced root
→ successor starts at that root and remains open to the world horizon
→ fired once-only relations are excluded
→ repeat until no later event
→ explicit horizon seal
```

This removes relation-authored future boundaries from the authority chain. The realized segment boundary is a consequence of the event certificate.

## Namespace and provenance isolation

Fresh 0.4 code is under `src/python/tom_world04r/`. The prior `tom_world04` module is absent. The authoritative world declares:

```json
{
  "prior_v0_4_used_as_source": false,
  "implementation_namespace": "tom_world04r"
}
```

The package does retain corrected 0.3 code and evidence so that the inheritance boundary can be rerun and audited.

## Acceptance conditions

The rebuilt line is trusted only when all of these hold:

- the corrected base archive identity and every pinned inherited file match;
- the rejected interval hash is absent from the inherited implementation;
- the strict 0.4.1 schema validates the world;
- no authoritative relation contains `continuation_until`;
- indexed and exhaustive event continuation produce the same semantic chain;
- an independent `fractions.Fraction` implementation produces that same chain;
- every event boundary equals an exact solver certificate;
- every successor extends to the world horizon, rather than to a relation-supplied endpoint;
- journal reconstruction reproduces the semantic-chain hash;
- corrupted world, segment, event, transition, seal, transaction, or commit bytes are detected;
- the TOMAGI reference program produces equal Python and C traces;
- the unchanged 128/64/48-byte TOMAGI ABI is preserved; and
- a generated-output-free clean archive reproduces the recorded boundaries byte-for-byte.

The validation report in `validation/world04r/validation_report.json` records the result. No result from the superseded 0.4.0 package is used as evidence.
