# TOMAGI 1.0 Literal Genome and Byte Materialization Specification

Status: normative for the implementation shipped in this package  
Version: 1.0.0  
Materialization profile: `tomagi-emit-bytes-be-v1`

## 1. Normative language and scope

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as normative
requirements.

This specification defines a finite, content-addressed byte algebra, its lowering
to TOMAGI `Cell48` records, its serialization as a `.tmg` program, and the generic
materialization of the bytes selected by actual TOMAGI `EMIT` transitions.

The profile can represent every finite, non-empty byte string whose length is in
the interval defined in Section 13. It does so without assigning meaning to those
bytes. An artifact MAY be text, an image, an executable format, an archive, or any
other byte sequence; neither the genome evaluator nor the materializer SHALL infer
that meaning.

This profile does **not** claim:

- an unbounded store;
- acceptance of a zero-byte artifact;
- Turing completeness;
- unbounded recursion, iteration, or runtime;
- synthesis of bytes not literally committed by the definition graph; or
- acceptance when host memory, integer, filesystem, or process limits are
  exhausted.

The definition graph is finite and acyclic. Its only byte-producing operations are
`literal_utf8`, `literal_hex`, `concat`, and `repeat` with a finite non-negative
integer count. The lowered program is a finite, sequential chain that halts.

## 2. Notation and integer conventions

Let:

- `B*` be the set of finite byte strings;
- `||` denote byte concatenation;
- `len(x)` denote byte length;
- `u32(x) = x mod 2^32`;
- `BE4(x)` be the four-byte big-endian representation of `u32(x)`;
- `LE32(x)` be the four-byte little-endian representation of `u32(x)`;
- `SHA256(x)` be the 32-byte SHA-256 digest of byte string `x`;
- `hex(x)` be lowercase hexadecimal with two digits per byte; and
- `ceil4(n) = ceil(n / 4)` for positive `n`.

Array order and dependency order are significant unless a rule explicitly states
otherwise. JSON object member order is not significant to canonical hashing.

## 3. Authoritative 244-byte TOM1 seed literal

The requester-supplied seed file is
`sources/TOM_seed_genome_2026-09-01.txt`. Its entire content is the following ASCII
and UTF-8 byte string, with no byte-order mark and no trailing line terminator:

```text
TOM1[TopologicalOpenModular]|TomKlootwijk|1990-07-10|NL200678942|2026-09-01|LUTlogp^{Klein,SDF0@Def}(rho,theta,t->;phi,dt,d2,J,v,a,j1)>P1>L2_BST^b>ASweepCone(T,apex)>Pi[pyrSide,circle,sphere]>support>compatibility>guard>event>transition>lineage
```

Its exact properties are:

```text
byte length       244
raw SHA-256       d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5
first bytes       54 4f 4d 31 5b 54 6f 70    ("TOM1[Top")
last bytes        69 6f 6e 3e 6c 69 6e 65 61 67 65    ("ion>lineage")
```

The raw SHA-256 above is a hash of the 244 source bytes. It is distinct from the
definition `content_hash`, which commits to the complete canonical JSON definition
record containing those bytes and its metadata.

The compiler does not open or verify this external seed file while compiling a
genome document. A JSON definition that declares `source_sha256` or
`source_byte_length` commits to those declarations through its `content_hash`, but
the declarations are not independently checked against a filesystem path. The
shipped example has been checked and matches the values above.

## 4. JSON genome document

### 4.1 Document grammar

A genome-mode document SHALL be a JSON object satisfying
`spec/tomagi.schema.json` and the following profile grammar:

```text
GenomeDocument = {
  "tomagi_version": "1.0.0",
  "entry": DefinitionID,
  "definitions": [ Definition, ... ]
}
```

The `definitions` array MUST contain at least one item. `entry` MUST name a
definition in that array. A genome-mode document MUST omit `cells`; when `cells` is
present, `compile_document` selects the explicit-cell compiler path instead of the
definition-genome lowering path.

The schema permits additional top-level members such as `$schema` and `title`.
Additional members participate in no genome evaluation unless they occur inside a
definition record, but they remain part of the source document. The compiler does
not separately reject duplicate JSON member names: the current Python JSON parser
retains the last occurrence before compilation. Producers SHOULD avoid duplicate
member names because the earlier occurrences have no effect.

