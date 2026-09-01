#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT/03_reference_implementation/python/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
pytest -q -p no:cacheprovider
python 05_benchmarks/generate_reference_vectors.py
python 05_benchmarks/run_benchmarks.py
cmake -S 03_reference_implementation/cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp -j2
ctest --test-dir build/cpp --output-on-failure
bash scripts/build_report.sh
python scripts/package_check.py
