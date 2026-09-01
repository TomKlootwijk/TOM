# TOMAGI 1.0 validation report

Generated: 2026-09-01

Pass: 6; source-checked: 2; failures: 0; not run: 4

## JSON Schema examples
**pass** - Draft 2020-12 validation: polar_loop.json, exact19_rule.json, tomagi_state_orbit.json, tomagi_state_2d.json, tomagi_state_3d.json, tomagi_state_4d.json

## Python/C equality: polar_loop
**not-run** - no compatible C executable for Windows (expected PE; tomagi-c=ELF)

## Python/C equality: exact19_rule
**not-run** - no compatible C executable for Windows (expected PE; tomagi-c=ELF)

## Python/C equality: tomagi_state_orbit
**not-run** - no compatible C executable for Windows (expected PE; tomagi-c=ELF)

## Literal State64 2D/3D/4D representation replay
**pass** - The 640-step/64-EMIT source orbit and all authenticated definition DAGs compile and replay byte-identically; 2d=1774 bytes/fcaa3bd926529fe92f382f896cff042708111c10d652ac8c539386f5340f161c; 3d=1355 bytes/4b356aa10acbd751b19b333db68b87e1f3c6231a7264099efb07349e555e0511; 4d=1483 bytes/d1ac54e5aa0a575c021692a646e6b211acaab63ca8657740f723d06480f853df

## 64-bit key reference vectors
**pass** - contiguous=0xe7b77000007800e3; Morton=0x88823bb88099128b

## OpenCL C syntax
**not-run** - clang was not found on PATH

## GLSL 4.50 source
**source-checked** - Balanced delimiters, shared ABI symbols and opcode dispatch present; glslang was not found on PATH.

## WGSL source
**source-checked** - Balanced delimiters, shared ABI symbols and opcode dispatch present; no WGSL compiler was configured.

## Operator/source condensation
**pass** - 43 operators; 322 crosswalk rows; 8 source artifacts; source labels ['SRC-A', 'SRC-B', 'SRC-C', 'SRC-D', 'SRC-E', 'SRC-F', 'SRC-G', 'SRC-H']

## Binary ABI sizes
**pass** - header=128; state=64; cell=48; polar_loop bytes=800

## Python conformance suite
**pass** - Ran 62 tests in 0.624s; return code 0

## Scope
Python was executed. C execution was not run because no platform-compatible backend was available. OpenCL was not syntax-checked because Clang was unavailable. GLSL received structural source checks because glslang was unavailable. WGSL received structural source checks; no WGSL compiler was configured. No physical GPU dispatch was performed.