### 4.2 Definition grammar

Each definition SHALL contain at least:

```text
Definition = {
  "id": string,
  "kind": string,
  "domain": any JSON value,
  "codomain": any JSON value,
  "dependencies": [ string, ... ],
  "parameters": JSON object,
  "content_hash": "sha256:" + 64 lowercase hexadecimal digits
}
```

`evaluation_phase` MAY be an integer. `provenance` and other additional members
MAY be present. Every member other than the top-level `content_hash` is included in
the canonical definition hash, including descriptive metadata, dependency IDs,
`dependency_hashes`, provenance, and unrecognized additional members.

All definitions, including definitions unreachable from `entry`, MUST have unique
IDs, valid content hashes, resolvable non-duplicate dependencies, and an acyclic
dependency graph. Every definition reachable from `entry` MUST use one of these
four kinds:

```text
literal_utf8 | literal_hex | concat | repeat
```

The current schema allows other kind strings, and an unreachable definition with
another kind is not evaluated. Such a definition is still subject to the global
hash and dependency checks above. An unsupported reachable kind MUST be rejected.

### 4.3 Kind-specific parameters

The reachable kind-specific forms are:

```text
literal_utf8:
  dependencies = []
  parameters.text = JSON string

literal_hex:
  dependencies = []
  parameters.hex = an even-length string in [0-9A-Fa-f]*

concat:
  dependencies = [id_0, ..., id_(k-1)]       where k >= 0
  parameters.dependency_hashes = [h_0, ..., h_(k-1)]

repeat:
  dependencies = [id_0]
  parameters.dependency_hashes = [h_0]
  parameters.count = non-negative JSON integer, excluding boolean
```

The root definition identified by `entry` MUST additionally contain:

```json
"materialization_profile": "tomagi-emit-bytes-be-v1"
```

inside its `parameters` object. Other metadata such as `filename`, `media_type`,
`byte_length`, or `artifact_sha256` MAY appear there and is content-addressed, but
the evaluator and generic materializer SHALL NOT interpret or independently verify
it.

## 5. Canonical JSON and definition hashes

### 5.1 Canonical byte algorithm

For a parsed JSON value `v`, the implementation defines:

```text
CJSON(v) = UTF8(
  json.dumps(
    v,
    sort_keys = true,
    ensure_ascii = false,
    separators = (",", ":")
  )
)
```

This is the exact shipped Python algorithm. It is not a claim of equivalence to a
different canonical-JSON standard. Object keys are sorted by the Python JSON
encoder, non-ASCII characters are encoded directly as UTF-8, and no optional
spaces are emitted.

### 5.2 Content hash

For definition object `d`, let `body(d)` be a shallow copy of `d` with the
top-level member named `content_hash` removed. Nested members of the same name are
not removed. The required hash is:

```text
H(d) = "sha256:" || hex(SHA256(CJSON(body(d))))
```

A compiler MUST reject a definition if `content_hash` is absent or is not exactly
equal to `H(d)`. The hexadecimal digest emitted by the implementation is lowercase.

### 5.3 Transitive dependency commitment

For a `concat` or `repeat` definition `d` with ordered dependency IDs
`[id_0, ..., id_(k-1)]`, the evaluator computes:

```text
actual_hashes(d) = [ definitions[id_i].content_hash for i = 0..k-1 ]
```

`parameters.dependency_hashes` MUST be a list of strings and MUST equal
`actual_hashes(d)` in length, value, and order. Equality is exact string equality.
Because the dependency-hash list is itself inside `body(d)`, a verified root hash
transitively commits to each reachable dependency record.

The root content hash is a definition-record hash. It is not the SHA-256 of the
evaluated artifact bytes.

## 6. Dependency validation and order

Before genome evaluation, the compiler SHALL perform the following over the full
`definitions` array:

1. Record the input rank of every definition.
2. Reject duplicate IDs.
3. Reject a missing or invalid `content_hash`.
4. For every dependency list, reject an unknown ID or a repeated ID.
5. Construct directed edges from each dependency to its dependent definition.
6. Produce a stable topological order using this algorithm:

