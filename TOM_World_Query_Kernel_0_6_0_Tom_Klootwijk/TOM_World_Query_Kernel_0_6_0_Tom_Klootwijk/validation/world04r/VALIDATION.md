# TOM World & Query Kernel 0.4.1 corrective validation

Status: **pass**

This validation excludes the superseded 0.4.0 line. It begins at the pinned corrected 0.3 archive and verifies every inherited critical source hash.

- Corrected 0.3 archive: `a7103ec92596fd54198e4a902f078712cf8eafcdf1e45320bbdc02dd53947278`
- Corrected interval implementation: `ea7b3ff2127e8ee7a696eb45e84ae9efdbca7c10c532617c51888fb13cd39f6d`
- Tests: `172` passed
- Validation checks: `20` passed, `0` failed
- Semantic chain: `sha256:9fd4f3e1ae8550ae3ca99e27e7bf61b22a4935fe764fd443723abfdb3804f226`
- Clean replay boundaries: `24` equal
- Validation content hash: `sha256:9df2b1f8983e13c47568bb4d862b1de30c605d200b6652d498a81795b16c21df`

The realized segment ends are solver-produced exact event times. No authoritative relation contains `continuation_until`.
