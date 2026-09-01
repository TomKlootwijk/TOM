# Domain adapter contract

A domain adapter is not a metaphorical rename of the CCD variables. It is a declared tuple

`A_d = (X_d, Phi_d, g_d, E_d, O_d, D_d, I_d, M_d, F_d)`

where:

- `X_d` is the physical or computational state space;
- `Phi_d` is the accepted evolution model;
- `g_d(x,t)=0` is a measurable event/contact/constraint boundary;
- `E_d` and `D_d` encode/decode between domain state and the NHDF runtime state;
- `O_d` is the subset of operators actually implemented;
- `I_d` lists units, conservation laws, causality, positivity, and other invariants;
- `M_d` defines metrics and baselines;
- `F_d` enumerates explicit failure states and stop conditions.

For a true cross-domain equivalence claim, the adapter must demonstrate

`||D_d(N_dt(E_d(x))) - Phi_d^dt(x)|| <= epsilon_d`

on a declared domain, with calibrated uncertainty and a baseline. Shared notation alone is not equivalence.

## CCD relationship classes

- **Literal CCD**: detects contact between moving geometric bodies.
- **Boundary-event reuse**: reuses bracketing/inclusion logic for another continuous threshold crossing.
- **Scheduling analogy only**: may reuse queues or coordinates but not collision semantics.
- **Research hypothesis**: no operator equivalence has been demonstrated.
