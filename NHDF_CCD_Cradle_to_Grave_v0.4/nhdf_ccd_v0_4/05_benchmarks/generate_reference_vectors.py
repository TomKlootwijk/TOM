from __future__ import annotations

import json
from pathlib import Path

from nhdf_ccd import AxisAlignedBox, Body, CCDConfig, LinearMotion, Plane, Sphere, StaticMotion, Vec3, detect_pair

ROOT = Path(__file__).resolve().parent


def cases() -> list[tuple[str, Body, Body]]:
    return [
        (
            "sphere_sphere_tunneling",
            Body("target", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0))),
            Body("bullet", Sphere(1.0), LinearMotion(Vec3(-10.0, 0.0, 0.0), Vec3(20.0, 0.0, 0.0))),
        ),
        (
            "sphere_plane_fast",
            Body("sphere", Sphere(1.0), LinearMotion(Vec3(0.0, 10.0, 0.0), Vec3(0.0, -100.0, 0.0))),
            Body("plane", Plane(Vec3(0.0, 1.0, 0.0)), StaticMotion()),
        ),
        (
            "aabb_crossing",
            Body("box_a", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), StaticMotion(Vec3(0.0, 0.0, 0.0))),
            Body("box_b", AxisAlignedBox(Vec3(1.0, 1.0, 1.0)), LinearMotion(Vec3(-5.0, 0.0, 0.0), Vec3(10.0, 0.0, 0.0))),
        ),
        (
            "sphere_sphere_no_hit",
            Body("a", Sphere(1.0), StaticMotion(Vec3(0.0, 0.0, 0.0))),
            Body("b", Sphere(1.0), LinearMotion(Vec3(10.0, 0.0, 0.0), Vec3(0.0, 5.0, 0.0))),
        ),
    ]


def main() -> None:
    config = CCDConfig()
    payload = []
    for name, a, b in cases():
        payload.append({"name": name, "certificate": detect_pair(a, b, config).to_dict()})
    (ROOT / "reference_vectors.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {len(payload)} reference vectors")


if __name__ == "__main__":
    main()
