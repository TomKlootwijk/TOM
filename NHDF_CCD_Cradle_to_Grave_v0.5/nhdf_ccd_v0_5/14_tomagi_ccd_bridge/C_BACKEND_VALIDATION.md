# Independent C-backend replay

Status: **PASS**

The portable C99 backend from the pinned Genesis archive was compiled under
WSL and run independently against `ccd_vf_q4.tmg`.

```bash
cc -std=c99 -O2 -Wall -Wextra -Wpedantic -Isrc/c \
  src/c/tomagi.c src/c/tomagi_cli.c -o build/tomagi-c
./build/tomagi-c <bridge>/ccd_vf_q4.tmg \
  --trace-json ccd_vf_q4.c_trace.json \
  --materialize ccd_vf_q4.certificate.c.json
```

| Boundary | Result |
|---|---:|
| Input `.tmg` | 9,392 bytes; SHA-256 `09cd3a2e311adb84391ec25762ecab2b63147861e7f8ab64f4fddce63568c900` |
| Materialized certificate | 378 bytes; SHA-256 `035a9ee91654675326e9b603990048395324855db560cfd54c797ad2da087a2b` |
| State64 final words | 16/16 equal to Python |
| Trace records | 110/110 equal across all 17 fields |
| EMIT records | 95/95 equal across all 8 fields |

Final state:

```text
rho=0 theta=1 tick=3 phi=1
vrho=-1 vtheta=0 vtick=1 vphi=0
orientation=0 sheet=0 branch=1 cell=104
lineage=4244936959 output=2685 residual=0 status=57
```

The C trace JSON is 60,760 bytes with SHA-256
`b18cb935aa4f9271c4dec24ede5a5ab3c066dadcd9fde98af2aab8e31f8b8367`.
It differs bytewise from the Python replay because the two CLIs format and
order JSON properties differently. Parsed state, trace, and EMIT values are
equal. The environment-specific compiled C binary and temporary replay files
are intentionally not delivered.
