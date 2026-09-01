# Retirement and decommissioning plan

A backend or release is retired when it cannot meet its declared correctness profile, depends on unsupported hardware/software, or has been superseded by a verified implementation.

## Procedure

- Freeze the version and publish the reason.
- Identify affected applications and scenes.
- Preserve reference vectors, exact datasets, build environment, and incident reports according to policy.
- Migrate callers to a supported backend with differential replay.
- Revoke production configuration and deployment credentials.
- Delete personal/sensor data according to retention rules while retaining non-personal reproducibility artifacts.
- Archive source, report, hashes, and known limitations.

No retired backend may silently fall back to discrete endpoint tests for workloads that require CCD.
