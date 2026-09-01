# TOMAGI 1.0 Literal Genome, Authenticated Record, and Byte Replay Specification

Status: normative for the implementation shipped in this package  
Version: 1.0.0  
Byte materialization profile: `tomagi-emit-bytes-be-v1`

## 1. Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, and **MAY** are normative requirements.

This specification describes the observable behavior of the current
`canonical.py`, `compiler.py`, `genome.py`, `format.py`, `project.py`, runtime,
schema, seed, and shipped state-representation examples. It does not assign
behavior that those files do not implement.

JSON Schema validation and compilation are separate operations. A conforming
source SHOULD satisfy `spec/tomagi.schema.json`. The `compile` CLI parses JSON and
calls the compiler; it does not automatically invoke a JSON Schema validator.

## 2. Scope and causal architecture

TOMAGI is the engine. Host code in this profile MAY perform only generic mechanics:

- JSON parsing;
- canonical hashing and dependency validation;
- definition evaluation;
- relative-path confinement and byte authentication;
- deterministic lowering to `Cell48`;
- TOMAGI execution and trace capture; and
- format-agnostic byte materialization.

Artifact and domain choices SHALL be literal, hashed definition data. In the
shipped state representations, SVG markup, OBJ records, CSV headers, field choices,
affine coefficients, templates, separators, and topology text all reside in the
definition documents. The host evaluator contains none of that vocabulary.

The implemented causal chain is:

```text
exact TOM1 seed definition
  -> hashed tomagi_cell_operation definitions
  -> definition-referenced runtime cells
  -> Compile(source) == authenticated runtime .tmg
  -> TOMAGI replay == authenticated trace and final State64
  -> authenticated_trace record table
  -> select_records
  -> project_fields
  -> format_records and, where declared, concat/repeat
  -> byte-string definition root
  -> sequential EMIT Cell48 lowering
  -> TOMAGI execution
  -> generic byte materialization
  -> byte-identical artifact
```

This profile is finite. It can replay any non-empty finite byte string within the
limits in Section 16. It does not claim unbounded storage, a zero-byte lowered
artifact, Turing completeness, semantic inference of missing artifact content, or
direct visualization of every numerical dimension.

## 3. Notation and value domains

Let:

- `B*` denote finite byte strings;
- `||` denote byte concatenation;
- `u32(x) = x mod 2^32`;
- `BE4(x)` denote the four-byte big-endian encoding of `u32(x)`;
- `LE32(x)` denote the four-byte little-endian encoding of `u32(x)`;
- `SHA256(x)` denote the 32-byte SHA-256 digest of bytes `x`;
- `hex(x)` denote lowercase hexadecimal with two digits per byte; and
- `floor(x)` denote mathematical floor.

The definition evaluator has exactly two runtime value types:

```text
ByteString  = bytes
Record      = finite mapping string -> integer, excluding boolean
RecordTable = ordered immutable sequence of Record
GenomeValue = ByteString | RecordTable
```

Operator input types are enforced. A byte operator MUST reject a record-table
dependency, and a record operator MUST reject a byte-string dependency. Record
order and the insertion order of projected fields are deterministic.

## 4. Authoritative TOM1 seed

The authoritative root seed file is
`sources/TOM_seed_genome_2026-09-01.txt`. Its complete content is the following
244-byte ASCII/UTF-8 string, with no byte-order mark and no trailing line ending:

```text
TOM1[TopologicalOpenModular]|TomKlootwijk|1990-07-10|NL200678942|2026-09-01|LUTlogp^{Klein,SDF0@Def}(rho,theta,t->;phi,dt,d2,J,v,a,j1)>P1>L2_BST^b>ASweepCone(T,apex)>Pi[pyrSide,circle,sphere]>support>compatibility>guard>event>transition>lineage
```

Its raw properties are:

```text
byte length   244
SHA-256       d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5
```

The shared seed definition in the shipped examples has content hash:

```text
sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d
```

The raw file hash and definition content hash are distinct. The former hashes only
the 244 seed bytes. The latter hashes the complete canonical definition record,
excluding only its top-level `content_hash` member.

The compiler does not independently open the seed file merely because a literal
definition declares `source_file` or `source_sha256`. Those fields are
content-addressed metadata. In the shipped examples, tests separately prove that
the literal text and both declared source hashes equal the exact seed file.

## 5. JSON documents and definitions

### 5.1 Common document requirements

A TOMAGI document is a JSON object with:

```text
tomagi_version = "1.0.0"
entry          = string
definitions    = array of Definition, when definitions are used
cells          = array of CellSource, when an explicit runtime graph is used
```

The schema requires `tomagi_version` and `entry`, and requires at least `cells` or
non-empty `definitions`. Additional top-level members are allowed. The compiler
rejects a version other than `1.0.0`.

When `cells` is absent, `compile_document` selects definition-genome byte lowering.
When `cells` is present, it selects explicit runtime-cell compilation. A present but
empty `cells` array is rejected.

The Python JSON parser retains the last occurrence of a duplicate object member.
Producers SHOULD NOT use duplicate member names.

### 5.2 Definition record

Every definition SHALL contain:

```text
id             string
kind           string
domain         any JSON value
codomain       any JSON value
dependencies   ordered array of strings
parameters     JSON value; an object for every executable kind in this profile
content_hash   "sha256:" followed by 64 lowercase hexadecimal digits
```

`evaluation_phase`, `provenance`, and additional members MAY be present. They are
included in the content hash. Descriptive members have no execution effect unless
the relevant operator explicitly reads them.

### 5.3 Canonical JSON and content hash

For parsed JSON value `v`, canonical bytes are exactly:

```text
CJSON(v) = UTF8(json.dumps(
    v,
    sort_keys=True,
    ensure_ascii=False,
    separators=(",", ":")
))
```

This is the shipped Python algorithm; it is not an assertion of equivalence to a
different canonical-JSON standard.

