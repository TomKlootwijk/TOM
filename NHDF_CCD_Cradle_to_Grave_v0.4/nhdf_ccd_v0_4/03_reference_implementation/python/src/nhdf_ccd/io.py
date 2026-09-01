from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .motion import LinearMotion, QuadraticMotion, StaticMotion
from .shapes import AxisAlignedBox, Body, Plane, PointShape, Sphere
from .vector import Vec3


def _vec(values: list[float]) -> Vec3:
    return Vec3.from_iterable(values)


def body_from_dict(data: dict[str, Any]) -> Body:
    shape_data = data["shape"]
    kind = shape_data["kind"]
    if kind == "sphere":
        shape = Sphere(float(shape_data["radius"]))
    elif kind == "aabb":
        shape = AxisAlignedBox(_vec(shape_data["half_extents"]))
    elif kind == "plane":
        shape = Plane(_vec(shape_data["normal"]), float(shape_data.get("offset", 0.0)))
    elif kind == "point":
        shape = PointShape()
    else:
        raise ValueError(f"unsupported serialized shape kind: {kind}")

    motion_data = data["motion"]
    motion_kind = motion_data["kind"]
    origin = _vec(motion_data.get("origin", [0.0, 0.0, 0.0]))
    if motion_kind == "static":
        motion = StaticMotion(origin)
    elif motion_kind == "linear":
        motion = LinearMotion(origin, _vec(motion_data["velocity"]))
    elif motion_kind == "quadratic":
        motion = QuadraticMotion(origin, _vec(motion_data["velocity"]), _vec(motion_data["acceleration"]))
    else:
        raise ValueError(f"unsupported motion kind: {motion_kind}")
    return Body(str(data["id"]), shape, motion)


def load_scene(path: str | Path) -> list[Body]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [body_from_dict(item) for item in payload["bodies"]]
