# TOM World & Query Kernel 0.3.0

## Exact rational interval events over the frozen TOMAGI 1.0 substrate

This release continues TOM World & Query Kernel 0.2 with the first certified between-tick event layer:

```text
exact rational affine trajectory
-> typed continuous SDF0@Def relation
-> closed interval residual and derivative
-> certified crossing bracket
-> exact root when affine
-> support and compatibility
-> simultaneous event set
-> deterministic event ordering
-> atomic conflict-checked transition
-> content-addressed certificate
```

The canonical 244-byte TOM seed, executable-definition compiler, persistent world store, immutable indexes, checkpoints, audit, and 10,000-record 0.2 fixture remain in the package. TOMAGI's 128-byte header, 64-byte `State64`, 48-byte `Cell48`, sixteen opcodes, and fixed-width transition semantics are unchanged.

## What 0.3 adds

- canonical reduced rational values;
- exact closed rational interval arithmetic;
- typed continuous expressions with constants, fields, time, negation, addition, subtraction, and multiplication;
- exact point, interval, and derivative-interval evaluation;
- sign-change or exact-endpoint existence certificates;
- monotonic derivative-interval uniqueness certificates;
- exact affine root extraction and bounded rational bisection;
- support and compatibility gates at exact roots or conservatively over unresolved brackets;
- exact-time simultaneous event sets;
- total event order `(root_time, priority, relation_id, event_id, relation_hash)`;
- deterministic per-field transition merge with explicit conflict rejection;
- an independent `fractions.Fraction` baseline;
- a TOMAGI integer-anchor program with full Python/C trace comparison;
- strict 0.3 world schema, CLI, tests, clean rebuild, and release package verification.

## Canonical fixture

The trajectory is:

```text
x(t)       = 2t
clock(t)   = t
mode(t)    = 1
counter(t) = 0
output(t)  = 0
0 <= t <= 10
```

Three relations reach zero at exactly `t=5/2`:

```text
time - 5/2 = 0
3*x - 15   = 0
x - 5      = 0
```

The `x-5` bracket `[2,3]` has exact residuals `[-1,+1]`, derivative interval `[2,2]`, and a unique exact root `5/2`. The simultaneous transition yields `counter=3` and `output=25`. A later event occurs at `t=5`; inactive, unsupported, and incompatible roots are rejected.

## Build and validate

```bash
# Build the literal 0.3 fixture and certificates.
PYTHONPATH=src/python python3 tools/build_world03_fixture.py

# Run all inherited and 0.3 tests.
PYTHONPATH=src/python python3 -m unittest discover -s tests -v

# Run the full 0.3 release validation and clean replay.
PYTHONPATH=src/python python3 tools/run_world03_validation.py

# Create the deterministic 0.3 ZIP and external release files.
PYTHONPATH=src/python python3 tools/package_world03_release.py
```

Convenience targets are also supplied:

```bash
make world03
make test-world03
make validate-world03
make package-world03
```

## CLI

```bash
# Validate the literal world.
PYTHONPATH=src/python python3 -m tom_world03 validate-world \
  examples/world03/interval_event_world.json

# Certify x-5 on [2,3].
PYTHONPATH=src/python python3 -m tom_world03 certify-crossing \
  examples/world03/interval_event_world.json \
  relation:x-equals-five 2 3

# Query the earliest simultaneous event set.
PYTHONPATH=src/python python3 -m tom_world03 next-event-set \
  examples/world03/interval_event_world.json 0 10

# Apply its conflict-checked transition.
PYTHONPATH=src/python python3 -m tom_world03 apply-next-event-set \
  examples/world03/interval_event_world.json 0 10

# Compare accepted roots with the independent Fraction baseline.
PYTHONPATH=src/python python3 -m tom_world03 compare-baseline \
  examples/world03/interval_event_world.json 0 10
```

## Primary files

- `spec/TOM_WORLD_QUERY_KERNEL_0_3.md` — normative interval-event profile.
- `spec/tom_world_query_kernel_0_3.schema.json` — strict source schema.
- `TOM_AGI_ROADMAP_AND_STARTER_0_3.md` — updated roadmap through 0.3.
- `TOM_WORLD_QUERY_KERNEL_0_3_RELEASE.md` — release overview.
- `src/python/tom_world03/` — implementation.
- `examples/world03/interval_event_world.json` — authoritative literal fixture.
- `examples/world03/affine_reference.tmg` — underlying integer-anchor program.
- `validation/world03/` — crossing, event-set, transition, baseline, trace, tests, and clean-rebuild evidence.

The previous 0.2 README and changelog are retained as `README_0_2.md` and `CHANGELOG_0_2.md`.

## Evidence boundary

0.3 certifies finite continuous expressions over exact rational affine trajectories. It does not claim validated arbitrary ODE integration, transcendental interval functions, autonomous learning, planning, perception, or AGI. The next kernel milestone is 0.4: piecewise validated dynamics, interval candidate indexes, event-set world transactions, and post-event continuation.