```text
indegree[id] = number of dependencies of id
ready = all indegree-zero IDs sorted by input rank
order = []

while ready is not empty:
    id = remove the lowest-input-rank item from ready
    append id to order
    for child of id, sorted by child input rank:
        indegree[child] -= 1
        if indegree[child] == 0:
            insert child into ready, retaining input-rank order

if len(order) != len(definitions):
    reject as a dependency cycle
```

The returned topological order validates that a finite order exists. It does not
reorder the dependency array used by `concat`; byte concatenation follows the
dependency order written in the selected definition.

The recursive evaluator also maintains an active-ID set and SHALL reject a cycle
encountered through its direct API, even if the compiler prevalidation was bypassed.

## 7. Exact byte-algebra evaluation

Let `E(id)` be the evaluated byte string of definition `id`. Results are memoized by
ID. Evaluation SHALL be exactly:

### 7.1 `literal_utf8`

```text
precondition: dependencies == []
precondition: parameters.text is a string
E(id) = UTF8(parameters.text)
```

UTF-8 encoding emits no byte-order mark. A string that the Python UTF-8 encoder
cannot encode MUST be rejected.

### 7.2 `literal_hex`

```text
precondition: dependencies == []
precondition: parameters.hex is a string
precondition: len(parameters.hex) is even
precondition: every character is in [0-9A-Fa-f]
E(id) = bytes represented by successive hexadecimal pairs
```

Uppercase and lowercase hexadecimal digits are equivalent. Whitespace is forbidden,
including whitespace that `bytes.fromhex` would otherwise accept. The empty string
evaluates to the empty byte string.

### 7.3 `concat`

After exact `dependency_hashes` validation:

```text
dependencies = [id_0, ..., id_(k-1)]
E(id) = E(id_0) || ... || E(id_(k-1))
```

For `k = 0`, the result is the empty byte string.

### 7.4 `repeat`

After exact `dependency_hashes` validation:

```text
dependencies = [child]
count is an integer, count >= 0, and count is not boolean
E(id) = E(child) repeated count times
```

For `count = 0`, the result is the empty byte string. A `repeat` node with zero or
more than one dependency MUST be rejected.

### 7.5 Root result

Evaluation returns the tuple:

```text
(entry ID, root content_hash, E(entry))
```

An empty intermediate value is valid. An empty final `E(entry)` MUST be rejected by
lowering because the current `.tmg` genome profile requires at least one `EMIT`
cell.

## 8. Required rejection behavior

Schema validation and compilation are separate in the shipped package.
`spec/tomagi.schema.json` defines document conformance, while `compile_file` parses
JSON and invokes `compile_document` without first invoking a JSON Schema validator.
A schema-invalid document might therefore reach an implementation error or, for an
unchecked descriptive field, compile successfully. Producers MUST validate against
the schema when schema conformance is required.

The compiler/evaluator itself SHALL reject the following detected conditions using
an exception or non-zero CLI termination rather than silently changing data:

- invalid JSON;
- `tomagi_version` other than `1.0.0`;
- absent genome definitions or an entry ID that does not exist;
- duplicate definition IDs;
- missing or mismatched definition `content_hash`;
- unknown or duplicate dependency IDs;
- a dependency cycle;
- a reachable unsupported genome kind;
- non-object `parameters` for a reachable definition;
- a reachable literal with dependencies;
- missing or non-string `text`/`hex` parameters in a reachable literal;
- odd-length, whitespace-containing, or non-hexadecimal data in a reachable
  `literal_hex`;
- absent, non-string, reordered, missing, extra, or incorrect
  `dependency_hashes` entries in a reachable `concat` or `repeat`;
- a reachable `repeat` with other than one dependency;
- a boolean, non-integer, or negative count in a reachable `repeat`;
- a root without the exact `tomagi-emit-bytes-be-v1` profile declaration;
- an entry `content_hash` that is not a valid `sha256:` digest;
- an empty root byte string;
- more than `0xffffffff` required cells;
- invalid `.tmg` magic, version, record sizes, reserved words, file length, opcode,
  entry, ordering, uniqueness, or successor range; and
- materialization of an execution trace containing no actual `EMIT` transition.

