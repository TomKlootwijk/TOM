# Examples

## `tomagi_state_orbit.json`

This is the definition-driven cyclic witness. Its ten cell records contain only `id`, `key` and `definition_ref`; the referenced `tomagi_cell_operation` definitions supply opcode, flags, arguments, successors, payload and auxiliary value. Their dependency hashes form one chain rooted in the exact 244-byte TOM1 seed literal (`d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5`; definition `sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d`).

Every ten-transition cycle executes `SDF0 -> JIT1 -> KIN2 -> PHI -> KLEIN -> HINGE -> LSYS -> CONE -> PROJECT -> EMIT`, then returns to `SDF0` without `HALT`. At 640 transitions the trace contains 64 occurrences of each opcode and 64 `EMIT` samples. All 64 emitted `(rho,theta,tick,phi)` tuples are unique; their component distinct counts are 64, 64, 64 and 62. The final state is `(680006,218400,3720,2388)`, cell 0, lineage `1437167731`, output `ORBT` (`0x4f524254`) and status `26`.

Exact SHA-256 values:

- 11,625-byte source JSON: `f456d0da681ae03ddb40cdc1c4566411b25a24e48d8ab279a9bc94d75a6f9cbd`;
- 608-byte `.tmg`: `349e51a5a402b3295d653ad08f00b55d465ffab7e943fb437d196af948487e3e`;
- 252,941-byte/640-record LF trace: `aa060ad1cdc25d7e95e2cdc36e1338ede0cced27f4791989b0cc287d01b9a14f`.

## Authenticated 2D, 3D and 4D representations

Each representation source declares the same generic definition pipeline:

```text
authenticated_trace -> select_records -> project_fields -> format_records
```

`authenticated_trace` verifies relative source/program/trace hashes, requires the declared source-definition anchors, recompiles the source and compares its bytes with the authenticated program, then replays 640 transitions and compares both the trace and final state. `select_records` selects the 64 `EMIT` records. `project_fields` applies only declared integer affine maps. `format_records` combines those derived records with content-addressed UTF-8 framing and templates.

The compiler evaluates that pipeline and lowers the resulting bytes to sequential `EMIT` cells. `materialize` subsequently executes the lowered `.tmg` and concatenates one-to-four-byte big-endian payload chunks under profile `tomagi-emit-bytes-be-v1`. It does not re-open the orbit trace, interpret fields, project geometry or recognize SVG, OBJ or CSV.

The finalized representations are:

- 2D SVG — root `sha256:532ba6cfc7b0aa42becafa4d4468107a2d3f5185ba7613cbbd5f762d6d5d97ad`; 6,956-byte source `4e9510a9ee659b4895e9521f39f5ed5f12a4c2ea8bbe3959dd5611fb72bb64fc`; 444-cell/21,440-byte `.tmg` `f29dbc09bc85637584db4fec314d904dbecd672b78e51ae1d981c118439a8c95`; 1,774-byte SVG `fcaa3bd926529fe92f382f896cff042708111c10d652ac8c539386f5340f161c`. It contains a 64-point `(theta,rho)` polyline with 64 distinct `x`, 63 distinct `y` and 64 distinct pairs.
- 3D OBJ — root `sha256:e52578589731c7621a136ce606bb003e6a7e883edc59e3a4ca9c3c1889ec864d`; 7,622-byte source `09ae1f5061a15b4d6ad004acb5b8b4cf93faed03994c7b2eac98db5761ceb7c5`; 339-cell/16,400-byte `.tmg` `793446ac860d1f7abf2984e9f98e894741ee8644bcd09efa2bdda91d183ad8d1`; 1,355-byte OBJ `4b356aa10acbd751b19b333db68b87e1f3c6231a7264099efb07349e555e0511`. It contains 64 unique `(rho,theta,phi)` vertices and one ordered open line `1..64`; `x/y/z` have 64/64/60 distinct values.
- 4D CSV — root `sha256:faeb0eb44a2f43e38de571a23201ae6bfa1068623c959a8ef309fc2d75735a08`; 6,064-byte source `ec129e19109db9481a7fe43f47931d4311426f8e287677511ae27b8352109b2c`; 371-cell/17,936-byte `.tmg` `37cb6a789d24ed9e18a81c87412ad3a7f428e8ad178721857762f5eb939ee5fb`; 1,483-byte CSV `d1ac54e5aa0a575c021692a646e6b211acaab63ca8657740f723d06480f853df`. Its 64 rows retain the four raw integer fields `(rho,theta,tick,phi)`. This is an exact four-coordinate data representation, not direct four-dimensional visual rendering.

The LF-canonical manifests are 7,793 bytes / `0c5e2f924bf9937ca29628ba62e41876f05e921c0878c69fcfd4b863a110c4bc` (2D, final lineage `1390009811`), 6,111 bytes / `8ef29b32cc050051bf0e617139f818804b4f2d76ba836f8e407721440eda4a78` (3D, `2395171639`) and 6,621 bytes / `373b6cbd72f6ebc9de5af8f23f0baf2447b30b7640be3c171e245e3cfabdfb3d` (4D, `629103799`).

Only framing, labels, style, separators, integer mappings and record templates are definition-authored. No coordinate row, OBJ vertex/index sequence, CSV sample or completed artifact blob is embedded; all numeric records derive from the authenticated trace.

Reproduction commands:

```bash
PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_state_orbit.json examples/tomagi_state_orbit.tmg
PYTHONPATH=src/python python -m tomagi run \
  examples/tomagi_state_orbit.tmg --ticks 640 --trace \
  --output examples/tomagi_state_orbit.trace.json

PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_state_2d.json examples/tomagi_state_2d.tmg
PYTHONPATH=src/python python -m tomagi materialize \
  examples/tomagi_state_2d.tmg examples/tomagi_state_2d.svg \
  --manifest examples/tomagi_state_2d.manifest.json

PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_state_3d.json examples/tomagi_state_3d.tmg
PYTHONPATH=src/python python -m tomagi materialize \
  examples/tomagi_state_3d.tmg examples/tomagi_state_3d.obj \
  --manifest examples/tomagi_state_3d.manifest.json

PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_state_4d.json examples/tomagi_state_4d.tmg
PYTHONPATH=src/python python -m tomagi materialize \
  examples/tomagi_state_4d.tmg examples/tomagi_state_4d.csv \
  --manifest examples/tomagi_state_4d.manifest.json
```

## `polar_loop.json`

Literal operator chain demonstrating `SDF0 -> JIT1 -> KIN2 -> PHI -> KLEIN -> HINGE -> LSYS -> CONE -> PROJECT -> EMIT`. `KLEIN` selects one of two branch-indexed hinge cells, and both routes preserve the complete chain. It compiles to `polar_loop.tmg`; regenerate that binary and its checked Python/C final-state fixture after changing the JSON source.

## `exact19_rule.json`

A tiny compiled deterministic rule. The input is encoded in `rho`; a zero-width cone relation tests `rho=19` and emits token `19` or `0`.

## `nineteen_hinge.json` and `nineteen_hinge.expected.json`

Source-derived high-level record for the separate representations of 19: numeric value, binary active-bit positions, Dutch profile segments, equal feature counts and a chosen three-pulse triangle projection.
