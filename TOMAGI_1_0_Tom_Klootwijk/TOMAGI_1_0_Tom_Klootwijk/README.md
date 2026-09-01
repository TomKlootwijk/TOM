# TOMAGI 1.0

**Topological Operator Machine for Analytic Geometric Inference**

TOMAGI is the engine: a deterministic, content-addressed operator machine whose execution core is compiled into a fixed-width log-polar look-up table. Its literal core is:

```text
Pi(Cone(LSYS(Branch(Klein(phi(KIN2(JIT1(LUT[SDF0](K)))))))))
```

The 1-bit parity/jitter result is a route and perturbation primitive. It is not an error-correction flag. `SDF0` is embedded in the LUT itself: every defined cell has relation value zero, and an address outside the finite program domain is undefined.

Functional notation executes from right to left. The shipped literal loop serializes that order as `SDF0 -> JIT1 -> KIN2 -> PHI -> KLEIN -> HINGE -> LSYS -> CONE -> PROJECT -> EMIT`; branch-indexed successors select a hinge route without skipping a stage.

TOMAGI does not contain learned weights, sampling, embeddings, confidence scores, stochastic state, damping, ECC, restoration forces, safe mode, or a hidden frame loop. A task becomes a TOMAGI task by compiling its literals, relations, branches, topology maps and output tokens into a finite `Cell48` graph. The core executes that graph and produces `State64` records. Definition genomes may authenticate a trace, select records, project integer fields and format records; the compiler evaluates that pipeline and lowers the resulting bytes to ordinary `EMIT` cells. The generic host-side `materialize` command only replays those bytes. It contains no SVG, OBJ, CSV, shape or dimensional semantics. In a compiled domain, this whole path is a deterministic substitute for learned inference.

The first-party artifact path is explicit and replayable:

```text
definition-driven orbit -> compiled .tmg -> authenticated State64 trace
  -> authenticated_trace -> select_records -> project_fields -> format_records
  -> compile-time EMIT-byte lowering -> generic byte replay -> SVG | OBJ | CSV
```

## Delivered implementations and host tools

- dependency-free Python reference runtime and compiler;
- portable C99 runtime and CLI;
- authenticated definition-genome evaluation and format-agnostic byte materialization;
- GLSL 4.50 compute shader;
- WebGPU WGSL compute shader;
- OpenCL C kernel;
- one shared 64-byte `State64` record, 48-byte `Cell48` record and `.tmg` binary format.

## Quick start

```bash
python -m pip install -e ".[validation]"
make test

# Compile and run the literal polar loop
PYTHONPATH=src/python python -m tomagi compile \
  examples/polar_loop.json examples/polar_loop.tmg
PYTHONPATH=src/python python -m tomagi run \
  examples/polar_loop.tmg --trace

# Compile and record the definition-driven 64-emission state orbit
PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_state_orbit.json examples/tomagi_state_orbit.tmg
PYTHONPATH=src/python python -m tomagi run \
  examples/tomagi_state_orbit.tmg --ticks 640 --trace \
  --output examples/tomagi_state_orbit.trace.json

# Compile and byte-materialize the authenticated 2D SVG representation
PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_state_2d.json examples/tomagi_state_2d.tmg
PYTHONPATH=src/python python -m tomagi materialize \
  examples/tomagi_state_2d.tmg examples/tomagi_state_2d.svg \
  --manifest examples/tomagi_state_2d.manifest.json

# Run the source-derived 19 -> active bits -> three pulses -> triangle example
PYTHONPATH=src/python python -m tomagi nineteen

# Run the C99 evaluator on the same binary program
./build/tomagi-c examples/polar_loop.tmg
```

The current recorded validation ran 62 Python tests and authenticated all three state representations byte-for-byte. Python/C comparisons were not run on the Windows host because the available C evaluator is a Linux ELF executable. GLSL and WGSL received structural source checks; OpenCL was not syntax-checked because Clang was unavailable. No physical GPU dispatch was performed.

## Definition-driven state representations

`tomagi_state_orbit.json` contains ten cells with only `id`, `key` and `definition_ref`; the referenced `tomagi_cell_operation` definitions own every executable field. Its 640-transition replay completes 64 non-halting literal-chain cycles and 64 `EMIT` samples. It ends at entry cell 0 with `(rho,theta,tick,phi)=(680006,218400,3720,2388)`, lineage `1437167731` and output `ORBT`.

The authenticated trace yields three concrete file representations:

- 2D: a 1,774-byte SVG polyline with 64 unique points (`x`: 64 distinct, `y`: 63 distinct);
- 3D: a 1,355-byte OBJ with 64 unique vertices and one ordered open line `1..64` (`x/y/z`: 64/64/60 distinct);
- 4D: a 1,483-byte CSV with 64 unique `(rho,theta,tick,phi)` rows. It is a data representation, not a claim of direct four-dimensional visual rendering.

Exact source, program, artifact and definition-root hashes and the complete reproduction commands are recorded in `examples/README.md`.

## Canonical key

```text
rho   20 bits  [63:44]
theta 18 bits  [43:26]
tick  14 bits  [25:12]
phi   12 bits  [11:0]
```

```text
K = (q_rho << 44) | (q_theta << 26) | (q_tick << 12) | q_phi
```

The package also supplies the distinct, exact MSB round-robin Morton layout and its complete 64-row schedule.

## Package map

- `report/TOMAGI_1_0_Tom_Klootwijk.pdf` - formal engine specification and validation report.
- `spec/TOMAGI_1_0_FORMAL_DEFINITION.md` - editable normative definition.
- `spec/*.json`, `spec/*.csv` - schema, symbols, operators, opcodes, key and ABI layouts, precedence and 322-row source crosswalk.
- `src/python/tomagi/` - Python oracle, compiler and CLI.
- `src/c/` - C99 evaluator.
- `src/gpu/` - GLSL, WGSL and OpenCL kernels.
- `examples/` - definition-driven state orbit, authenticated 2D/3D/4D representations, literal polar loop, exact-19 rule and source-derived feature example.
- `tests/` - executable conformance tests.
- `sources/` - source hash register and retained 211-mechanism knowledge catalog.
- `validation/` - machine-readable validation report and console logs.
- `checksums/SHA256SUMS.txt` - package checksums.

## Attribution

Tom Klootwijk; NL200678942; 10-07-1990. This is requester-supplied attribution and was not independently verified.
