# Typed NHDF-CCD operator contract

The v0.4 state is threaded through every stage:

`Sigma = (scene, time_interval, candidates, motion_bounds, separation_oracles, refinement_queue, certificates, telemetry, failures)`.

The normative chain is:

`Sigma' = U(Pi_cert(R_refine(A_CA(B_bound(C_pair(E_scene(Sigma)))))))`.

Source vocabulary maps as follows:

| Source operator | CCD v0.4 role | Correctness authority |
|---|---|---|
| log-polar LUT | scheduling metadata and workload binning | no |
| local SDF-zero | pair separation equation `d_ij(t)=0` | yes, when the distance contract is valid |
| 1-bit parity | anomaly/refinement hint; diagnostic only | no |
| BST/L-system | bounded interval or candidate refinement queue | only its certified bounds, not tree shape |
| golden ratio / delta-delta phase | optional split/priority ablation | no |
| forward timeline | monotonic TOI interval and generation order | yes |
| cone sweep | conservative swept support/bounds | yes when mathematically conservative |
| projection | collision certificate/contact manifold output | yes if derived from valid narrow phase |
| feedback | scheduler/cache update and telemetry | no independent geometric authority |
| Klein-bottle chart | optional topology metadata | no role in ordinary Euclidean contact correctness |

A heuristic may increase work or trigger a safer backend. It may not discard a broad-phase candidate, move a TOI later, convert `INCONCLUSIVE` to `NO_HIT`, or manufacture a contact.
