# TOMAGI 1.0 Formal Engine Definition

**TOMAGI: Topological Operator Machine for Analytic Geometric Inference**  
Version 1.0.0 - 1 September 2026

Requester attribution: **Tom Klootwijk; NL200678942; 10-07-1990**. Supplied by the requester and not independently verified.

## 1. Decision

TOMAGI is the deterministic state-and-operator engine. Its executable authority is a finite package of typed definitions, fixed-width LUT cells, an initial state and an explicitly ordered transition relation, not a trained model or an opaque rendered scene. Its generic host tooling can also evaluate content-addressed record/byte definitions and materialize literal bytes emitted by a compiled program. The host adds no artifact-format, geometry or dimensional semantics.

The literal source chain is retained as the normative macro:

```text
Pi(Cone(LSYS(Branch(Klein(phi(KIN2(JIT1(LUT[SDF0](K)))))))))
```

Functional notation composes from right to left. A binary TOMAGI program serializes the same composition as one `Cell48` transition per tick. The stored order is authoritative and is never re-sorted by operator name.

Consequently, the normative execution order of the macro is `LUT[SDF0]`, `JIT1`, `KIN2`, lower-case `phi`, `Klein`, `Branch`, `LSYS`, `Cone`, `Pi`. A compiled branch may select different cells for a stage, but every successor route claiming this literal macro must preserve that order and may not bypass `phi`, `Klein`, `LSYS`, `Cone` or projection.

The key interpretation is literal:

- `LUT[SDF0]` means that every address belonging to the compiled LUT domain is a zero-level relation;
- `JIT1` derives one deterministic bit from seed, key, tick and cell salt;
- that bit selects a signed perturbation and the branch successor;
- `KIN2` applies discrete second-order kinematics packed in the cell;
- lower-case `phi`, timeline and Klein wrapping transform the same state;
- branch-indexed radix and hinge cells route the graph without reordering stages;
- the L-system transforms the routed state;
- cone, sphere and overlap relations then convert state into branch bits;
- projection and emission produce symbolic output while lineage preserves replay identity;
- `authenticated_trace`, `select_records`, `project_fields` and `format_records` can derive representation bytes from an authenticated `State64` replay;
- the compiler lowers those bytes to ordinary `EMIT` cells, while the generic `materialize` host only replays their declared big-endian byte chunks.

Thus the first-party engine path is:

```text
definition-driven orbit -> compiled .tmg -> authenticated State64 trace
  -> authenticated_trace -> select_records -> project_fields -> format_records
  -> compiled EMIT-byte program -> generic byte replay -> SVG | OBJ | CSV.
```

Definition evaluation occurs at compile time. Materialization does not dynamically project fields or interpret a file type: it executes the lowered byte program and concatenates the bytes selected by `EMIT`. In particular, the shipped 4D result is a CSV table of four integer state fields, not a claim of direct four-dimensional visual rendering.

TOMAGI 1.0 deliberately excludes the corrective layers introduced in some previous drafts: no jitter guard, ECC, damping, restoration force, confidence threshold, safe mode or kill-criteria operator is present in the execution core.

## 2. Source synthesis

The supplied project corpus contributes the following directly usable pieces:

1. The 1-bit/lower-case-phi dialogue provides the literal `SDF0`-inside-LUT ordering, parity-conditioned branch, packed kinematics, analytic cone, projection, Klein and binary L-system chain.
2. SCLP 3.6.2 provides the typed symbol separation, finite cone and sphere relations, exact log-polar chart and kinematics, deterministic bit generation, reflective Klein map, radix refinement, 20/18/14/12 key and distinct Morton schedule.
3. UGTS-KC 3.6 provides content-addressed definitions, explicit dependency order, non-commutative hinges, deterministic traces and the active-bit/pulse example.
4. The Ben Burger dialogue contributes the exact zero-based offset/ordinal distinction, the split-lower-case-phi/double-D hinge image and the overlap lens as a shared domain.
5. The 19 dialogue contributes `19 = 10011`, active positions `{0,1,4}`, three declared Dutch segments `ne|gen|tien`, the chosen three-pulse triangle and the log-polar/Klein/Delta-Delta terminology.
6. The chronological synthesis contributes the query-first interpretation: local cone/sphere supports, directly queryable relations, explicit transitions and lineage, with projection downstream.
7. The supplied ZIP contributes the 211-entry normalized knowledge catalog and a GPU-native fixed-width implementation precedent.
8. The exact 244-byte `sources/TOM_seed_genome_2026-09-01.txt` literal (SHA-256 `d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5`) contributes the root content of the executable definition DAGs.

