# Native Query API 0.1

The CLI is installed as `tom-world`. With an unpacked repository, prefix commands with `PYTHONPATH=src/python python3 -m tom_world.cli`.

## Initialize and commit

```bash
PYTHONPATH=src/python python3 -m tom_world.cli init \
  world/counter_store --seed TOM_seed_genome_2026-09-01.txt

PYTHONPATH=src/python python3 -m tom_world.cli commit \
  world/counter_store examples/world_counter/initial_transaction.json
```

## `definition_at(id)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli definition-at \
  world/counter_store relation:counter-rho-equals-five
```

Returns the exact immutable record at the selected commit.

## `verify_definition(id)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli verify-definition \
  world/counter_store definition:world-query-kernel
```

Verifies object identity, record content hash, and dependency resolution.

## `state_at(t)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli state-at \
  world/counter_store instance:counter 3
```

The 0.1 meaning of `t` is a zero-based count of complete TOMAGI transitions. The benchmark returns `rho=3` and `tick=3`.

## `next_event(t0)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli next-event \
  world/counter_store instance:counter 0 --horizon 8 \
  --output validation/next_event.json
```

Returns the earliest event at index 5 with residual zero, passed support and compatibility gates, event/pre/post states, transition, route, confidence record, guard margin, and definition hashes.

## `events_in_support`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli events-in-support \
  world/counter_store instance:counter 0 8 \
  --support support:counter-rho-window
```

The interval is `(start_tick, end_tick]`.

## `compatible(q1,q2)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli compatible \
  world/counter_store instance:counter instance:peer \
  compatibility:same-topology 3
```

Returns a certificate containing both exact states and the boolean result.

## `trace`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli trace \
  world/counter_store instance:counter 5
```

Returns the ordered TOMAGI transitions and terminal state.

## `reconstruct(lineage)`

```bash
PYTHONPATH=src/python python3 -m tom_world.cli reconstruct \
  world/counter_store lineage:<certificate-prefix>
```

Loads the embedded event certificate, checks its content hash, replays the source commit and query, and reports whether the canonical certificate bytes are equal.

## Bounded grammar

```bash
PYTHONPATH=src/python python3 -m tom_world.cli expand-grammar \
  world/counter_store grammar:bounded-binary-branch --depth 3
```

Returns every finite generation, branch-bit decisions, stack depth, and terminal symbols.

## Literal emitted-byte documentation

```bash
PYTHONPATH=src/python python3 -m tom_world.cli make-artifact-source \
  docs/ROADMAP_AND_STARTER.md examples/artifacts/roadmap.source.json \
  --artifact-id tom-agi-roadmap-and-starter \
  --media-type text/markdown \
  --seed TOM_seed_genome_2026-09-01.txt

PYTHONPATH=src/python python3 -m tom_world.cli compile-artifact \
  examples/artifacts/roadmap.source.json \
  examples/artifacts/roadmap.tmg \
  --seed TOM_seed_genome_2026-09-01.txt

PYTHONPATH=src/python python3 -m tom_world.cli materialize-artifact \
  examples/artifacts/roadmap.tmg \
  artifacts/TOM_AGI_ROADMAP_AND_STARTER.md
```
