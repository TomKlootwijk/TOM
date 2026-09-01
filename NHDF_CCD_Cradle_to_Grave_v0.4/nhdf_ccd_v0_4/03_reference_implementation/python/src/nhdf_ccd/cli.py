from __future__ import annotations

import argparse
import json

from .engine import detect_scene
from .io import load_scene
from .types import CCDConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NHDF-CCD reference engine on a JSON scene")
    parser.add_argument("scene")
    parser.add_argument("--distance-tolerance", type=float, default=1e-8)
    parser.add_argument("--max-candidates", type=int, default=100_000)
    args = parser.parse_args()
    config = CCDConfig(distance_tolerance=args.distance_tolerance, max_candidates=args.max_candidates)
    result = detect_scene(load_scene(args.scene), config)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
