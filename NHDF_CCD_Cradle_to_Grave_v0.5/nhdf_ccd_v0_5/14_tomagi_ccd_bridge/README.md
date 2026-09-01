# TOMAGI CCD bridge v0.1

This directory supplies one deliberately narrow, executable bridge between the
literal TOM seed/TOMAGI substrate and NHDF-CCD v0.5.

`FORMAL_PROFILE.md` is the normative specialization for this fixture.

The fixture is an exact q4 fixed-point, zero-thickness vertex-face query:

- static closed triangle `A=(0,0,0)`, `B=(1,0,0)`, `C=(0,1,0)`;
- vertex `P(T)=(1/4,1/4,3/4-T)` for `T` in `[0,1]`;
- expected first contact `HIT` at `T=3/4`.

The literal definition graph does not merely embed the successful result. It
constructs executable `SET`, `KIN2`, `CONE`, `SPHERE`, and `RADIX` cells. The
runtime advances signed separation and time in State64, detects `rho=0`, checks
a conservative `x,y in [0,1/2]` support patch contained in the triangle, and
branches to either the `MISS` or `HIT` certificate. The selected canonical JSON
bytes are emitted and generically materialized from ordered runtime records.

## Causal chain

```text
<repository-root>/TOM_seed_genome_2026-09-01.txt
  + ccd_vf_q4.source.json
  + token_registry_1_0.json
  + <repository-root>/TOM_Genesis_1_0_Tom_Klootwijk.zip
    -> ccd_vf_q4.tmg
    -> ccd_vf_q4.replay.json
    -> ccd_vf_q4.certificate.json
    -> ccd_vf_q4.proof.json
```

Run from this directory:

```powershell
python -B build_and_validate.py
```

The validator rebuilds twice in isolated temporary directories, requires
byte-identical `.tmg`, compile manifests, traces, EMIT records, and materialized
certificate bytes, then checks the same fixture with the independent v0.5
floating-point reference solver.

`C_BACKEND_VALIDATION.md` records an additional Python/C semantic replay match.

## Claim boundary

This proves a real TOMAGI execution/replay for the stated fixture. It is not yet
a general CCD compiler, a finite-thickness proof, a mesh-level solver, or a
camera-sensor frontend. Extending the literal operation set with general exact
polynomial and interval operations is required before arbitrary VF/EE queries
can be compiled this way.
