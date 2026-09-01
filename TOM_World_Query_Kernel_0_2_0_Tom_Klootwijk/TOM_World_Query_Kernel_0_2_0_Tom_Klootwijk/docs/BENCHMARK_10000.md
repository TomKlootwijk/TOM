# TOM Immutable-Index Benchmark — 10,000 Records

## Frozen source

The benchmark is not generated from hidden runtime behavior. Its two content-addressed transactions are shipped as literal JSON:

- `examples/index_benchmark/initial_transaction.json` — 9,990 records;
- `examples/index_benchmark/checkpoint_transaction.json` — ten checkpoint records;
- `examples/index_benchmark/batch_requests.json` — ordered query batch;
- `examples/index_benchmark/benchmark_spec.json` — content-addressed acceptance contract.

The initial transaction references the literal compiled counter `.tmg` blob. The committed world is under `world/index_benchmark_store/`.

## Population

| Record type | Count in final snapshot |
|---|---:|
| definition | 1 |
| support | 16 |
| compatibility | 4 |
| instance | 100 |
| relation | 9,600 |
| observation | 269 |
| checkpoint | 10 |
| **Total** | **10,000** |

## Exact query evidence

Primary indexed query:

```text
instance = instance:benchmark:042
interval = (0,32]
support  = support:benchmark-bucket:04
```

Candidate path:

```text
10,000 records
9,600 relation records
96 instance relations
6 support-bucket relations
2 interval-overlapping relations
```

Result: two exact events at ticks 5 and 21. Exhaustive evaluation returns byte-identical semantic certificate data.

## Checkpoint evidence

The state query at tick 999 selects checkpoint 900 and executes 99 transitions. The checkpoint-free baseline executes 999. Both return the same complete state and semantic certificate hash.

## Evidence files

- `validation/index_benchmark/report.json`
- `validation/index_benchmark/events_indexed.json`
- `validation/index_benchmark/events_exhaustive.json`
- `validation/index_benchmark/state_at_999_indexed.json`
- `validation/index_benchmark/state_at_999_exhaustive.json`
- `validation/index_benchmark/batch_indexed.json`
- `validation/index_benchmark/batch_exhaustive.json`
- `validation/index_benchmark/index_rebuild.json`
- `validation/index_benchmark/audit.json`

Wall-clock time is not a normative result. Work counters and candidate counts are.
