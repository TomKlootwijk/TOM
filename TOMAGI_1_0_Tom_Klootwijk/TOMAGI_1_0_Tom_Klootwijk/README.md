# TOMAGI 1.0

**Topological Operator Machine for Analytic Geometric Inference**

TOMAGI is the engine: a deterministic, content-addressed operator machine whose execution core is compiled into a fixed-width log-polar look-up table. Its literal core is:

```text
Pi(Cone(LSYS(Branch(Klein(phi(KIN2(JIT1(LUT[SDF0](K)))))))))
```

The 1-bit parity/jitter result is a route and perturbation primitive. It is not an error-correction flag. `SDF0` is embedded in the LUT itself: every defined cell has relation value zero, and an address outside the finite program domain is undefined.

Functional notation executes from right to left. The shipped literal loop serializes that order as `SDF0 -> JIT1 -> KIN2 -> PHI -> KLEIN -> HINGE -> LSYS -> CONE -> PROJECT -> EMIT`; branch-indexed successors select a hinge route without skipping a stage.

TOMAGI does not contain learned weights, sampling, embeddings, confidence scores, stochastic state, damping, ECC, restoration forces, safe mode, or a hidden frame loop. A task becomes a TOMAGI task by compiling its literals, relations, branches, topology maps and output tokens into a finite `Cell48` graph. The core executes that graph and produces `State64` records; TOMAGI's first-party native SVG projection backend consumes the `EMIT` records and serializes their declared projection tokens and state geometry. The SVG serializer is a backend of the engine, not a new core opcode or a replacement for the fixed-width ABI. In a compiled domain, this whole path is a deterministic substitute for learned inference.

The first-party artifact path is explicit and replayable:

```text
source JSON -> compiled .tmg -> State64 trace/EMIT records -> SVG + manifest
```

## Delivered backends

- dependency-free Python reference runtime and compiler;
- portable C99 runtime and CLI;
- first-party native SVG projection backend with a trace and render manifest;
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

# Render the perpetual 64-emission TOMAGI engine portrait
PYTHONPATH=src/python python -m tomagi compile \
  examples/tomagi_engine_portrait.json examples/tomagi_engine_portrait.tmg
PYTHONPATH=src/python python -m tomagi render \
  examples/tomagi_engine_portrait.tmg examples/tomagi_engine_portrait.svg \
  --trace-output examples/tomagi_engine_portrait.trace.json \
  --manifest examples/tomagi_engine_portrait.manifest.json

# Run the source-derived 19 -> active bits -> three pulses -> triangle example
PYTHONPATH=src/python python -m tomagi nineteen

# Run the C99 backend on the same binary program
./build/tomagi-c examples/polar_loop.tmg
```

The shipped validation compares the final 16-word state from Python and C byte-semantically. In the recorded build, glslang compiled the GLSL shader; WGSL received structural checks because no WGSL compiler was configured; OpenCL was not syntax-checked because Clang was unavailable. No physical GPU dispatch was performed.

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

- `report/TOMAGI_1_0_Tom_Klootwijk.pdf` - formal substrate specification.
- `spec/TOMAGI_1_0_FORMAL_DEFINITION.md` - editable normative definition.
- `spec/*.json`, `spec/*.csv` - schema, symbols, operators, opcodes, key and ABI layouts, precedence and 322-row source crosswalk.
- `src/python/tomagi/` - Python oracle, compiler and CLI.
- `src/c/` - C99 evaluator.
- `src/gpu/` - GLSL, WGSL and OpenCL kernels.
- `examples/` - perpetual engine portrait, literal polar loop, exact-19 rule and source-derived feature example.
- `tests/` - executable conformance tests.
- `sources/` - source hash register and retained 211-mechanism knowledge catalog.
- `validation/` - machine-readable validation report and console logs.
- `checksums/SHA256SUMS.txt` - package checksums.

## Attribution

Tom Klootwijk; NL200678942; 10-07-1990. This is requester-supplied attribution and was not independently verified.
