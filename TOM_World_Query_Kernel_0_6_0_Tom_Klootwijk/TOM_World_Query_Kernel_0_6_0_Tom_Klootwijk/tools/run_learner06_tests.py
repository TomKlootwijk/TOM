from __future__ import annotations

"""Run the complete unittest suite and write a timing-free deterministic log."""

import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation/learner06/tests.txt"


def canonicalize_test_output(raw: str) -> str:
    """Remove host-only paths/timing and force a stable LF transcript."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(str(ROOT), "<PACKAGE_ROOT>")
    text = re.sub(r"Ran (\d+) tests? in [0-9.]+s", r"Ran \1 tests", text)
    text = re.sub(r"/tmp/[A-Za-z0-9_.\-/]+", "<TEMP_PATH>", text)
    return "\n".join(text.splitlines()) + "\n"


def main() -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src/python")
    # Warning rendering includes interpreter-version-specific source context.
    # Suppress it before unittest starts so the evidence transcript contains
    # only test results rather than host diagnostics.
    env["PYTHONWARNINGS"] = "ignore"
    proc = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    text = canonicalize_test_output(proc.stdout)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    print(text, end="")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
