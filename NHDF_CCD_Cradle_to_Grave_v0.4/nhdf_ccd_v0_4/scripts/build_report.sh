#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="$ROOT/11_report"
BASE="NHDF_CCD_Cradle_to_Grave_v0.4"
TEX="$BASE.tex"
OUT_REPORT="$REPORT/$BASE.pdf"
OUT_ROOT="$ROOT/$BASE.pdf"
BUILD="$(mktemp -d /tmp/nhdf-ccd-latex.XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT

# Keep report tables and figures synchronized with the latest benchmark.
python "$REPORT/generate_report_assets.py"

cd "$REPORT"
run_latex() {
  local pass="$1"
  local log="$BUILD/pdflatex-pass-$pass.stdout"
  if ! pdflatex \
      -interaction=nonstopmode \
      -halt-on-error \
      -file-line-error \
      -recorder \
      -output-directory="$BUILD" \
      "$TEX" >"$log" 2>&1; then
    echo "pdflatex pass $pass failed" >&2
    tail -120 "$log" >&2
    exit 1
  fi
}

# First pass creates the .bcf. Biber resolves citations. Three further passes
# settle citations, long tables, contents, figure lists, and hyperlinks.
run_latex 1
if ! (
  cd "$BUILD"
  BIBINPUTS="$REPORT:" biber "$BASE" >"$BUILD/biber.stdout" 2>&1
); then
  echo "biber failed" >&2
  tail -120 "$BUILD/biber.stdout" >&2
  exit 1
fi
run_latex 2
run_latex 3
run_latex 4

FINAL_LOG="$BUILD/$BASE.log"
if grep -Eq 'LaTeX Error|Package .* Error|Citation .* undefined|Reference .* undefined|There were undefined references' "$FINAL_LOG"; then
  echo "final LaTeX pass contains unresolved errors or references" >&2
  grep -E 'LaTeX Error|Package .* Error|Citation .* undefined|Reference .* undefined|There were undefined references' "$FINAL_LOG" >&2 || true
  exit 1
fi

cp "$BUILD/$BASE.pdf" "$OUT_REPORT"
cp "$FINAL_LOG" "$REPORT/build_report.log"
cp "$BUILD/$BASE.pdf" "$OUT_ROOT"
printf 'report built: %s\nroot copy: %s\n' "$OUT_REPORT" "$OUT_ROOT"