For definition `d`, `body(d)` is a shallow copy with the top-level
`content_hash` member removed. Nested members with that name remain. The required
hash is:

```text
H(d) = "sha256:" || hex(SHA256(CJSON(body(d))))
```

Every definition supplied to the compiler or evaluator MUST have a `content_hash`
exactly equal to `H(d)`. Missing or mismatched hashes are rejected.

## 6. Dependency validation, order, and hash commitments

### 6.1 Stable dependency order

The compiler validates the complete definition array before cell compilation or
genome lowering:

1. IDs MUST be unique.
2. Every dependency ID MUST exist.
3. An ID MUST NOT occur twice in one dependency list.
4. The complete graph MUST be acyclic.
5. Definition hashes MUST verify.

The stable topological order is constructed as follows:

```text
input_rank[id] = definition array index
indegree[id]   = number of dependencies
ready          = indegree-zero IDs sorted by input_rank
order          = []

while ready is not empty:
    id = pop lowest-input-rank ready item
    append id to order
    for child of id, sorted by child input_rank:
        indegree[child] -= 1
        if indegree[child] == 0:
            insert child into ready and retain input-rank order

if len(order) != number of definitions:
    reject cycle
```

Topological validation does not reorder a definition's dependency array. Operators
such as `concat` consume dependencies in their written order.

### 6.2 Optional and enforced `dependency_hashes`

For definition `d` with dependencies `[id_0, ..., id_(k-1)]`, define:

```text
actual_dependency_hashes(d) =
  [definitions[id_0].content_hash, ..., definitions[id_(k-1)].content_hash]
```

The implementation has three precise cases:

1. During general compiler validation, `parameters.dependency_hashes` is optional.
   If the member is present in an object-valued `parameters`, it MUST equal
   `actual_dependency_hashes(d)` exactly in length, value, and order.
2. The evaluator requires `dependency_hashes` for `concat`, `repeat`,
   `authenticated_trace`, `select_records`, `project_fields`, and
   `format_records`. It MUST be a list of strings and MUST equal the actual list.
3. `tomagi_cell_operation` is consumed by the explicit-cell compiler rather than
   the genome evaluator. The literal causal profile defined here REQUIRES each such
   operation definition to carry the exact dependency-hash list. The compiler then
   enforces it under case 1.

Leaf `literal_utf8` and `literal_hex` definitions have no dependencies and do not
require a `dependency_hashes` member.

Because each declared hash list is itself included in `H(d)`, a derived
definition's verified content hash commits to the ordered current hashes of its
dependencies.

## 7. Definition-driven runtime cells

### 7.1 Causal cell-source profile

In this profile, an explicit runtime cell source SHALL contain exactly:

```json
{
  "id": "cell-id",
  "key": "0x...",
  "definition_ref": "operation-definition-id"
}
```

`definition_ref` MUST resolve to a definition whose kind is
`tomagi_cell_operation`. That definition's `parameters` MUST contain every
executable operation field:

```text
opcode   opcode name or integer
flags    integer
args     exactly four integers
next     exactly two cell IDs
payload  integer
aux      integer
```

The cell source owns only identity, key, and the reference. Opcode, flags,
arguments, successors, payload, and auxiliary word SHALL be sourced from the hashed
definition. This makes definitions executable compiler inputs rather than ignored
metadata.

The current schema/compiler retain backward compatibility:

- a raw cell without `definition_ref` may provide `op`, `args`, `next`, and
  optional flags/payload/aux; and
- a definition-referenced cell may redundantly provide operation fields if their
  normalized values exactly match the referenced definition.

Those two forms are supported but are outside the causal cell-source profile above.
A redundant field that differs after normalization MUST be rejected. The shipped
orbit cells contain only `id`, `key`, and `definition_ref`.

### 7.2 Resolution and lowering

Keys are decoded either from a hexadecimal `u64` or from a
`rho/theta/tick/phi` object. Prepared cells are sorted by unsigned canonical key.
Cell IDs MUST be unique. Successor IDs from `parameters.next` are resolved to
indices after sorting; unknown successors are rejected.

For a `tomagi_cell_operation`, compilation performs:

```text
Cell48.key_hi/key_lo = decoded cell-source key
Cell48.opcode        = normalized parameters.opcode
Cell48.flags         = integer(parameters.flags)
Cell48.arg0..arg3    = integer(parameters.args[0..3])
Cell48.next0/next1   = sorted-cell indices named by parameters.next[0..1]
Cell48.payload       = integer(parameters.payload)
Cell48.aux           = integer(parameters.aux)
```

The top-level `entry` names the entry cell. Top-level `seed`, `default_ticks`,
`flags`, and `initial_state` supply the corresponding program fields. The compiler
sets `initial_state.cell` to the sorted entry index.

Changing any executable operation parameter and recomputing all affected hashes
MUST change the compiled program whenever that parameter changes a lowered word.
Changing a cell's mirrored field without changing the referenced definition MUST
be rejected if the values differ.

## 8. Definition evaluator and generic value typing

The evaluator recognizes these kinds:

```text
literal_utf8
literal_hex
concat
repeat
authenticated_trace
select_records
project_fields
format_records
```

`tomagi_cell_operation` is not a genome value operator; it is interpreted only by
the explicit-cell compiler in Section 7.

Evaluation is recursive, memoized by definition ID, and guarded by an active-ID
set. An unknown entry, unknown dependency, cycle, unsupported reachable kind, or
non-object parameters value is rejected.

`evaluate_definition_genome` requires the selected root to evaluate to bytes.
`evaluate_definition_records` requires it to evaluate to a record table. A type
mismatch is rejected.

## 9. Byte-algebra operators

### 9.1 `literal_utf8`

Requirements:

- dependencies MUST be empty;
- `parameters.text` MUST be a string.

Semantics:

```text
Eval(d) = UTF8(parameters.text)
```

No byte-order mark is added. A string rejected by Python's UTF-8 encoder is
rejected.

