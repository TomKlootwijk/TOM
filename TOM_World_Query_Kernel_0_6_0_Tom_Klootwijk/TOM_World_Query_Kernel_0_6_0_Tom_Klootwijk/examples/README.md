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

## Corrective 0.4.1 open-segment continuation

`world04r/` is the rebuilt 0.4 line. It is based only on the pinned corrected
0.3 archive and uses the fresh `tom_world04r` namespace. The superseded
`tom_world04` implementation is not present.

Literal authority files:

- `piecewise_world.json` — 1,208 content-addressed relations, exact interval
  index, support/compatibility records, and an initial open segment spanning
  the complete world horizon;
- `piecewise_reference.json` — literal TOMAGI integer-anchor source;
- `world04r_release_artifact.literal.json` — seeded executable source for the
  release-document artifact.

Generated evidence:

- `piecewise_reference.tmg`;
- `continuation_store/` — genesis, four solver-derived event commits, and an
  explicit horizon-finalization commit;
- `validation/world04r/` — indexed/exhaustive runs, independent baseline,
  crossing/event/transition/seal certificates, Python/C traces, journal audit
  and reconstruction, rejection capsule, clean replay, and validation report.

No authoritative relation may contain `continuation_until`. Every realized
segment endpoint is produced by the corrected 0.3 exact event certifier, then
recorded in a separate immutable segment seal. Every successor begins at that
certified root and remains open to the declared world horizon.

## TOM Learner 0.2 / WQK 0.6

`learner06/` contains the literal authority and generated evidence for the finite four-family learner:

- `family_registry.json` — 121 candidates across polynomial, piecewise-affine, transition-table, and expression-tree families;
- `datasets/` and `dataset_bundle.json` — sixteen exact train/validation/holdout fixtures;
- `prior_authority.json` — twelve pinned 0.5.2 definitions and regression cases;
- `learner06_family_authority.formal.json` and `.literal.json` — formal learner and seeded execution graph;
- `learner06_promotion_authority.formal.json` and `.literal.json` — parent-bound promotion continuation;
- `promotion_store/` — generic same-host locked immutable store ending at the canonical 0.6 terminal head;
- `learner06_release_artifact.literal.json` — literal TOMAGI source of the byte-identical 0.6 release document.

The formal learner accepts nine data sets, rejects seven, and emits three explicit ambiguity records. The independent oracle agrees on all sixteen outcomes. Generated proofs and traces live under `validation/learner06/`.
