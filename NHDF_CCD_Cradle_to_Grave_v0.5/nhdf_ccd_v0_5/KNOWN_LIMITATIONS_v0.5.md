# Known limitations — v0.5

1. Cubic roots are computed in double precision; multiple, clustered, or badly scaled roots can be lost or shifted.
2. Persistent coplanarity uses bounded interval subdivision and may end inconclusively or exhaust the interval budget.
3. Tolerance is absolute in the reference API; a host-scale policy is required for heterogeneous scene units.
4. Only linearly moving feature endpoints are supported by the v0.5 VF/EE solver.
5. Mesh adjacency filtering, self-collision topology, complete broad-phase feature expansion, and rotating rigid screw motion are not implemented in the upgrade module.
6. Event grouping is temporal interval merging, not full contact-manifold construction.
7. The response example excludes angular impulse, friction, stabilization, stacking, and coupled constraint solution.
8. The vendored evidence is two files, not the complete upstream corpus.
9. The C++ translation covers bounds/events/impulse, not the full Python feature solver.
10. The CUDA skeleton is not compiled, executed, or numerically compared with the CPU implementation.
