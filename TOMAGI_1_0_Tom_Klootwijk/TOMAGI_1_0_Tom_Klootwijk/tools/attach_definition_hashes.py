from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))
from tomagi.canonical import attach_hash

p=Path(sys.argv[1])
d=json.loads(p.read_text(encoding='utf-8'))
d['definitions']=[attach_hash(x) for x in d.get('definitions',[])]
p.write_bytes((json.dumps(d,indent=2,ensure_ascii=False)+"\n").encode('utf-8'))