The machine-readable `source_crosswalk.json` contains 322 rows mapping every cataloged or direct document motif, including the literal TOM1 seed genome, to the condensed TOMAGI namespace.

## 3. Typed program object

A TOMAGI program is

```text
P = (D, C, i0, seed, m0, q0, F)
```

where:

- `D` is a content-addressed definition registry;
- `C = (c0,...,cN-1)` is a strictly key-sorted finite array of `Cell48` values;
- `i0` is the entry cell;
- `seed` is the deterministic 32-bit source of the one-bit sequence;
- `m0` is the default query horizon in transitions;
- `q0` is the initial `State64`;
- `F` is a program flag word reserved for versioned profiles.

A definition record is

```text
d = (id, kind, A, B, parameters, dependencies, phase, provenance, hash)
```

with content address

```text
hash = SHA256(canonical_JSON(d without hash)).
```

Dependencies must resolve and admit a finite topological order. This is a language property: without it, the meaning of a composed literal definition would be ambiguous.

A `tomagi_cell_operation` definition owns the complete executable cell fields: opcode, flags, four arguments, two successors, payload and auxiliary word. A source cell may therefore contain only `id`, `key` and `definition_ref`. The compiler resolves and verifies the definition and lowers those fields to `Cell48`; any duplicated executable field in the cell must match the referenced definition exactly. `tomagi_state_orbit.json` uses this definition-driven form for all ten runtime cells.

## 4. State64

The hot state is sixteen 32-bit words:

```text
q_n = (
  rho, theta, X, phi,
  v_rho, v_theta, v_X, v_phi,
  orientation, sheet, branch, cell,
  lineage, output, residual, status
).
```

The first eight words and `residual` are interpreted as two's-complement signed integers. The remaining topology and output words are unsigned. The periodic coordinate domains are:

```text
rho key component   in Z/(2^20 Z)
theta               in Z/(2^18 Z)
X                   in Z/(2^14 Z)
phi                 in Z/(2^12 Z)
orientation         in Z/2Z
branch              in Z/2Z
```

`rho` itself may temporarily lie outside its canonical range so that a Klein wrap can observe the number and parity of radial crossings. Key construction always uses its modulo-`2^20` representative.

Lower-case `phi` is the periodic hoop/hinge/phase coordinate. Capital `Phi` is reserved for an optional golden-ratio constant in a compile-time profile. They never alias.

## 5. Canonical 64-bit key

For normalized quantized fields

```text
q_rho   : 20 bits
q_theta : 18 bits
q_X     : 14 bits
q_phi   : 12 bits
```

the contiguous key is

```text
K = (q_rho << 44) | (q_theta << 26) | (q_X << 12) | q_phi.
```

The exact address capacity is `2^64`. The profile may decode `rho` to `[-20,0]`, `theta` and `phi` to `[0,2*pi)`, and `X` to zero-based modular ticks, but the runtime hot path operates on integers only.

The distinct Morton key consumes source bits in MSB round-robin order:

```text
rho19, theta17, X13, phi11,
rho18, theta16, X12, phi10, ...
```

until all 64 source bits are consumed. The complete schedule is supplied in JSON and CSV. For the SCLP reference tuple `(949111,0,1920,227)`:

```text
contiguous = 0xe7b77000007800e3
Morton     = 0x88823bb88099128b
```

Both decode exactly to the same tuple.

## 6. Literal SDF0 LUT

Let `D_K` be the finite set of keys present in the compiled cell table. TOMAGI defines

