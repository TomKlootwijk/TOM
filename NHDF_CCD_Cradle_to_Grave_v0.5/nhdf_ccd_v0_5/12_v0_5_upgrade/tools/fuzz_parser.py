from __future__ import annotations
import random
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nhdf_ccd_v05.corpus import load_sample_queries

rng=random.Random(505)
rejected=0
with tempfile.TemporaryDirectory() as td:
    for i in range(500):
        rows=[]
        for _ in range(rng.randint(0,12)):
            cols=[str(rng.randint(-10,10)) for _ in range(rng.randint(0,9))]
            rows.append(",".join(cols))
        p=Path(td)/f"f{i}.csv"
        p.write_text("\n".join(rows)+"\n")
        try:
            load_sample_queries(p,rng.choice(["vertex-face","edge-edge"]))
        except (ValueError,ZeroDivisionError):
            rejected += 1
print({"cases":500,"rejected_malformed":rejected})
