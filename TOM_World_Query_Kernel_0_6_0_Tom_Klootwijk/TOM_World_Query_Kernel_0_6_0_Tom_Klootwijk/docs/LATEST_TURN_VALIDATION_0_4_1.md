# Independent validation of the latest trusted turn

## Result

The trusted V0.4.1 corrective archive was independently extracted and validated before 0.5 implementation began.

Verified identities:

```text
archive SHA-256
de8d47704f086f8f265b79aa4c373b5d84127ddbb3e8662c3c1cda57e8272517

corrected interval implementation
ea7b3ff2127e8ee7a696eb45e84ae9efdbca7c10c532617c51888fb13cd39f6d

semantic chain
9fd4f3e1ae8550ae3ca99e27e7bf61b22a4935fe764fd443723abfdb3804f226

validation content hash
57be1528d1759c5469259a71daa6f0118b006a1f6a38f9d205f29d3230308391
```

Checks performed:

- 10,379-file internal package manifest: exact;
- 10,380-entry internal SHA-256 inventory: exact;
- canonical seed: 244 bytes, no terminal line ending, exact hash;
- `make validate-world04r`: completed successfully;
- inherited and corrective tests: 144 passed;
- validation checks: 20 passed, zero failures;
- clean replay boundaries: 24 equal;
- indexed, exhaustive, independent baseline, and journal reconstruction: equal;
- event times: exact 2, 5, 7, 9;
- final state at time 10: `clock=10, counter=34, mode=5, output=90, x=3`;
- superseded `tom_world04` namespace: absent;
- relation-authored `continuation_until`: absent from corrected authority.

## Exact uploaded V0.4.2 archive limitation

The conversation supplied a file named `TOM_World_Query_Kernel_0_4_2_Literal_Handoff_Tom_Klootwijk.zip`, but those archive bytes were not exposed to the execution filesystem used for this build. It was therefore **not** silently accepted, hashed, extracted, or treated as authority.

To continue without compounding trust, this release independently reconstructed a literal-only handoff from the verified V0.4.1 archive. The handoff pins 47 literal/implementation authority files and excludes all generated evidence. Its identity is:

```text
sha256:3d2b46cfd33ba6e5cf0a13697fb59e374a64ad30450fdd3c256c98a04ebc474b
```

This is an explicit replacement boundary, not a claim that the inaccessible uploaded ZIP was byte-identical.