### 9.2 `literal_hex`

Requirements:

- dependencies MUST be empty;
- `parameters.hex` MUST be a string;
- its character count MUST be even;
- it MUST contain no whitespace; and
- all characters MUST form hexadecimal byte pairs.

Semantics:

```text
Eval(d) = bytes.fromhex(parameters.hex)
```

Uppercase and lowercase digits are equivalent. The empty hex string evaluates to
empty bytes.

### 9.3 `concat`

After exact dependency-hash validation, every dependency MUST evaluate to bytes.
For ordered dependencies `[d_0, ..., d_(k-1)]`:

```text
Eval(d) = Eval(d_0) || ... || Eval(d_(k-1))
```

Zero dependencies yield empty bytes.

### 9.4 `repeat`

`repeat` MUST have exactly one dependency. Its dependency MUST evaluate to bytes.
`parameters.count` MUST be an integer other than boolean and MUST be non-negative.
After dependency-hash validation:

```text
Eval(d) = Eval(dependency) repeated parameters.count times
```

Count zero yields empty bytes.

## 10. `authenticated_trace`

### 10.1 Parameters and path confinement

An authenticated trace definition requires:

```text
trace_path, trace_sha256
program_path, program_sha256
source_path, source_sha256
source_definition_hashes
ticks
dependency_hashes
```

`trace_key` defaults to `"trace"`; `state_key` defaults to `"state"`. If supplied,
both MUST be strings.

Evaluation requires a document base directory. `compile_file` supplies the parent
directory of the definition JSON. A direct `compile_document` caller MUST pass
`base_dir` when an authenticated path is reached.

For every authenticated file:

1. The path MUST be a non-empty string.
2. The declared digest MUST be exactly 64 lowercase hexadecimal digits without a
   `sha256:` prefix.
3. The path MUST be relative, not absolute.
4. Let `root = resolve(base_dir)` and
   `candidate = resolve(root / relative_path)`. `candidate` MUST remain beneath
   `root` under `Path.relative_to`; `..`, a symlink, or any other resolution that
   escapes is rejected.
5. The file MUST be readable.
6. `hex(SHA256(file_bytes))` MUST equal the declared digest.

The authenticated source, program, and trace are parsed or replayed from the
captured bytes just hashed. If the authenticated source itself contains reachable
file-authenticating definitions, compiling it MAY perform their separately
confined and authenticated reads.

### 10.2 Source-definition anchors

`source_definition_hashes` MUST be a list of strings. For this operator it MUST be
exactly equal to `dependency_hashes`, including order. Each listed value MUST occur
as a `content_hash` in the authenticated source document's `definitions` array.

The evaluator explicitly evaluates each local dependency, thereby checking its
content hash and its own dependency chain. The authenticated source document is
then compiled, which verifies all of its definition hashes and dependencies.

The anchor list is a membership commitment, not a substitute for the raw source
hash. The raw source SHA-256 authenticates the complete source file.

### 10.3 Compile and replay authentication

The authenticated source and trace bytes MUST parse as JSON; the source MUST be an
object, and the trace document MUST be an object with an array at `trace_key`.
`ticks` MUST be a non-negative integer other than boolean.

The following equalities are REQUIRED:

```text
Compile(source_document, base_dir=source_path.parent), serialized with dumps,
    == authenticated program bytes

run(loads(program_bytes), ticks=ticks, trace=True).trace
    == trace_document[trace_key]

StateDict(run(...).final_state)
    == trace_document[state_key]
```

The program bytes are thus required to be exactly `Compile(source)`, not merely a
program with a matching declared hash. The stored trace and final state are
required to be exact runtime replay, not independently authored records.

After those equalities pass, each trace record MUST be an object whose field names
are strings and values are integers other than booleans. The result is an ordered
`RecordTable` preserving every integer field.

Any file hash mismatch, missing anchor, compile mismatch, replay mismatch, final
state mismatch, invalid record, missing base directory, or path escape is rejected.

## 11. Record-table operators

### 11.1 `select_records`

`select_records` requires exactly one record-table dependency and an exact
dependency-hash list. `parameters.predicates` defaults to `[]` and MUST be an array.

Each predicate SHALL be:

```text
field     string naming an existing record field
operator  one of eq, ne, lt, le, gt, ge
value     integer other than boolean
```

For each source record in order, predicates are visited in written order and
combined by short-circuiting logical AND. A reached predicate whose field is
missing, value is invalid, object shape is invalid, or operator is unsupported is
rejected. Once a predicate is false, later predicates are not inspected for that
record. Consequently, predicates never reached by any record—including every
predicate when the input table is empty—are not independently validated. Records
that pass retain source order.

After predicate filtering, the implementation applies:

```text
selected[start : stop : stride]
```

where `start` defaults to `0` and MUST be a non-negative non-boolean integer;
`stop` defaults to null and MUST be null or a non-negative non-boolean integer; and
`stride` defaults to `1` and MUST be a positive non-boolean integer.

### 11.2 `project_fields`

`project_fields` requires exactly one record-table dependency and a non-empty
`parameters.fields` array. Each field descriptor requires:

```text
name         output field name matching ^[A-Za-z_][A-Za-z0-9_]*$
source       field name present in every input record
numerator    integer other than boolean, default 1
denominator  positive integer other than boolean, default 1
offset       integer other than boolean, default 0
rounding     "floor" or "trunc", default "floor"
```

Output names MUST be unique within a record. For source integer `s`:

```text
p = s * numerator

q = floor(p / denominator)                                  if rounding == floor
q = sign(p) * floor(abs(p) / denominator), with sign(0)=0   if rounding == trunc

output[name] = q + offset
```

All arithmetic uses Python integers and is not narrowed to `i32` during definition
evaluation. Record order is preserved. Only declared output fields are retained.
Field descriptors are inspected inside the record loop; with an empty input table,
the implementation checks only that `fields` is a non-empty array and returns an
empty table without inspecting its descriptors.

