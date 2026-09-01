from __future__ import annotations

import json

from nhdf_ccd import Body, LinearMotion, Plane, Sphere, StaticMotion, Vec3, detect_pair


def main() -> None:
    bullet = Body("bullet", Sphere(0.25), LinearMotion(Vec3(0.0, 3.0, 0.0), Vec3(0.0, -20.0, 0.0)))
    floor = Body("floor", Plane(Vec3(0.0, 1.0, 0.0)), StaticMotion())
    result = detect_pair(bullet, floor)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
