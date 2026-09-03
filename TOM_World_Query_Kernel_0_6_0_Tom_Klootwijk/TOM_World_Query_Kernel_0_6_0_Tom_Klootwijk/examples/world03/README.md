# World & Query Kernel 0.3 examples

`interval_event_world.json` is the authoritative literal source. Ordinary builds read and verify this file; they do not replace its semantics from host code. A maintainer may explicitly regenerate the same source with `TOM_WORLD03_REFRESH_SOURCE=1` and then review the resulting content-addressed diff.

`affine_reference.tmg` is a one-cell TOMAGI program using `KIN2` with constant velocity. Its integer states provide independent machine anchors for the affine query trajectory.

The generated certificates are under `validation/world03/`:

- `certified_crossing_x5.json`
- `events_0_10.json`
- `next_event_set.json`
- `simultaneous_transition.json`
- `trusted_baseline_comparison.json`
- `tomagi_trajectory_baseline.json`
- `simultaneous_conflict_rejection.json`
- `fixture_report.json`
