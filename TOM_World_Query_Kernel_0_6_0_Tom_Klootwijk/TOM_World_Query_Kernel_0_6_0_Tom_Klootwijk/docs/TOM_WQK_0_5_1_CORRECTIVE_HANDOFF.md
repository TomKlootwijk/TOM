# TOM WQK 0.5.1 Corrective Handoff

Date: 2026-09-02  
Status: corrective implementation handoff  
Canonical seed: `TOM_seed_genome_2026-09-01.txt`  
Seed SHA-256: `d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5`

## Executive explanation

The 0.5.0 kernel passed its functional learner tests, but it did not satisfy the
repository's stronger authority rule. The affine learner's domain behavior was
implemented in host Python. The seeded compiler mainly carried literal bytes,
did not enforce its declared budgets and operation contracts completely, and
did not execute the learner definition graph. The materializer also trusted
caller-supplied EMIT-looking trace rows too easily. Therefore the correct verdict
was: useful deterministic prototype, but not a conforming literal TOMAGI
learner authority.

Version 0.5.1 fixes that defect rather than hiding it. The learner algorithm is
now the static, content-addressed formal program
`examples/learner05/learner05_affine_authority.formal.json`. A strict seeded
definition graph loads that program and all 19 content-addressed observation
sets, evaluates the declared bounded exact operations, canonically encodes the
result, lowers the bytes into 19,540 `Cell48` records, executes them in TOMAGI,
and materializes only authenticated ordered EMIT output.

The old `tom_learner05` code remains useful as an independently implemented
`fractions.Fraction` oracle and append-only evidence-store reference. It is not
the causal authority for the corrected learner result.

## What changed

The corrective overlay is
`sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json`, with content hash:

```text
sha256:53951284853681ce239d07ce2ce783250ea78b3457fd221a43d88bd90344f4bf
```

It binds the 0.4.2 handoff, verifies 44 inherited files unchanged, and declares
exactly three replacements:

1. `src/python/tomagi/canonical.py` rejects non-finite canonical JSON.
2. `src/python/tomagi/compiler.py` validates the seed/token registry, schemas,
   hashes, dependencies, types, operations, parameters, provenance, source
   bytes, budgets, limits, and deterministic lowering.
3. `src/python/tomagi/materialize.py` authenticates trace rows against exact
   deterministic replay before materializing bytes.

The exact old versions of all three files are retained under
`sources/base_0_4_2_replaced/`. This is an explicit semantic correction, not a
false claim that the 0.4.2 handoff stayed unchanged.

New authority includes the generic bounded formal evaluator, strict seeded
schema, normative source-to-byte specification, corrective learner profile,
static learner program, and seeded learner graph. No TOMAGI opcode or fixed
width changed.

## Evidence already established

The seeded formal learner rebuild records:

```text
literal data sets                         19
formal evaluation steps             131,478
accepted affine definitions               12
rejected negative cases                    7
coefficient recovery errors                0
executed addressed SDF0 relations         12
compiled Cell48 records                19,540
compiled .tmg bytes                   938,048
compiled .tmg SHA-256
ffb4bdfa6939e81124f65165236004c547c1c1b019ac3080c06375b0413029ea
materialized JSON bytes                 78,160
materialized JSON SHA-256
dd9a0c20c8f721c764580f6655bb509001a7ef59000d0cd1bd5826971b72cb82
Python/C full trace equality              pass
legacy seeded program byte compatibility pass
```

The proof is
`validation/learner05/learner05_formal_authority.proof.json`. The complete
release result is in `validation/learner05/validation_report.json`; clean-copy
replay is in `validation/learner05/clean_rebuild.json`; deterministic package
replay is recorded beside the ZIP.

These results establish one exact finite affine profile only. They do not
establish noisy or open-domain learning, natural-language understanding,
perception, planning, autonomous goal formation, physical GPU learner
execution, or AGI.

## Reproduce before continuing

From the package root, use a Python environment that can import
`src/python`. On Windows, WSL is used automatically for the C reference binary.