```text
Z_D(K) = 0       when K is in D_K
Z_D(K) = bottom  when K is not in D_K.
```

`bottom` is undefined/non-member, not a positive or negative distance. Therefore every definable cell or bit is literally on the zero-level set, while the complement does not pretend to be a metric field.

The `SDF0` opcode applies the first case because execution already holds a defined cell. It performs:

```text
residual <- 0
status.ZERO <- 1
branch <- 1
```

This operator is not a boundary contraction, guard or restoration force. It is the membership/value relation that makes data and operator definition coincide inside the LUT.

## 7. Deterministic one-bit jitter

For state key `(K_hi,K_lo)`, timeline tick `X`, program seed `s` and cell auxiliary `a`, define:

```text
h = mix32(s xor K_hi xor rotl32(K_lo,13) xor X xor a)
j = popcount(h) mod 2
sigma = 2*j - 1, so sigma is -1 or +1.
```

`mix32` is exactly:

```text
x ^= x >> 16
x *= 0x7feb352d
x ^= x >> 15
x *= 0x846ca68b
x ^= x >> 16
```

with every multiplication and shift performed in `u32` arithmetic.

`JIT1(field,A)` then applies

```text
field <- field + sigma*A
branch <- j.
```

The bit is deterministic for the complete input tuple. It is called jitter because it can produce a bipolar local displacement; it is called parity because `j` is the parity of the mixed word. It does not diagnose corruption and it does not trigger an automatically safer mode.

## 8. Discrete kinematic calculus

The four coordinate components are collected as

```text
p_n = (rho_n, theta_n, X_n, phi_n)
v_n = (v_rho,n, v_theta,n, v_X,n, v_phi,n).
```

A `KIN2` cell contains acceleration/change-of-change vector

```text
a_i = (arg0,arg1,arg2,arg3).
```

The exact update is symplectic-Euler order in modular integer arithmetic:

```text
v_(n+1) = wrap32(v_n + a_i)
p_(n+1) = wrap32(p_n + v_(n+1)).
```

After the opcode, `theta`, `X` and lower-case `phi` are normalized to their declared periodic domains. `arg3` is therefore the runtime form of `Delta^2 phi`: the second discrete change of the lower-case phase coordinate.

For host-side geometric compilation, SCLP's continuous log-polar formulas remain available:

```text
rho = ln(r/r0), theta = atan2(y,x), r = r0*exp(rho)
v = r*(rho_dot*e_r + theta_dot*e_theta)
a = r*((rho_ddot + rho_dot^2 - theta_dot^2)*e_r
      + (theta_ddot + 2*rho_dot*theta_dot)*e_theta).
```

Those real equations compile parameters into the integer state/cell profile. They are not reevaluated with floating point in the hot backend-neutral transition.

## 9. Timeline and lower-case phi

`X` is a zero-based modular timeline coordinate. The ordinal shown to a human is `X+1`; that display transformation never changes the stored offset.

`TIME(delta)` computes mathematical floor winding:

```text
raw = X + delta
w   = floor(raw / 2^14)
X'  = raw - w*2^14
branch = w mod 2.
```

Nonzero winding is mixed into lineage so repeated phases remain distinguishable.

`PHI(delta)` performs the analogous update modulo `2^12`. Flags may expose either wrap parity or the upper/lower half-circle as the branch. An odd wrap may optionally flip orientation. This gives the lower-case phi symbol a literal, typed role as a periodic hinge rather than overloading it with the capital golden ratio.

## 10. Topological wrapping

TOMAGI retains two separate source maps.

### 10.1 Reflective Klein map

For radial wrap count

```text
w = floor(rho / 2^20),   rho' = rho - w*2^20,
```

an odd wrap applies

```text
theta'       = 2^17 - theta   (mod 2^18)
phi'         = -phi           (mod 2^12)
orientation' = orientation xor 1
sheet'       = sheet xor flip_sheet
branch       = 1.
```

Even wrap parity preserves theta, phi, orientation and sheet and yields branch zero. The angular reflection is orientation reversing.