### 11.3 `format_records`

`format_records` requires exactly one record-table dependency. Parameters are:

```text
encoding         defaults to "utf-8" and MUST equal "utf-8"
prefix           string, default ""
record_template  REQUIRED string
separator        string, default ""
suffix           string, default ""
index_start      integer other than boolean, default 0
```

For records in order, the evaluator copies the record, rejects an existing field
named `index`, adds `index` from `enumerate(records, start=index_start)`, and formats
one row.

For each input record, templates use `string.Formatter`. Each replacement field MUST match
`^[A-Za-z_][A-Za-z0-9_]*$` and MUST exist in the row. Attribute access, item access,
conversions, and non-empty format specifications are rejected. Literal escaped
braces remain supported by the formatter. A malformed template is rejected when a
row causes it to be parsed. With an empty table, no template parse occurs; after
the unconditional parameter type checks, the result is `UTF8(prefix || suffix)`.

The result is exactly:

```text
UTF8(prefix || separator.join(formatted_rows) || suffix)
```

No artifact type is inferred from the text.

## 12. Definition-genome byte lowering

When a document has no `cells`, its `entry` definition MUST evaluate to bytes and
its object-valued parameters MUST contain:

```text
materialization_profile = "tomagi-emit-bytes-be-v1"
```

Let root bytes be `B`, `L = len(B)`, and root content hash digest bytes be `R`.
`L` MUST be positive. Define:

```text
n       = ceil(L / 4)
chunk_i = B[4i : min(4i + 4, L)]       for i = 0..n-1
```

The compiler MUST reject `n > 0xffffffff`. For every chunk:

```text
final_i     = (i == n - 1)
successor_i = i if final_i else i + 1
count_i     = len(chunk_i)
padded_i    = chunk_i right-padded with zero bytes to length four
payload_i   = big_endian_integer(padded_i)
flags_i     = ((count_i - 1) << 24) | (1 if final_i else 0)
```

The lowered cell is:

| Field | Value |
|---|---:|
| `key_hi` | `i >> 32` |
| `key_lo` | `i & 0xffffffff` |
| `opcode` | `14` (`EMIT`) |
| `flags` | `flags_i` |
| `arg0..arg3` | all zero |
| `next0` | `successor_i` |
| `next1` | `successor_i` |
| `payload` | `payload_i` |
| `aux` | `i & 0xffffffff` |

The generated program is:

```text
cells             = ordered cells above
entry             = 0
seed              = little_endian_u32(R[0:4])
default_ticks     = n
initial lineage   = little_endian_u32(R[4:8])
all other initial State64 fields = 0
program flags     = 0x314e4547
```

The program flag is stored little-endian as ASCII `GEN1`. Both successors are
equal, so runtime branch state cannot change byte order. The final cell self-loops
and sets the existing `EMIT` halt bit.

## 13. `.tmg` binary format and byte packing

The `.tmg` file is:

```text
64-byte header
64-byte initial State64
n * 48-byte Cell48
```

All integer words in `.tmg` storage are little-endian. The header fields are:

| Offset | Size | Meaning |
|---:|---:|---|
| 0 | 8 | ASCII `TOMAGI1\0` |
| 8 | 4 | version `0x00010000` |
| 12 | 4 | program flags |
| 16 | 4 | cell count |
| 20 | 4 | entry index |
| 24 | 4 | seed |
| 28 | 4 | default ticks |
| 32 | 4 | cell size, exactly 48 |
| 36 | 4 | state size, exactly 64 |
| 40 | 24 | six reserved zero words |
| 64 | 64 | initial `State64` |
| 128 | `48n` | cells |

The sixteen `State64` words are stored in this order:

```text
rho, theta, tick, phi, vrho, vtheta, vtick, vphi,
orientation, sheet, branch, cell, lineage, output, residual, status
```

The twelve words of each `Cell48` are stored in this order:

```text
key_hi, key_lo, opcode, flags, arg0, arg1, arg2, arg3,
next0, next1, payload, aux
```

The first eight state words and `residual`, and the four argument words, are
interpreted as signed two's-complement `i32`; the remaining words are interpreted
as unsigned `u32` by the loader.

The loader rejects short files, incorrect magic/version/record sizes, nonzero
reserved words, incorrect total length, or opcode values above 15. `Program`
construction rejects an empty cell table, out-of-range entry, unsorted or duplicate
keys, and out-of-range successors.

### 13.1 Little-endian storage versus big-endian literal bytes

`.tmg` word endianness does not define artifact byte order. Under
`tomagi-emit-bytes-be-v1`:

```text
count(flags) = ((u32(flags) & 0x03000000) >> 24) + 1
chunk        = BE4(payload)[0:count(flags)]
```

Flag bits 24..25 encode `count - 1`. Bit 0 retains the existing `EMIT` halt
meaning. The count encoder MUST preserve other flag bits.

For literal bytes `54 4f 4d 41`:

```text
payload numeric value       0x544f4d41
payload bytes in .tmg       41 4d 4f 54
materialized bytes          54 4f 4d 41
```

A materializer MUST reconstruct the numeric word from `.tmg`, then apply the
big-endian profile. It MUST NOT copy the four on-disk payload bytes directly.

## 14. Generic materialization and manifest

Given program `P` and optional tick horizon `m`:

```text
(final_state, trace) = run(P, ticks=m, trace=True)
emissions = [record for record in trace if record.opcode == EMIT]

if emissions is empty:
    reject

artifact = b""
chunk_byte_counts = []

for record in emissions in trace order:
    cell = P.cells[record.cell_before]
    require cell.opcode == EMIT
    count = ((u32(cell.flags) & 0x03000000) >> 24) + 1
    artifact = artifact || BE4(cell.payload)[0:count]
    append count to chunk_byte_counts
```

Selection MUST use each actual trace opcode. It MUST NOT use the latched
`STATUS_EMIT` bit, which can remain set after an emission in a continuing program.