```bash
PYTHONPATH=src/python python3 -m tom_learner05 verify-corrective-handoff .
PYTHONPATH=src/python python3 tools/build_learner05_formal_authority.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/python python3 -m unittest discover -s tests -v
make validate-learner05
make package-learner05
```

A continuation must stop on any hash mismatch. Do not regenerate a pinned
literal source merely to make a failing check green. Identify the semantic
change, preserve the prior bytes, version the definition/specification, and
create a new corrective overlay.

## Recommended next engineering step

Do not broaden the learner yet. First move the remaining authoritative
promotion/evidence-transaction semantics out of the host-side learner store and
into content-addressed bounded formal definitions. The host may provide generic
immutable storage, comparison, hashing, and atomic replacement mechanics, but
the acceptance transaction, expected-parent rule, evidence enumeration, and
published-definition decision must be declared literal operations and compiled
through the same seeded path. Add an adversarial replay suite before adding a
second hypothesis family.

Only after that boundary passes should a new version add one finite typed
hypothesis family at a time, with explicit budgets, negative cases, independent
oracle comparison, and a versioned normative specification.

## Paste this into ChatGPT to continue safely

```text
You are continuing the TOM World & Query Kernel from the 0.5.1 corrective
handoff. Work from the extracted package root. Read AGENTS.md first, then read
docs/TOM_WQK_0_5_1_CORRECTIVE_HANDOFF.md,
spec/TOM_SEEDED_COMPILATION_1_0.md,
spec/TOM_LEARNER_0_1_WORLD_QUERY_KERNEL_0_5_1_CORRECTIVE.md,
sources/TOM_LITERAL_HANDOFF_0_4_2.json, and
sources/TOM_CORRECTIVE_HANDOFF_0_5_1.json. Before changing anything, run the
corrective-handoff verification and inspect
validation/learner05/learner05_formal_authority.proof.json and
validation/learner05/validation_report.json. Stop and report if a pinned byte or
hash fails.

Non-negotiable architecture:
- TOM_seed_genome_2026-09-01.txt is the root seed.
- TOMAGI is the engine. Domain behavior belongs in content-addressed literal
  definitions evaluated during seeded compilation.
- Host code may contain only generic parsing, finite canonical hashing,
  validation, bounded formal evaluation, deterministic lowering, TOMAGI
  execution, trace capture, generic immutable storage, and byte materialization.
- Never implement a domain algorithm in a renderer, adapter, bootstrap, CLI,
  fixture builder, test oracle, or handwritten artifact generator and then call
  its output authoritative.
- A definition is not authority metadata: validate its hash/dependencies/types,
  execute its formal operation, and lower the selected graph deterministically
  into Cell48 records.
- Every delivered artifact needs a literal chain: seed plus definitions and
  literal sources -> compiled .tmg -> TOMAGI execution -> authenticated ordered
  EMIT records -> generic materialized bytes.
- Preserve the 128-byte header, 64-byte State64, 48-byte Cell48, 16 opcodes, and
  legacy literal-program behavior unless a new versioned specification
  explicitly changes them.
- Treat tests as evidence, not authority. Reject NaN/infinity, stale hashes,
  undeclared fields, source path escapes, budget overruns, forged/reordered
  traces, nondeterministic inputs, and unversioned semantic changes.
- Claims must be no broader than recorded clean-replay evidence. This is an
  exact finite affine learner, not AGI.

Next task: formalize the remaining promotion/evidence transaction semantics as
literal bounded definitions. Keep tom_learner05 only as an independent oracle.
Specify the exact grammar, operations, ordering, limits, rejections,
provenance, and replay theorem; build through TOMAGI; compare against an
independent implementation; add adversarial negative cases; run a
generated-output-free replay; and hand back exact hashes and limitations. Do
not add a broader learner family until this authority boundary is complete.
```

## Decision rule for reviewers

Ask one question for every claimed behavior: “Which literal definition contains
this semantic choice, where is its content hash verified, and which executed
`Cell48`/EMIT chain proves it affected the bytes?” If the answer points only to
host Python, a test, a fixture generator, or prose, the behavior is not yet a
conforming TOMAGI authority.