### 10.2 Source half-turn bundle

When the `SOURCE_HALF_TURN` flag is set, the theta equation becomes

```text
theta' = theta + 2^17  (mod 2^18),
```

while lower-case phi and orientation still flip. This is preserved as a distinct bundle twist; it is not silently identified with the reflective Klein quotient.

## 11. Relations and supports

### 11.1 Packed cone relation

A cone/support cell stores radial interval `[rho_min,rho_max]`, angular center `theta0` and half-width `alpha_q`. Let `delta_N` be the shortest cyclic difference. The signed integer relation is

```text
r_C = max(
  rho_min - rho_bar,
  rho_bar - rho_max,
  abs(delta_(2^18)(theta_bar,theta0)) - abs(alpha_q)
).
```

`branch = 1` exactly when `r_C <= 0`.

This is the runtime packed relation corresponding to the cone/support part of the source chain. A host compiler may derive it from the finite right-circular cone with slant length `T_c`, half-angle `alpha`, height `T_c*cos(alpha)` and radius `T_c*sin(alpha)`, or from a swept-cone support envelope.

### 11.2 Packed sphere/shell relation

A spherical support is stored as radial center `rho0`, radial half-width `d_rho`, lower-case-phi center `phi0` and phase half-width `d_phi`:

```text
r_S = max(
  abs(rho_bar-rho0)-abs(d_rho),
  abs(delta_(2^12)(phi_bar,phi0))-abs(d_phi)
).
```

A negative `d_phi` disables the phase term and yields a pure radial shell. `branch = 1` exactly when `r_S <= 0`.

### 11.3 Circle, side-view pyramid and sphere

The source's circle, side-view pyramid and sphere are retained as typed projections or support profiles:

- a side-view pyramid token is emitted from the triangular/conic relation;
- a circle token is the axial or radial-shell projection;
- a sphere token is the spherical-support projection.

`PROJECT` and `EMIT` are core operations: they make the selected symbolic projection and replay state authoritative. File representations are separate definition programs. The supplied 2D definition selects emitted states and maps `(theta,rho)` through declared integer affine coefficients before formatting an SVG polyline; the 3D definition similarly maps `(rho,theta,phi)` to OBJ vertices and declares one ordered open line. Neither mapping is built into an opcode or the materialization host, and neither implies a general raster, scene or game-rendering contract.

### 11.4 Overlap lens

For two predicates or supports `A` and `B`, the slight overlap is

```text
L = A intersect B.
```

The lens can be compiled as a conjunction, shared-domain tag or connector hinge. No physical energy, fusion or interference meaning is implied unless a separate rule encodes it.

## 12. Binary routing, radix and hinge

`RADIX(k)` reads bit `k` of the canonical 64-bit key, with low-word bits numbered 0-31 and high-word bits 32-63. Repeated bit tests form a radix-trie decision path.

Each cell stores two successor indices:

```text
cell_(n+1) = next0  when branch=0
cell_(n+1) = next1  when branch=1.
```

A TOMAGI hinge is the compiled form of

```text
H = (state, map0, map1, invariant metadata).
```

`map0` is identity. When `branch=1`, `map1` adds the four cell arguments to `(rho,theta,X,phi)` and may flip orientation and sheet. Multiple hinges are applied in stored order. They are not assumed to commute.

This single interface covers a continuous or quantized geometric hinge, a parity-selected route, a connector node such as Dutch `en`, and the split-lower-case-phi/double-D fold when those meanings are declared in the definition record. The literal polar loop uses distinct `next0` and `next1` hinge cells, so routing remains branch-indexed while both routes execute the hinge stage.

## 13. L-system

`LSYS(turn,shift)` implements the condensed branch-node transform:

```text
chirality = +1 when orientation=0, else -1
turn_sign = +1 when branch=1, else -1
phi' = phi + chirality*turn_sign*turn  (mod 2^12)
v' = trunc_toward_zero(v / 2^shift).
```

This is the runtime one-step form of

```text
F(T) -> F(T/2) [ +/- phi F(T/2) ].
```