At the default horizon, a byte-lowered genome executes all generated cells and the
final cell halts. A shorter positive horizon produces only the reached byte prefix;
it is not a complete replay. Zero ticks produces no emissions and is rejected.

The generic materializer computes and records:

```text
program_sha256  = hex(SHA256(dumps(program)))
artifact_sha256 = hex(SHA256(artifact))
tomagi_version
materialization_profile
seed
requested_ticks
executed_ticks
emit_count
byte_count
chunk_byte_counts
emit_steps
final_lineage
final_output
final_state (all sixteen State64 fields)
```

It does not read a filename extension or interpret media type, geometry, topology,
dimension, color, or record semantics.

When the CLI writes a trace sidecar or manifest, its bytes are exactly:

```text
UTF8(json.dumps(value, indent=2, sort_keys=True) || "\n")
```

The CLI passes those UTF-8 bytes directly to `write_bytes`, so the terminator and
all pretty-print line endings are LF (`0x0a`) on every host. This pretty sidecar
serialization is distinct from the compact `CJSON` used for definition hashes.

## 15. Required rejection behavior

The applicable compiler/evaluator/materializer rejects:

- malformed JSON;
- wrong TOMAGI version;
- missing entry or definitions required by the selected mode;
- duplicate IDs, unknown dependencies, duplicate dependencies, or cycles;
- missing or mismatched definition hashes;
- a present but incorrect dependency-hash list;
- a derived genome operator without its required exact dependency-hash list;
- a causal-profile cell whose `id`, `key`, or `tomagi_cell_operation` reference
  is absent or invalid;
- an operation definition missing opcode, flags, four args, two successors,
  payload, or aux;
- conflicting redundant operation fields;
- invalid opcode, integer, key, entry, or successor;
- unsupported reachable evaluator kind or wrong `GenomeValue` type;
- the operator-specific invalid inputs in Sections 9 through 11;
- absent base directory for authenticated files;
- absolute or escaping authenticated paths;
- malformed or mismatched lowercase SHA-256 declarations;
- unreadable authenticated files;
- missing source-definition anchors;
- source compilation unequal to authenticated program bytes;
- replay unequal to authenticated trace or final state;
- trace fields not mapping strings to non-boolean integers;
- a byte-lowering root without the exact materialization profile;
- an empty final byte string;
- too many output cells;
- an invalid `.tmg`; or
- a materialization run with no actual `EMIT` transition.

A conforming causal-profile source contains only `id`, `key`, and
`definition_ref` in each cell. As the compatibility exception specified in Section
7, the shipped compiler also accepts redundant operation fields when every such
field exactly matches the referenced operation definition; it rejects a conflict.
The raw-cell compatibility path likewise remains available for pre-existing
programs.

## 16. Limits and security properties

### 16.1 Hard byte-lowering bounds

For artifact length `L` and generated cell count `n`:

```text
1 <= n <= 2^32 - 1
4(n - 1) + 1 <= L <= 4n
1 <= L <= 17,179,869,180 bytes
.tmg size = 128 + 48n
maximum format-level .tmg size = 206,158,430,288 bytes
```

These are representational bounds, not guaranteed practical capacity.

### 16.2 Practical resource limits

The Python implementation is non-streaming. It retains definition values, record
tables, traces, formatted strings, output bytes, cells, and serialized programs in
memory. `repeat`, large authenticated traces, large tick horizons, and formatting
may exhaust memory or CPU before a hard format bound is reached. Python recursion
depth also limits very deep dependency chains. Resource failure MUST NOT be reported
as successful truncated replay.

An authenticated program may be non-halting under its own graph, but
`authenticated_trace.ticks` is a required finite non-negative integer. Replay work
is therefore bounded by the declared horizon and available resources.

### 16.3 Security boundary

- Relative-path resolution confines authenticated reads to the definition
  document's resolved directory, including symlink resolution.
- Files are hashed before their authenticated contents are used.
- SHA-256 provides content integrity, not signer identity, authorization, or proof
  of authorship.
- `Compile(source) == program` prevents substitution of a different runtime binary
  under a merely self-consistent trace.
- Replay equality prevents substitution of independently authored trace records or
  final state.
- Source-definition anchors bind declared literal definitions into the
  representation DAG; the raw source hash binds the complete source file.
- Formatting permits only direct safe field names and forbids attribute/index
  traversal, conversions, and format specifications.
- No network retrieval is performed.
- Artifact bytes remain untrusted data to downstream consumers. Byte-identical
  materialization does not make an executable, markup document, or model safe to
  open.

## 17. Determinism and replay theorem

Let:

- `S` be an authenticated TOMAGI runtime source document;
- `P = Compile(S, base_dir=dir(S))` and `PB = dumps(P)`;
- `T` and `Q` be the trace and final state produced by `run(P, ticks=m)`;
- `D` be a valid representation definition document whose
  `authenticated_trace` verifies the exact bytes of `S`, `PB`, and a trace document
  containing `T` and `Q`;
- `B = Eval(D.entry, base_dir=dir(D))` be the resulting non-empty byte string;
- `G = lower_definition_genome(D.definitions, D.entry, base_dir=dir(D))`;
- `GB = dumps(G)`; and
- `M = materialize_program(loads(GB))` at its default horizon.

Then, assuming adequate resources:

```text
dumps(Compile(S)) = PB
run(loads(PB), ticks=m).trace = T
run(loads(PB), ticks=m).final_state = Q
M.data = B
SHA256(M.data) = SHA256(B)
dumps(loads(GB)) = GB
```

Proof sketch:

1. Canonical definition hashing and ordered dependency validation fix the executable
   inputs.
2. Definition-referenced cells source every operation word from verified operation
   definitions; key sorting and successor resolution are deterministic.
3. `authenticated_trace` requires byte equality between compilation and program,
   then exact replay equality for trace and final state.
