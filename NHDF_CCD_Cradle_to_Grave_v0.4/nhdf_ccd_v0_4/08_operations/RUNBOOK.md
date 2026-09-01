# Operations runbook

## Startup

- Verify release hashes and configuration schema.
- Run reference-vector smoke tests.
- Confirm units, coordinate frame, time normalization, and shape backend support.
- Allocate bounded pools and record actual available memory.

## Runtime telemetry

Record at least: frame/generation, candidate count, backend counts, earliest TOI bracket, iteration count, minimum separation, tolerance, overflow flags, unsupported count, inconclusive count, runtime, and trace digest.

## Alarms

- Any false-negative found in replay: stop the affected backend.
- Repeated `INCONCLUSIVE`: lower step or switch to robust backend.
- Capacity watermark: throttle nonessential queries before overflow.
- NaN/Inf or invalid bound: quarantine input and fail safe.
- CPU/GPU divergence: disable accelerated backend.

## Incident preservation

Save the exact scene input, configuration, build hash, hardware/runtime versions, certificate trace, and deterministic replay seed. Do not rely on screenshots or personal metadata as cryptographic evidence.
