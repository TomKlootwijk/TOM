# Examples

## Original TOMAGI examples

`polar_loop.json`, `exact19_rule.json`, and `nineteen_hinge.json` are retained and regression-tested against TOMAGI 1.0.

## Counter world

`world_counter/` contains the 0.1 starter world: a one-cell linear TOMAGI trajectory, relations, support, compatibility, transition, event specification, bounded grammar, and the initial content-addressed transaction.

## 10,000-record index benchmark

`index_benchmark/` contains frozen literal source:

- `initial_transaction.json`: 9,990 content-addressed records and one TOMAGI blob reference;
- `checkpoint_transaction.json`: ten exact checkpoints;
- `batch_requests.json`: four declared-order queries;
- `benchmark_spec.json`: content-addressed acceptance contract.

The generated committed store lives at `world/index_benchmark_store/`; certificates live at `validation/index_benchmark/`.

## Literal documentation artifacts

`artifacts/` contains the content-addressed definition sources and compiled `.tmg` EMIT programs for:

- the combined AGI roadmap and starter document;
- the World & Query Kernel 0.2 release record.

Each materialized artifact is byte-identical to its documentation source and can be reconstructed from either the Python or C execution trace using the generic byte materializer.
