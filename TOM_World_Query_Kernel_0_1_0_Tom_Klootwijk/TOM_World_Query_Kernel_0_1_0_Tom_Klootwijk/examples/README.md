# Examples

## `polar_loop.json`

Literal operator chain demonstrating `SDF0 -> JIT1 -> KIN2 -> KLEIN -> HINGE -> LSYS -> CONE -> EMIT`. It compiles to `polar_loop.tmg` and has a checked Python/C final state.

## `exact19_rule.json`

A tiny compiled deterministic rule. The input is encoded in `rho`; a zero-width cone relation tests `rho=19` and emits token `19` or `0`.

## `nineteen_hinge.json` and `nineteen_hinge.expected.json`

Source-derived high-level record for the separate representations of 19: numeric value, binary active-bit positions, Dutch profile segments, equal feature counts and a chosen three-pulse triangle projection.