If `cells` is present, `compile_document` selects explicit-cell compilation instead
of genome lowering. That dispatch is not itself a rejection; the resulting document
is outside this literal-genome profile.

Resource exhaustion MAY prevent evaluation before the explicit cell-count check,
because the shipped evaluator constructs repeated byte strings in memory. It MUST
NOT substitute truncated or altered bytes and report success.

## 9. Byte-to-`Cell48` lowering

Let:

```text
B = E(entry)
L = len(B), with L >= 1
n = ceil(L / 4)
chunk_i = B[4i : min(4i + 4, L)]     for i = 0..n-1
```

The compiler MUST require `n <= 0xffffffff`. It SHALL construct exactly `n`
`Cell48` records. For each ordinal `i`, define:

```text
final_i     = (i == n - 1)
successor_i = i                  if final_i
              i + 1              otherwise
count_i     = len(chunk_i)       in 1..4
padded_i    = chunk_i || zero bytes until length 4
payload_i   = integer decoded from padded_i in big-endian order
flags_i     = ((count_i - 1) << 24) | (1 if final_i else 0)
```

The resulting cell fields SHALL be:

| `Cell48` field | Required value |
|---|---:|
| `key_hi` | `i >> 32` |
| `key_lo` | `i & 0xffffffff` |
| `opcode` | `14` (`EMIT`) |
| `flags` | `flags_i` |
| `arg0` | `0` |
| `arg1` | `0` |
| `arg2` | `0` |
| `arg3` | `0` |
| `next0` | `successor_i` |
| `next1` | `successor_i` |
| `payload` | `payload_i` |
| `aux` | `i & 0xffffffff` |

The current bound means actual generated indices are `0..0xfffffffe`, so
`key_hi` is zero for every permitted cell, although the formula above remains the
implemented field definition. Keys are strictly increasing and unique. Both
successors are equal, so the branch bit cannot change byte order. The terminal cell
self-loops but sets the existing `EMIT` halt flag before another transition occurs.

### 9.1 EMIT flag allocation

For this profile:

```text
bits 24..25 = count_i - 1
bit 0       = existing EMIT halt flag
```

All other lowering-generated flag bits are zero. Encoding byte length MUST preserve
bit 0. Decoding is:

```text
count(flags) = ((u32(flags) & 0x03000000) >> 24) + 1
```

### 9.2 Program fields

Let `R` be the 32 raw digest bytes represented by the verified root
`content_hash`. The lowered `Program` SHALL be:

```text
cells         = the n cells above
entry         = 0
seed          = little_endian_u32(R[0:4])
default_ticks = n
flags         = 0x314e4547
initial_state = State64 with:
                  lineage = little_endian_u32(R[4:8])
                  all other words = 0
```

The program flag value `0x314e4547` is stored little-endian in `.tmg` as the ASCII
bytes `47 45 4e 31`, namely `GEN1`.

## 10. `.tmg` serialization and endianness boundary

### 10.1 File structure

The `.tmg` file is exactly:

```text
64-byte fixed header
64-byte initial State64
n consecutive 48-byte Cell48 records
```

Its total length is:

```text
128 + 48n bytes
```

All integer words in the file are unsigned 32-bit little-endian storage words.
Signed state/argument fields are stored as their two's-complement `u32`
representatives.

The fixed header is:

| Offset | Size | Field | Genome value |
|---:|---:|---|---|
| 0 | 8 | magic | ASCII `TOMAGI1\0` |
| 8 | 4 | version | `0x00010000` |
| 12 | 4 | program flags | `0x314e4547` |
| 16 | 4 | cell count | `n` |
| 20 | 4 | entry | `0` |
| 24 | 4 | seed | root-derived seed |
| 28 | 4 | default ticks | `n` |
| 32 | 4 | cell size | `48` |
| 36 | 4 | state size | `64` |
| 40 | 24 | reserved | six zero words |
| 64 | 64 | initial state | root-derived `State64` |
| 128 | `48n` | cells | sequential emission cells |

The loader MUST require the exact magic, version, record sizes, zero reserved
words, and total file length. It MUST reject opcodes greater than 15. The `Program`
constructor MUST reject an empty cell table, an out-of-range entry, unsorted or
duplicate keys, or out-of-range successors.

