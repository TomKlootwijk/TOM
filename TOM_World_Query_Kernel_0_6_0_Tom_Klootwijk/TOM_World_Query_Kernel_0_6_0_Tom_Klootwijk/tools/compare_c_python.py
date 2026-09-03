from __future__ import annotations
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compare_c_python.py PYTHON_RESULT.json C_STATE.json", file=sys.stderr)
        return 2
    py = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    c = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    expected = py.get("state", py)
    if expected != c:
        print(json.dumps({"expected": expected, "actual": c}, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps({"match": True, "fields": len(c)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