4. Selection is an ordered deterministic filter and slice.
5. Projection is declared integer affine arithmetic with explicit rounding.
6. Formatting uses declared literal templates and canonical UTF-8.
7. Byte lowering partitions `B` into ordered chunks, stores each padded chunk as a
   big-endian numeric payload, and stores its exact length in flags.
8. Equal successors execute every generated `EMIT` cell in order; the final cell
   halts.
9. Materialization recovers every original chunk with `BE4(payload)[0:count]`.

Thus the artifact bytes are a replay of the literal definition graph. The theorem
does not claim that TOMAGI invented the semantics encoded by those definitions.

## 18. Shared authenticated State64 orbit

The three shipped representations use one authenticated runtime source:

```text
source   examples/tomagi_state_orbit.json
program  examples/tomagi_state_orbit.tmg
trace    examples/tomagi_state_orbit.trace.json
```

### 18.1 Exact file commitments

| File | Bytes | SHA-256 |
|---|---:|---|
| `tomagi_state_orbit.json` | 11,625 | `f456d0da681ae03ddb40cdc1c4566411b25a24e48d8ab279a9bc94d75a6f9cbd` |
| `tomagi_state_orbit.tmg` | 608 | `349e51a5a402b3295d653ad08f00b55d465ffab7e943fb437d196af948487e3e` |
| `tomagi_state_orbit.trace.json` | 252,941 | `aa060ad1cdc25d7e95e2cdc36e1338ede0cced27f4791989b0cc287d01b9a14f` |

The source has ten causal cells. Every cell contains exactly `id`, `key`, and
`definition_ref`. The compiled keys are `0..9`; the opcodes are:

```text
SDF0, JIT1, KIN2, PHI, KLEIN, HINGE, LSYS, CONE, PROJECT, EMIT
```

The operation-definition commitments are:

| Definition | Content hash |
|---|---|
| `definition:orbit-sdf0` | `sha256:8b0f9bb5cd815caf3246c51873b40c0ced0659b0217425d1dc0c43b4053f2c1f` |
| `definition:orbit-jit1` | `sha256:f866b9c78ec2475a2b3a6edf248ea82d60dbca3f70b593ff015d80b01e387273` |
| `definition:orbit-kin2` | `sha256:fe72c1b9d4e2903a6d801efec7c2e7746062a95e3d8602ea2c30207fd2b75050` |
| `definition:orbit-phi` | `sha256:ba56cb66942ae2b24cd1d978d90c551dfa0c5d52e3a12467ad1f6885fb883f63` |
| `definition:orbit-klein` | `sha256:684e8d3441dd13d68aa065b9b3bad1b9f272c812781ea7a28f1c8692a85b6109` |
| `definition:orbit-hinge` | `sha256:785d6b167cbff2ca2d1dbd7115c014d5ca92121c16e3b424c6dd1400017d9cb3` |
| `definition:orbit-lsys` | `sha256:578a1b18d04146549a629559a70a2f1b2766e3668fba26c146e66bb7947f8e1b` |
| `definition:orbit-cone` | `sha256:b325663a6455b37763a6b387c882cc06655179468a2b11ad31744a197b0df1ee` |
| `definition:orbit-project` | `sha256:aa9ed6dbb43b20105e9ac7d9726ff59834bbf235b239b0316acf0dde7c35be21` |
| `definition:orbit-emit` | `sha256:1f8c7fca09946453bd72a2a642dc04440232f2dafff45afed30104c74cbfcee2` |

Every operation is transitively dependent on the exact seed definition. The source
declares program seed `0xd1417a31`, the first 32 raw seed-digest bits in big-endian
notation, and initial lineage `0x36772c0c`, the next 32 bits. These values are
literal top-level source values with provenance; the general compiler does not
derive them automatically from the seed file.

### 18.2 Exact replay

The non-halting ten-cell cycle runs for 640 ticks and yields 640 trace records and
64 `EMIT` records. The stored program is byte-identical to fresh compilation. The
parsed stored trace and final-state objects are JSON-value-equal to fresh replay.

The first and last emission coordinates are:

```text
first  (rho, theta, tick, phi) = (201197, 20580, 1011, 498)
last   (rho, theta, tick, phi) = (680006, 218400, 3720, 2388)
```

The final state is:

```text
rho=680006, theta=218400, tick=3720, phi=2388
vrho=13800, vtheta=5620, vtick=74, vphi=69
orientation=0, sheet=0, branch=1, cell=0
lineage=1437167731 (0x55a97073)
output=1330790996 (0x4f524254, "ORBT")
residual=-43743, status=26
```

No cell is `HALT`; both `EMIT` successors return to the entry cell.

## 19. Exact 2D representation

Source: `examples/tomagi_state_2d.json`

Entry: `orbit2d:svg-record-format`

The definition chain and hashes are:

| Definition | Kind | Content hash |
|---|---|---|
| seed | `literal_utf8` | `sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d` |
| `orbit2d:authenticated-trace` | `authenticated_trace` | `sha256:401a6213da224e707215b53368d51e27aa284842ec4a793390eca23aeea2ed7f` |
| `orbit2d:emit-samples` | `select_records` | `sha256:ca27cedf9053e4dd3de945b3615b1175b7d094d804da7293408cf00c76cc8233` |
| `orbit2d:theta-rho-canvas` | `project_fields` | `sha256:02e081f45c2c151cf5b21a5b0d2ad7c2d391ef4653e298c699a6650357b1b27f` |
| `orbit2d:svg-record-format` | `format_records` | `sha256:532ba6cfc7b0aa42becafa4d4468107a2d3f5185ba7613cbbd5f762d6d5d97ad` |

The selector retains exactly the 64 records whose opcode is `EMIT`. The declared
projection is:

```text
x = floor(theta * 1040 / 262144) + 80
y = floor(rho * -580 / 1048576) + 650
```