### 10.2 Storage endianness is not payload endianness

Little-endian `.tmg` word storage and big-endian literal-payload interpretation are
separate layers.

For the literal bytes `54 4f 4d 41` (`TOMA`):

```text
numeric payload                    0x544f4d41
bytes stored in the .tmg cell      41 4d 4f 54
bytes materialized from payload    54 4f 4d 41
```

The loader first reconstructs the numeric `u32` from little-endian storage. The
materializer then computes `BE4(payload)` and takes its declared prefix. A
conforming implementation MUST NOT copy the four on-disk payload bytes directly
to the artifact.

## 11. Generic materialization algorithm

The host algorithm SHALL have no artifact-format, filename, media-type, token,
shape, layout, or palette semantics.

Given a loaded `Program P` and optional tick horizon `m`:

```text
(final_state, trace) = run(P, ticks=m, trace=true)
emissions = [r in trace where r.opcode == EMIT]

if emissions is empty:
    reject

artifact = empty byte string
chunk_counts = []

for r in emissions, in trace order:
    i = r.cell_before
    c = P.cells[i]
    if c.opcode != EMIT:
        reject
    k = ((u32(c.flags) & 0x03000000) >> 24) + 1
    artifact = artifact || BE4(c.payload)[0:k]
    append k to chunk_counts

return artifact, final_state, trace, emissions, manifest
```

The selection test MUST use the opcode of the actual executed trace record. It
MUST NOT use the latched `STATUS_EMIT` bit, because that status remains set after an
emission in programs that continue.

With no explicit `ticks`, the genome program executes `default_ticks = n`. Each
cell is executed once in ordinal order, and the final cell sets both `EMIT` and
`HALT` status. A horizon greater than `n` still produces only `n` records because
execution stops at `HALT`. A positive horizon less than `n` materializes the exact
prefix represented by the reached cells; it is not a full replay. A zero horizon
produces no `EMIT` record and is rejected by materialization.

During `EMIT`, the runtime writes the padded numeric payload to `State64.output`,
sets status bit 3 (`EMIT`), and, on the final cell, sets status bit 0 (`HALT`). The
artifact bytes are nevertheless read from the executed cell payload and declared
byte count, not inferred from a file extension or the final state.

## 12. Manifest, trace, and provenance

The materializer computes:

```text
program_sha256  = hex(SHA256(dumps(program)))
artifact_sha256 = hex(SHA256(materialized bytes))
```

Both are lowercase bare hexadecimal digests without a `sha256:` prefix. Its
manifest SHALL contain the following implementation fields:

```text
tomagi_version
materialization_profile
program_sha256
artifact_sha256
seed
requested_ticks
executed_ticks
emit_count
byte_count
chunk_byte_counts
emit_steps
final_lineage
final_output
final_state
```

`chunk_byte_counts[j]` is the decoded 1..4 count for emission `j`.
`emit_steps[j]` is the corresponding trace step. `final_state` is a JSON object
containing all sixteen `State64` fields:

```text
rho, theta, tick, phi,
vrho, vtheta, vtick, vphi,
orientation, sheet, branch, cell,
lineage, output, residual, status
```

The optional CLI trace sidecar contains:

```json
{
  "state": { "...all State64 fields...": 0 },
  "trace": [ "...actual runtime trace records..." ]
}
```

The generic materializer SHALL NOT copy `media_type`, `filename`, or other
artifact-specific root metadata into its behavior. Such fields remain source-level
provenance committed by the root definition hash. A complete audit chain SHOULD
retain:

1. the source JSON and all verified definition hashes;
2. the compiled `.tmg` and `program_sha256`;
3. the actual runtime trace;
4. the materialized bytes and `artifact_sha256`; and
5. the materialization manifest.

The root definition hash is not currently repeated in the runtime manifest. Only
its first eight digest bytes enter the program, as the derived seed and initial
lineage; the complete 32-byte root digest is not stored in `.tmg`. The exact compiled
program is committed by `program_sha256`. Auditors that require the complete
source-to-program proof MUST retain and recompile the source JSON.

## 13. Resource and size limits

Let `n` be the number of cells and `L` the artifact byte length. The hard profile
relations are:

```text
1 <= n <= 2^32 - 1
4(n - 1) + 1 <= L <= 4n
1 <= L <= 4(2^32 - 1) = 17,179,869,180 bytes
.tmg size = 128 + 48n
maximum format-level .tmg size = 206,158,430,288 bytes
```

These are representational bounds, not guaranteed practical capacities. The
shipped Python implementation is non-streaming:

- evaluated dependency values are memoized as Python `bytes`;
- `concat` and `repeat` allocate byte strings;
- the complete root result is split into an in-memory chunk list;
- all `Cell` objects are built in memory; and
- `dumps` constructs the complete binary file in memory.

Consequently, available memory and Python/filesystem limits will normally impose a
much lower ceiling. A large `repeat` may exhaust resources before the explicit
cell-count check. An implementation MUST NOT claim that the mathematical maximum
was successfully accepted unless it actually completed without truncation.

The number of JSON definitions and their metadata is also bounded by finite input
and available resources. This specification supplies no recursion-depth or memory
availability guarantee beyond the explicit format bounds.

## 14. Determinism and byte-replay theorem

### 14.1 Determinism conditions

For a fixed parsed JSON document, TOMAGI 1.0 implementation, tick horizon, and
adequate resources:

1. `CJSON` is deterministic.
2. Every verified definition hash is deterministic.
3. Dependency validation and the recursive byte algebra are deterministic.
4. `concat` preserves written dependency order.
5. `repeat` has a declared finite count.
6. Lowering assigns every field by the equations in Section 9.
7. `.tmg` serialization assigns every byte by Section 10.
8. Both successors of every non-terminal cell select the next ordinal.
9. Materialization reads only actual `EMIT` cells and uses an explicit count and
   byte order.

No randomness, clock, locale, filesystem content, media library, renderer, or
learned model participates in these operations.

### 14.2 Byte-replay theorem

Let `D` be a valid genome document, `r = D.entry`, and `B = E(r)` with
`1 <= len(B)` and `ceil4(len(B)) <= 0xffffffff`. Let:

```text
P = lower_definition_genome(D.definitions, r)
Q = dumps(P)
P' = loads(Q)
M = materialize_program(P') using the default tick horizon
```

Then:

```text
M.data = B
SHA256(M.data) = SHA256(B)
dumps(P') = Q
```

Proof: lowering partitions `B` into ordered chunks of one to four bytes. For each
chunk, `payload_i` is its right-zero-padded big-endian integer and the exact original
length is stored as `count_i - 1`. Little-endian `.tmg` serialization and loading
preserve the numeric payload and flag word. Execution begins at cell 0; equal
successors advance to cell `i+1`; the final cell halts. The materializer reconstructs
`BE4(payload_i)[0:count_i]`, which equals `chunk_i`. Ordered concatenation of all
chunks therefore equals `B`. Deterministic serialization gives `dumps(P') = Q`.

The theorem is a finite byte-replay statement. It is not a claim that the engine
derived the semantic design of `B`; all bytes are committed by the literal genome.

## 15. Exact shipped worked example

The source document is `examples/tomagi_engine_portrait.json`. Its entry is:

```text
artifact:tomagi-engine-portrait-svg
```

The reachable definitions evaluate as follows:

| Definition | Kind | Bytes | Content hash |
|---|---|---:|---|
| `literal:svg-prefix` | `literal_hex` | 357 | `sha256:4e483d4ce8e7eaa19aa92204db61c42dc1fe383c91ed543abecd62c116b857f0` |
| `literal:tom1-seed-genome` | `literal_utf8` | 244 | `sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d` |
| `literal:svg-body` | `literal_hex` | 4,238 | `sha256:78be8293f96a1fd796c7196001bd088f9b631fba528548c69aa744ff58086100` |
| `literal:emission-dash` | `literal_utf8` | 8 | `sha256:a7d2f13f5e952fc662567ec945f00970516cfa0da58031661a3d6460b9fec6fa` |
| `definition:repeat-64-emission-dashes` | `repeat(64)` | 512 | `sha256:205a6bce900bd2cd7b825c37807755c40f5a69ac9fd2269c7a6d116426151220` |
| `literal:svg-tail` | `literal_hex` | 252 | `sha256:4283e50c6b4a69cf011b53ed5b6b98c67dde8d7d19f31d4f2d1d8ac0e25eecb0` |
| `artifact:tomagi-engine-portrait-svg` | `concat` | 5,603 | `sha256:1f627995f36c67fca90b19d480cae74681abf724549f684e8f2bc455c276d0bd` |

