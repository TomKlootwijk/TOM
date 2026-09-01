# TOM World & Query Kernel 0.2 Query API

Set:

```bash
export PYTHONPATH=src/python
```

## Store and index operations

```bash
python3 -m tom_world.cli init STORE TOM_seed_genome_2026-09-01.txt
python3 -m tom_world.cli commit STORE TRANSACTION.json
python3 -m tom_world.cli list STORE --type relation
python3 -m tom_world.cli index-query STORE relation_by_instance instance:benchmark:042
python3 -m tom_world.cli interval-index STORE 1 32 --type relation
python3 -m tom_world.cli rebuild-indexes STORE
python3 -m tom_world.cli audit STORE --require-no-orphans
```

The posting-list commands return exact IDs from the immutable index attached to the selected commit.

## Planned `state_at`

```bash
python3 -m tom_world.cli state-at \
  world/index_benchmark_store instance:benchmark:042 999 \
  --plan --planner indexed
```

The result contains the semantic state certificate and replay plan. Use `--no-checkpoint` for the root-replay baseline.

Python:

```python
from tom_world.query import QueryEngine
from tom_world.store import WorldStore

store = WorldStore("world/index_benchmark_store")
engine = QueryEngine(store, max_query_steps=2000, planner_mode="indexed")
planned = engine.state_at_with_plan("instance:benchmark:042", 999)
```

## Planned event queries

```bash
python3 -m tom_world.cli next-event \
  world/index_benchmark_store instance:benchmark:042 20 \
  --horizon 16 --plan --planner indexed

python3 -m tom_world.cli events-in-support \
  world/index_benchmark_store instance:benchmark:042 0 32 \
  --support support:benchmark-bucket:04 \
  --plan --planner indexed
```

For the second query, the shipped plan records `10000 -> 9600 -> 96 -> 6 -> 2` and events at ticks 5 and 21.

## Checkpoints

```bash
# Write one checkpoint record without committing it
python3 -m tom_world.cli make-checkpoint \
  world/counter_store instance:counter 4 checkpoint.json

# Commit exact checkpoints
python3 -m tom_world.cli commit-checkpoints \
  world/counter_store instance:counter 0 2 4
```

Checkpoint creation always replays from the instance root.

## Stable batch query

```bash
python3 -m tom_world.cli batch-query \
  world/index_benchmark_store \
  examples/index_benchmark/batch_requests.json \
  --planner indexed --output validation/batch.json
```

The request file contains a `requests` array. Supported operations are `state_at`, `next_event`, `events_in_support`, `compatible`, and `definition_at`. IDs must be unique. Evaluation order is exactly array order.

## Existing native queries

```bash
python3 -m tom_world.cli definition-at STORE definition:world-query-kernel
python3 -m tom_world.cli verify-definition STORE definition:world-query-kernel
python3 -m tom_world.cli trace STORE instance:counter 5
python3 -m tom_world.cli compatible STORE instance:counter instance:peer compatibility:same-topology 3
python3 -m tom_world.cli reconstruct STORE lineage:<prefix>
python3 -m tom_world.cli expand-grammar STORE grammar:bounded-binary-branch --depth 3
```

## Literal documentation artifact

```bash
python3 -m tom_world.cli make-artifact-source \
  docs/WORLD_QUERY_KERNEL_0_2_RELEASE.md \
  examples/artifacts/world_query_kernel_0_2_release.source.json \
  --artifact-id world-query-kernel-0-2-release \
  --media-type 'text/markdown; charset=utf-8' \
  --seed TOM_seed_genome_2026-09-01.txt

python3 -m tom_world.cli compile-artifact \
  examples/artifacts/world_query_kernel_0_2_release.source.json \
  examples/artifacts/world_query_kernel_0_2_release.tmg \
  --seed TOM_seed_genome_2026-09-01.txt

python3 -m tom_world.cli materialize-artifact \
  examples/artifacts/world_query_kernel_0_2_release.tmg \
  artifacts/TOM_WORLD_QUERY_KERNEL_0_2_RELEASE.md
```