The definition-owned formatter emits an SVG polyline. The first point is
`(161,538)` and the last is `(946,273)`. There are 64 distinct x values and 63
distinct y values.

Exact artifacts:

| Boundary | Bytes/count | SHA-256 |
|---|---:|---|
| source JSON | 6,956 bytes | `4e9510a9ee659b4895e9521f39f5ed5f12a4c2ea8bbe3959dd5611fb72bb64fc` |
| compiled `.tmg` | 21,440 bytes / 444 cells | `f29dbc09bc85637584db4fec314d904dbecd672b78e51ae1d981c118439a8c95` |
| materialized SVG | 1,774 bytes / 64 points | `fcaa3bd926529fe92f382f896cff042708111c10d652ac8c539386f5340f161c` |
| manifest JSON | 7,793 bytes | `0c5e2f924bf9937ca29628ba62e41876f05e921c0878c69fcfd4b863a110c4bc` |

The byte-lowered program has seed `3483773779` (`0xcfa62b53`), initial lineage
`1118482631` (`0x42aab0c7`), 444 executed emissions, final lineage `1390009811`
(`0x52d9ddd3`), final output `0x3e0a0000`, and final status `9` (`EMIT|HALT`).

## 20. Exact 3D representation

Source: `examples/tomagi_state_3d.json`

Entry: `orbit3d:obj-artifact`

The definition chain and hashes are:

| Definition | Kind | Content hash |
|---|---|---|
| seed | `literal_utf8` | `sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d` |
| `orbit3d:authenticated-trace` | `authenticated_trace` | `sha256:4b6c43250313f729157c08f53adf3bbdac1aaafa744ae98660a81a5517d0305a` |
| `orbit3d:emit-samples` | `select_records` | `sha256:d4433d1de35c79f038aac2e98ff45e019cc593569f7f2f19cae5d70bc3f23fd1` |
| `orbit3d:rho-theta-phi-coordinates` | `project_fields` | `sha256:d1d32b7bb21cf81f70e44f0e9b1eee4fbaf8165cb2324eea1d65a1d5d65d0c15` |
| `orbit3d:vertex-record-format` | `format_records` | `sha256:4fc8e59b8732ed24e6a2af077528eb2b2c48f76dbf4419970ba8c50eeb22a3ab` |
| `orbit3d:ordered-line-topology` | `format_records` | `sha256:ac97eb7d5a58da6bd0867e123c56011dfafd5ff1ea0e514824a23fb46f90eee4` |
| `orbit3d:obj-artifact` | `concat` | `sha256:e52578589731c7621a136ce606bb003e6a7e883edc59e3a4ca9c3c1889ec864d` |

The selector retains the same 64 `EMIT` records. The declared coordinates are:

```text
x = floor(rho   * 1000 / 1048576)
y = floor(theta * 1000 / 262144)
z = floor(phi   * 1000 / 4096)
```

One formatter emits 64 OBJ vertex records; another emits the single ordered open
line `l 1 2 ... 64`; `concat` joins both byte strings. The first vertex is
`(191,78,121)` and the last is `(648,833,583)`. The x/y/z distinct counts are
64/64/60.

Exact artifacts:

| Boundary | Bytes/count | SHA-256 |
|---|---:|---|
| source JSON | 7,622 bytes | `09ae1f5061a15b4d6ad004acb5b8b4cf93faed03994c7b2eac98db5761ceb7c5` |
| compiled `.tmg` | 16,400 bytes / 339 cells | `793446ac860d1f7abf2984e9f98e894741ee8644bcd09efa2bdda91d183ad8d1` |
| materialized OBJ | 1,355 bytes / 64 vertices | `4b356aa10acbd751b19b333db68b87e1f3c6231a7264099efb07349e555e0511` |
| manifest JSON | 6,111 bytes | `8ef29b32cc050051bf0e617139f818804b4f2d76ba836f8e407721440eda4a78` |

The byte-lowered program has seed `1484269029` (`0x587825e5`), initial lineage
`1657221527` (`0x62c73197`), 339 executed emissions, final lineage `2395171639`
(`0x8ec36b37`), final output `0x36340a00`, and final status `9` (`EMIT|HALT`).

## 21. Exact 4D numeric representation

Source: `examples/tomagi_state_4d.json`

Entry: `orbit4d:csv-record-format`

The definition chain and hashes are:

| Definition | Kind | Content hash |
|---|---|---|
| seed | `literal_utf8` | `sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d` |
| `orbit4d:authenticated-trace` | `authenticated_trace` | `sha256:faa97a2358551bf9bd1626f881d1cf0d62a1834dd060b5b250d7161cbd1f52ba` |
| `orbit4d:emit-samples` | `select_records` | `sha256:c4082d413d0cb31448efbebe487955a0d2e7fca1f4a30c2359f8ad194701e61f` |
| `orbit4d:raw-state-fields` | `project_fields` | `sha256:74ebcde87ab9e2a0ec7a9c14dba9265e9422ecce5a04fd83d2f15b8e687cdd9f` |
| `orbit4d:csv-record-format` | `format_records` | `sha256:faeb0eb44a2f43e38de571a23201ae6bfa1068623c959a8ef309fc2d75735a08` |

The selector retains the same 64 `EMIT` records. `project_fields` applies the
identity affine map (`numerator=1`, `denominator=1`, `offset=0`) to:

```text
rho, theta, tick, phi
```

The CSV header is `rho,theta,tick,phi`. The first row is
`201197,20580,1011,498`; the last is `680006,218400,3720,2388`.

**This CSV is a numeric representation of four State64 coordinates. It is not a
claim of direct visible four-dimensional rendering.** A downstream visualization
would require a separately declared, content-addressed projection.

Exact artifacts:

| Boundary | Bytes/count | SHA-256 |
|---|---:|---|
| source JSON | 6,064 bytes | `ec129e19109db9481a7fe43f47931d4311426f8e287677511ae27b8352109b2c` |
| compiled `.tmg` | 17,936 bytes / 371 cells | `37cb6a789d24ed9e18a81c87412ad3a7f428e8ad178721857762f5eb939ee5fb` |
| materialized CSV | 1,483 bytes / 64 data rows | `d1ac54e5aa0a575c021692a646e6b211acaab63ca8657740f723d06480f853df` |
| manifest JSON | 6,621 bytes | `373b6cbd72f6ebc9de5af8f23f0baf2447b30b7640be3c171e245e3cfabdfb3d` |

The byte-lowered program has seed `3020876794` (`0xb40eebfa`), initial lineage
`3812831050` (`0xe3432f4a`), 371 executed emissions, final lineage `629103799`
(`0x257f5cb7`), final output `0x38380a00`, and final status `9` (`EMIT|HALT`).

## 22. Reproducible commands

The following commands rebuild the complete chain in an isolated directory while
preserving the relative authenticated filenames. They require only the installed
package for compilation/materialization; schema validation and the full test suite
use the optional validation dependencies.

```bash
python -m pip install -e ".[validation]"
python -c "from pathlib import Path; import shutil; d=Path('build/state_replay'); d.mkdir(parents=True, exist_ok=True); [shutil.copyfile(Path('examples')/n, d/n) for n in ('tomagi_state_orbit.json','tomagi_state_2d.json','tomagi_state_3d.json','tomagi_state_4d.json')]"

python -m tomagi compile \
  build/state_replay/tomagi_state_orbit.json \
  build/state_replay/tomagi_state_orbit.tmg
python -m tomagi run \
  build/state_replay/tomagi_state_orbit.tmg \
  --ticks 640 --trace \
  --output build/state_replay/tomagi_state_orbit.trace.json

python -m tomagi compile \
  build/state_replay/tomagi_state_2d.json \
  build/state_replay/tomagi_state_2d.tmg
python -m tomagi materialize \
  build/state_replay/tomagi_state_2d.tmg \
  build/state_replay/tomagi_state_2d.svg \
  --manifest build/state_replay/tomagi_state_2d.manifest.json

python -m tomagi compile \
  build/state_replay/tomagi_state_3d.json \
  build/state_replay/tomagi_state_3d.tmg
python -m tomagi materialize \
  build/state_replay/tomagi_state_3d.tmg \
  build/state_replay/tomagi_state_3d.obj \
  --manifest build/state_replay/tomagi_state_3d.manifest.json

python -m tomagi compile \
  build/state_replay/tomagi_state_4d.json \
  build/state_replay/tomagi_state_4d.tmg
python -m tomagi materialize \
  build/state_replay/tomagi_state_4d.tmg \
  build/state_replay/tomagi_state_4d.csv \
  --manifest build/state_replay/tomagi_state_4d.manifest.json

python -m unittest discover -s tests -p "test_state_representations.py" -v
```

Verify the rebuilt program and artifact hashes with:

```bash
python -c "from pathlib import Path; import hashlib; d=Path('build/state_replay'); names=('tomagi_state_orbit.json','tomagi_state_orbit.tmg','tomagi_state_orbit.trace.json','tomagi_state_2d.json','tomagi_state_2d.tmg','tomagi_state_2d.svg','tomagi_state_2d.manifest.json','tomagi_state_3d.json','tomagi_state_3d.tmg','tomagi_state_3d.obj','tomagi_state_3d.manifest.json','tomagi_state_4d.json','tomagi_state_4d.tmg','tomagi_state_4d.csv','tomagi_state_4d.manifest.json'); [print(n, len((d/n).read_bytes()), hashlib.sha256((d/n).read_bytes()).hexdigest()) for n in names]"
```

The expected output values are:

```text
tomagi_state_orbit.json 11625 f456d0da681ae03ddb40cdc1c4566411b25a24e48d8ab279a9bc94d75a6f9cbd
tomagi_state_orbit.tmg 608 349e51a5a402b3295d653ad08f00b55d465ffab7e943fb437d196af948487e3e
tomagi_state_orbit.trace.json 252941 aa060ad1cdc25d7e95e2cdc36e1338ede0cced27f4791989b0cc287d01b9a14f
tomagi_state_2d.json 6956 4e9510a9ee659b4895e9521f39f5ed5f12a4c2ea8bbe3959dd5611fb72bb64fc
tomagi_state_2d.tmg 21440 f29dbc09bc85637584db4fec314d904dbecd672b78e51ae1d981c118439a8c95
tomagi_state_2d.svg 1774 fcaa3bd926529fe92f382f896cff042708111c10d652ac8c539386f5340f161c
tomagi_state_2d.manifest.json 7793 0c5e2f924bf9937ca29628ba62e41876f05e921c0878c69fcfd4b863a110c4bc
tomagi_state_3d.json 7622 09ae1f5061a15b4d6ad004acb5b8b4cf93faed03994c7b2eac98db5761ceb7c5
tomagi_state_3d.tmg 16400 793446ac860d1f7abf2984e9f98e894741ee8644bcd09efa2bdda91d183ad8d1
tomagi_state_3d.obj 1355 4b356aa10acbd751b19b333db68b87e1f3c6231a7264099efb07349e555e0511
tomagi_state_3d.manifest.json 6111 8ef29b32cc050051bf0e617139f818804b4f2d76ba836f8e407721440eda4a78
tomagi_state_4d.json 6064 ec129e19109db9481a7fe43f47931d4311426f8e287677511ae27b8352109b2c
tomagi_state_4d.tmg 17936 37cb6a789d24ed9e18a81c87412ad3a7f428e8ad178721857762f5eb939ee5fb
tomagi_state_4d.csv 1483 d1ac54e5aa0a575c021692a646e6b211acaab63ca8657740f723d06480f853df
tomagi_state_4d.manifest.json 6621 373b6cbd72f6ebc9de5af8f23f0baf2447b30b7640be3c171e245e3cfabdfb3d
```