The root concatenates, in order:

```text
svg-prefix
|| TOM1 seed genome
|| svg-body
|| repeat(emission-dash, 64)
|| svg-tail
```

Thus:

```text
357 + 244 + 4,238 + (8 * 64) + 252 = 5,603 bytes
artifact SHA-256 = ce661db8357b2df4fdecd5c3de2b4796d97ab081595d601892ea82a46b4ab32b
```

The root hash digest begins:

```text
1f 62 79 95 f3 6c 67 fc ...
```

Therefore lowering derives:

```text
program seed     little_u32(1f 62 79 95) = 2507760159 = 0x9579621f
initial lineage  little_u32(f3 6c 67 fc) = 4234636531 = 0xfc676cf3
cell count       ceil(5603 / 4)           = 1401
default ticks                               1401
program flags                               0x314e4547
.tmg byte size   128 + 48 * 1401          = 67,376
```

The first four artifact bytes are `3c 3f 78 6d` (`<?xm`), so cell 0 contains:

```text
key_hi=0, key_lo=0, opcode=14
flags=0x03000000, args=(0,0,0,0)
next0=1, next1=1
payload=0x3c3f786d, aux=0
```

The last three artifact bytes are `67 3e 0a` (`g>` followed by newline), so final
cell 1400 (`0x578`) contains:

```text
key_hi=0, key_lo=0x00000578, opcode=14
flags=0x02000001, args=(0,0,0,0)
next0=1400, next1=1400
payload=0x673e0a00, aux=1400
```

The exact shipped replay results are:

```text
source JSON SHA-256  e10a112ebc05474a62b6855e9763ea1fa4e4f15f690e226e029f46709cda4c99
.tmg SHA-256         36081cf017b77373eff3c1eef4e3640d760740217604efb6ab194c5575588dc1
artifact SHA-256     ce661db8357b2df4fdecd5c3de2b4796d97ab081595d601892ea82a46b4ab32b
emissions            1401
executed ticks       1401
final lineage        143154426 = 0x08885cfa
final output         1732119040 = 0x673e0a00
final status         9 = EMIT | HALT
```

The artifact is an SVG because the source genome literally contains SVG bytes.
The materializer does not contain SVG behavior and would perform the identical
operation for any other byte format.

## 16. Reproducible CLI procedure

From the package root, the following commands compile and replay the worked example
without modifying the shipped example artifacts:

```bash
python -m pip install -e .
python -c "from pathlib import Path; Path('build').mkdir(exist_ok=True)"
python -m tomagi compile \
  examples/tomagi_engine_portrait.json \
  build/tomagi_engine_portrait.tmg
python -m tomagi materialize \
  build/tomagi_engine_portrait.tmg \
  build/tomagi_engine_portrait.svg \
  --trace-output build/tomagi_engine_portrait.trace.json \
  --manifest build/tomagi_engine_portrait.manifest.json
python -c "from pathlib import Path; import hashlib; [print(p, len(Path(p).read_bytes()), hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in ('build/tomagi_engine_portrait.tmg','build/tomagi_engine_portrait.svg')]"
```

The final command MUST report:

```text
build/tomagi_engine_portrait.tmg 67376 36081cf017b77373eff3c1eef4e3640d760740217604efb6ab194c5575588dc1
build/tomagi_engine_portrait.svg 5603 ce661db8357b2df4fdecd5c3de2b4796d97ab081595d601892ea82a46b4ab32b
```

For an arbitrary non-empty byte string, a producer MAY create a root
`literal_hex` definition containing the complete hexadecimal encoding, add the
required materialization profile to its parameters, compute its canonical
definition hash, compile it, and invoke the same `materialize` command. More complex
genomes MAY factor repeated or shared byte strings through verified `concat` and
`repeat` nodes; this factoring changes definition and program provenance but MUST
NOT change the replayed bytes unless the evaluated root changes.
