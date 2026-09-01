from __future__ import annotations
import json
import sys
from pathlib import Path

def canonical_digest(path: Path) -> str:
    import hashlib
    payload=json.loads(path.read_text())
    text=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest()

if __name__ == "__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: replay_certificate.py record.json")
    print(canonical_digest(Path(sys.argv[1])))
