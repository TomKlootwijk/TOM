# Cradle-to-grave roadmap

No stage may erase uncertainty, unsupported geometry, numerical failure, or bounded-resource failure.

## G0 - Provenance and claim boundary
**Inputs:** S1-S4.
**Outputs:** source register, claim dispositions, privacy policy.
**Gate:** Every claim is source-derived, externally supported, or explicitly labeled hypothesis.

## G1 - Requirements and hazard model
**Inputs:** use case, shapes, motions, tolerances.
**Outputs:** requirements, acceptance criteria, hazards.
**Gate:** Supported profile and caller policy are unambiguous.

## G2 - Mathematical contract
**Inputs:** requirements.
**Outputs:** typed state, separation oracle, speed/inclusion bounds, certificate semantics.
**Gate:** No heuristic has safety authority; every no-hit statement has a proof obligation.

## G3 - CPU reference
**Inputs:** formal contract.
**Outputs:** deterministic implementation, schemas, reference vectors.
**Gate:** Unit/property tests pass and failures are preserved.

## G4 - Robust verification
**Inputs:** CPU reference, exact datasets.
**Outputs:** differential results, adversarial corpus, coverage.
**Gate:** Zero false negatives in declared profile; TOI bounds within tolerance.

## G5 - Accelerated backend
**Inputs:** verified CPU semantics.
**Outputs:** C++/GPU implementation, equivalence report.
**Gate:** CPU/GPU outcomes and failure states agree; performance is measured.

## G6 - Application integration
**Inputs:** verified CCD backend, response solver.
**Outputs:** engine adapter, rollback/safe-stop policy, HIL tests.
**Gate:** End-to-end tunneling and failure-recovery tests pass.

## G7 - Deployment and operations
**Inputs:** integrated system.
**Outputs:** runbook, telemetry, incident process.
**Gate:** Monitoring detects divergence, overflow, invalid bounds, and unsupported inputs.

## G8 - Domain adapters
**Inputs:** core evidence, domain laws.
**Outputs:** adapter contract, domain-specific validation.
**Gate:** The adapter preserves units/invariants and beats or complements a baseline.

## G9 - Maintenance and change control
**Inputs:** defects, new hardware, new geometry.
**Outputs:** versioned changes, regression evidence, rollback.
**Gate:** Every correctness-affecting change is revalidated.

## G10 - Retirement
**Inputs:** supersession or failure.
**Outputs:** migration, archive, data deletion.
**Gate:** No caller silently falls back to unsafe discrete checks.