The finite cell graph specifies how many such steps are taken for a particular query. There is no separate runtime recursion guard or safety governor.

## 14. Output, lineage and trace

`PROJECT(payload)` sets a symbolic output token and continues. `EMIT(payload)` sets the token and the emitted status; its low flag bit may terminate the program. `HALT` terminates without changing the token. Each transition on which `EMIT` executes is an emission record; the trace retains the complete resulting `State64` fields.

Every transition updates the replay lineage checksum:

```text
lineage' = mix32(
  lineage xor payload xor aux xor K_hi xor rotl32(K_lo,7)
  xor branch xor cell_index
).
```

Lineage is a compact deterministic replay witness. It is not a cryptographic ownership claim. A trace records the ordered cell index, opcode, branch, key, relation residual, topology bits, output, lineage and status after every transition.

The representation-definition pipeline is generic and compile-time:

1. `authenticated_trace` reads only declared relative source, program and trace paths; verifies all three hashes and the declared source-definition anchors; proves `Compile(source) == program`; replays the declared horizon; and requires the replay trace and final state to equal the authenticated JSON.
2. `select_records` applies declared integer predicates and slicing. The supplied representations select opcode `EMIT`, yielding 64 records.
3. `project_fields` applies declared rational affine transforms with integer floor or truncation semantics. It has no named geometry or dimensional vocabulary.
4. `format_records` applies safe UTF-8 prefix, record-template, separator and suffix definitions.
5. The compiler evaluates the root byte definition and lowers the result into sequential `EMIT` cells. Each cell owns one to four literal big-endian bytes under `tomagi-emit-bytes-be-v1`.
6. `materialize_program` executes that lowered program, selects the executed `EMIT` cells and concatenates their declared chunks. It does not read the authenticated trace or dynamically perform selection, field projection or formatting.

The reference artifact workflow is therefore a single engine pipeline with a strict interface:

```text
orbit definitions --compile/run--> authenticated State64 trace
  --authenticated_trace/select_records/project_fields/format_records-->
representation bytes --compile-time lowering--> EMIT-only .tmg
  --generic materialize--> byte-identical SVG | OBJ | CSV + manifest.
```

## 15. Execution relation and determinism

Let `Step_P(q)` be the complete opcode, normalization, lineage and successor procedure. For a requested transition count `m`:

```text
Exec(P,q0,m) = q_k
```

where `k` is the first index not greater than `m` for which `HALT` is set, or `k=m` when no earlier halt occurs.

### Determinism theorem

For any two conforming backends `A` and `B`, if they receive byte-identical `.tmg` program data, identical initial state, identical seed and identical requested transition count, then

```text
Exec_A(P,q0,m) = Exec_B(P,q0,m)
```

word for word, provided both implement the specified `u32`, `i32`, floor-division, truncating-division and periodic-normalization semantics.

The supplied Python and C99 implementations define this relation. The current Python polar-loop reference ends in the following state; the recorded Windows validation did not execute the available Linux C binary, so it does not claim a current cross-backend comparison:

```text
rho=8, theta=39, X=1, phi=2117
v=(8,-3,0,-2)
orientation=0, sheet=1, branch=0, cell=12
output=0x50595241 (PYRA)
lineage=1625236203
residual=65497, status=0x0000000f.
```

The definition-driven state orbit provides the cyclic witness. Its ten source cells retain only `id`, `key` and `definition_ref`; content-addressed `tomagi_cell_operation` definitions own all runtime fields and are transitively rooted in the exact TOM1 seed definition `sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d`. It executes 640 transitions as 64 ten-stage cycles, with exactly 64 occurrences of every opcode in `SDF0`, `JIT1`, `KIN2`, `PHI`, `KLEIN`, `HINGE`, `LSYS`, `CONE`, `PROJECT`, `EMIT` order. It does not halt. All 64 emitted four-coordinate tuples are unique and the replay ends with:

```text
rho=680006, theta=218400, X=3720, phi=2388
orientation=0, sheet=0, branch=1, cell=0
output=0x4f524254 (ORBT)
lineage=1437167731, status=0x0000001a.
```

