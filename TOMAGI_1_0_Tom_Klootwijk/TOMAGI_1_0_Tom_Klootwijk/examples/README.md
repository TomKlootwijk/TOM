# Examples

## `tomagi_engine_portrait.json`

The engine portrait is a perpetual TOMAGI program rather than a picture assembled outside the machine. Every ten-transition cycle executes the complete literal chain `SDF0 -> JIT1 -> KIN2 -> PHI -> KLEIN -> HINGE -> LSYS -> CONE -> PROJECT -> EMIT`, after which both emission routes return to `SDF0` without setting `HALT`. Its default 640-transition horizon produces 64 deterministic emission records: 30 `PYRA` and 34 `CIRC`. The final replay lineage is `516999469` and the final output is `CIRC` (`0x43495243`).

`tomagi_engine_portrait.json` is the editable, content-addressed source and `tomagi_engine_portrait.tmg` is its 800-byte compiled `Cell48` graph. TOMAGI's native SVG projection consumes the resulting `State64` trace and `EMIT` records:

```bash
PYTHONPATH=src/python python -m tomagi render \
  examples/tomagi_engine_portrait.tmg examples/tomagi_engine_portrait.svg \
  --trace-output examples/tomagi_engine_portrait.trace.json \
  --manifest examples/tomagi_engine_portrait.manifest.json
```

This gives the complete first-party path `source JSON -> compiled .tmg -> trace -> SVG/manifest`. SVG serialization is an engine backend; it does not change the fixed-width runtime, infer missing geometry or claim a general raster/game-rendering facility.

## `polar_loop.json`

Literal operator chain demonstrating `SDF0 -> JIT1 -> KIN2 -> PHI -> KLEIN -> HINGE -> LSYS -> CONE -> PROJECT -> EMIT`. `KLEIN` selects one of two branch-indexed hinge cells, and both routes preserve the complete chain. It compiles to `polar_loop.tmg`; regenerate that binary and its checked Python/C final-state fixture after changing the JSON source.

## `exact19_rule.json`

A tiny compiled deterministic rule. The input is encoded in `rho`; a zero-width cone relation tests `rho=19` and emits token `19` or `0`.

## `nineteen_hinge.json` and `nineteen_hinge.expected.json`

Source-derived high-level record for the separate representations of 19: numeric value, binary active-bit positions, Dutch profile segments, equal feature counts and a chosen three-pulse triangle projection.
