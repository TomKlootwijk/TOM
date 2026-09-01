"""NHDF-CCD semantics-first reference package."""

from .engine import detect_pair, detect_scene
from .motion import LinearMotion, QuadraticMotion, StaticMotion
from .shapes import AxisAlignedBox, Body, ImplicitSDF, Plane, PointShape, Sphere
from .types import CCDConfig, CCDStatus, CollisionCertificate, SceneResult
from .vector import Vec3

__all__ = [
    "AxisAlignedBox",
    "Body",
    "CCDConfig",
    "CCDStatus",
    "CollisionCertificate",
    "ImplicitSDF",
    "LinearMotion",
    "Plane",
    "PointShape",
    "QuadraticMotion",
    "SceneResult",
    "Sphere",
    "StaticMotion",
    "Vec3",
    "detect_pair",
    "detect_scene",
]
