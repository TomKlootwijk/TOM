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
**pass** - The 640-step/64-EMIT source orbit and all authenticated definition DAGs compile and replay byte-identically; 2d=1774 bytes/f9419ee90565be876b1c8792b4b4250031469536a37c9949b74fa06b88541c8f; 3d=1355 bytes/ff5a0557a23d0809386c4d66e9685654ca038f61f21249ba3b627a060063dfee; 4d=1483 bytes/d1ac54e5aa0a575c021692a646e6b211acaab63ca8657740f723d06480f853df

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
**pass** - Ran 61 tests in 0.632s; return code 0

## Scope
Python was executed. C execution was not run because no platform-compatible backend was available. OpenCL was not syntax-checked because Clang was unavailable. GLSL received structural source checks because glslang was unavailable. WGSL received structural source checks; no WGSL compiler was configured. No physical GPU dispatch was performed.
