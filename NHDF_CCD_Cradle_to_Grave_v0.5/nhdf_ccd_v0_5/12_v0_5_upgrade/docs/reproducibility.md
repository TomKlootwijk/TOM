# Reproducibility record

All generated benchmark values originate from `benchmarks/run_validation.py`. The script uses fixed seeds and writes raw per-query CSV records before producing the JSON summary and figures. The environment is captured in `validation/environment.json`. The final package manifest hashes every regular file other than the manifest itself.

Third-party corpus data is included locally to avoid network dependence during replay. The upstream README and MIT license are preserved. No external query result is manually relabeled.

Reference throughput is host-specific and is reported only as an environment-bound measurement, not a portable performance guarantee.