The authoritative orbit SHA-256 values are source `f456d0da681ae03ddb40cdc1c4566411b25a24e48d8ab279a9bc94d75a6f9cbd`, 608-byte program `349e51a5a402b3295d653ad08f00b55d465ffab7e943fb437d196af948487e3e`, and 252,941-byte/640-record LF trace `aa060ad1cdc25d7e95e2cdc36e1338ede0cced27f4791989b0cc287d01b9a14f`.

## 16. Deterministic substitution for AI

A domain is TOMAGI-compilable when it provides:

1. a finite typed input encoding into `State64` or literal definitions;
2. finite facts, equations, relations, topology maps or decision rules;
3. a compiler from those rules to sorted `Cell48` values;
4. finite output tokens or relation records;
5. a declared query horizon or an emitted/halting leaf.

For such a domain, inference is

```text
answer = Exec(Compile(definitions,rules), Encode(input), m).output.
```

This substitutes explicit operator execution for learned prediction. It supports deterministic classification, finite-state planning, procedural generation, geometric/topological queries, rule engines, signal routing and compiled symbolic knowledge.

It does not invent facts absent from the definition graph. This is not a restriction injected into the runtime; it is the meaning of deterministic compilation. A learned model generalizes statistically from weights. TOMAGI evaluates exactly the relations that have been made literal.

The `exact19_rule.json` example compiles equality with the quantized relation into a three-cell program and emits `19` for input `rho=19` and `0` for `rho=18`. The `nineteen` helper separately demonstrates the source-derived representation chain:

```text
19 -> binary 10011 -> active positions {0,1,4} -> count 3
negentien -> ne|gen|tien -> pulse count 3
3 declared pulses -> chosen triangle projection.
```

The value remains 19 and the binary word remains 10011.

## 17. Implementation mapping

### 17.1 Python oracle

`src/python/tomagi` supplies canonical hashing, JSON compilation, binary serialization, the exact step function, trace evaluation, authenticated record-definition evaluation, byte lowering/materialization and the source-derived knowledge example. It has no runtime dependency outside the Python standard library.

### 17.2 C99 CPU

`src/c/tomagi.c` loads `.tmg` bytes without structure-packing assumptions and implements the same operations with explicit little-endian reads and two's-complement conversion. `tomagi_cli.c` is a minimal host executable.

### 17.3 Generic definition evaluation and byte materialization

The compiler recognizes representation-agnostic definition kinds `authenticated_trace`, `select_records`, `project_fields` and `format_records`. Their evaluated root is a byte string that is lowered at compile time to an `EMIT`-only `.tmg`. The `tomagi materialize` command later executes that program and concatenates the emitted byte chunks. Its manifest records the program/artifact hashes, byte/chunk counts, executed/emission steps and final state; the host has no format-specific branch.

The finalized representation evidence is:

- 2D SVG — root `sha256:532ba6cfc7b0aa42becafa4d4468107a2d3f5185ba7613cbbd5f762d6d5d97ad`; source `4e9510a9ee659b4895e9521f39f5ed5f12a4c2ea8bbe3959dd5611fb72bb64fc`; 444-cell/21,440-byte program `f29dbc09bc85637584db4fec314d904dbecd672b78e51ae1d981c118439a8c95`; 1,774-byte artifact `fcaa3bd926529fe92f382f896cff042708111c10d652ac8c539386f5340f161c`. It contains 64 unique `(theta,rho)` points after the declared affine map (`x/y`: 64/63 distinct).
- 3D OBJ — root `sha256:e52578589731c7621a136ce606bb003e6a7e883edc59e3a4ca9c3c1889ec864d`; source `09ae1f5061a15b4d6ad004acb5b8b4cf93faed03994c7b2eac98db5761ceb7c5`; 339-cell/16,400-byte program `793446ac860d1f7abf2984e9f98e894741ee8644bcd09efa2bdda91d183ad8d1`; 1,355-byte artifact `4b356aa10acbd751b19b333db68b87e1f3c6231a7264099efb07349e555e0511`. It contains 64 unique vertices and one ordered open line `1..64` (`x/y/z`: 64/64/60 distinct).
- 4D CSV — root `sha256:faeb0eb44a2f43e38de571a23201ae6bfa1068623c959a8ef309fc2d75735a08`; source `ec129e19109db9481a7fe43f47931d4311426f8e287677511ae27b8352109b2c`; 371-cell/17,936-byte program `37cb6a789d24ed9e18a81c87412ad3a7f428e8ad178721857762f5eb939ee5fb`; 1,483-byte artifact `d1ac54e5aa0a575c021692a646e6b211acaab63ca8657740f723d06480f853df`. Its 64 rows preserve raw `(rho,theta,tick,phi)` fields; it is not a direct visual rendering of four-dimensional space.

