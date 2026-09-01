from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "RELEASE_NOTES.md",
    "LICENSE.txt",
    "NHDF_CCD_Cradle_to_Grave_v0.4.pdf",
    "CRADLE_TO_GRAVE_ROADMAP.yaml",
    "RISK_REGISTER.csv",
    "TRACEABILITY_MATRIX.csv",
    "02_formal_specification/scene.schema.json",
    "02_formal_specification/certificate.schema.json",
    "03_reference_implementation/python/src/nhdf_ccd/engine.py",
    "04_verification/VERIFICATION_REPORT.md",
    "05_benchmarks/benchmark_summary.json",
    "10_domain_adapters/adapter_matrix.csv",
    "11_report/generate_report_assets.py",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        print("missing required files:", *missing, sep="\n - ", file=sys.stderr)
        return 1
    benchmark = json.loads((ROOT / "05_benchmarks/benchmark_summary.json").read_text(encoding="utf-8"))
    if benchmark["ca_false_negatives"] != 0:
        print("benchmark contains false negatives", file=sys.stderr)
        return 2
    entries = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and "build" not in p.parts and p.name != "SHA256SUMS.txt"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(entries) + "\n", encoding="utf-8")
    print(f"package check passed; hashed {len(entries)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
