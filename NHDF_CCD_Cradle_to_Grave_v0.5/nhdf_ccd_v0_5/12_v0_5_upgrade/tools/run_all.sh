#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
python -m unittest discover -s tests -v
python benchmarks/run_validation.py
python tools/fuzz_parser.py
python examples/feature_ccd_demo.py > validation/example_certificates.jsonl
printf 'v0.5 validation complete\n'