Only templates, framing, labels, style, separators and affine coefficients are authored in the representation definitions. Every numeric record comes from the authenticated orbit trace; no completed artifact, coordinate row, vertex list or topology-index list is stored as a literal.

Canonical commands:

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

### 17.4 GPU

The GLSL, WGSL and OpenCL kernels use the same three-buffer ABI:

```text
binding/input 0: State64[] read-write
binding/input 1: Cell48[] read-only
parameters: state_count, cell_count, seed, reserved.
```

One invocation executes one transition for one state. Repeated dispatches advance the graph. The kernels use 32-bit integer arithmetic, bit count, shifts and buffer reads only; no tensor core, vendor-specific intrinsic or floating-point geometry instruction is required.

## 18. Normative no-failsafe profile

The following earlier-draft mechanisms are absent from the TOMAGI 1.0 transition algebra:

```text
jitter interval guard
confidence or event-margin threshold
ECC/Hamming correction
boundary restoration force
damping or emergency contraction
safe-mode state
watchdog oscillation detector
VRAM reserve/safety ring
source-claim kill criteria.
```

A program may explicitly encode any domain rule it needs, but none of these is silently injected by the runtime. Parity is allowed to branch either way. `SDF0` always returns zero for a defined cell. The compiler's structural checks only ensure that the bytecode has a unique parse and declared successors.

## 19. Conformance

A TOMAGI 1.0 package conforms when:

- the `.tmg` magic, version and record sizes are exact;
- the cell table is strictly sorted by unique canonical keys;
- every opcode lies in `0..15` and every successor is in range;
- definition hashes verify and references resolve;
- key pack/unpack matches the supplied reference vectors;
- the Python reference tests pass;
- another backend matches the Python final state on the conformance program.

The current recorded package validation ran 62 Python tests successfully and verified all authenticated 2D/3D/4D definition DAGs, recompilations, trace replays and artifact bytes. Six example JSON documents validate under the supplied Draft 2020-12 schema. Python/C comparisons were not run on the Windows host because the available C evaluator is a Linux ELF executable. GLSL and WGSL received structural source checks because no compiler was configured; OpenCL syntax checking was not run because Clang was unavailable. No physical GPU dispatch is claimed.

## 20. Final definition

**TOMAGI 1.0 is a finite, content-addressed, deterministic operator machine in which a 20/18/14/12 log-polar key selects a literal SDF-zero LUT cell; a parity-of-mixed-word one-bit operator produces signed jitter and a branch; integer second-order kinematics advances log-radius, angle, zero-based time and lower-case phi; reflective Klein or half-turn maps transport orientation and sheet; branch-indexed radix/hinge routing precedes L-system grammar and cone/sphere/overlap classification; projection and emission then return replayable `State64` answers with lineage. Branch-indexed successors serialize non-commutative composition. The same 64-byte state and 48-byte cell definitions map to the supplied Python, C, GLSL, WGSL and OpenCL implementations. Generic content-addressed definitions can authenticate a trace, select and affinely map integer fields, format records and compile those bytes to `EMIT` cells; the host evaluates those definitions, while materialization only replays the compiled bytes and assigns no SVG, OBJ, CSV or dimensional meaning.**
