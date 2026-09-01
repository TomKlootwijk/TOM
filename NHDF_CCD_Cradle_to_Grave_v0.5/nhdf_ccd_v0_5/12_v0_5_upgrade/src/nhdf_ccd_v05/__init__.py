"""NHDF-CCD v0.5: bounded, auditable feature-level CCD reference code."""
from .model import Vec3, LinearPoint, Status, Certificate, Witness
from .ccd import vertex_face_ccd, edge_edge_ccd, sphere_sphere_ccd
from .events import group_contact_events, ContactEvent
from .rigid import relative_speed_bound, rotational_margin, RigidMotionBound

__all__ = [
    "Vec3", "LinearPoint", "Status", "Certificate", "Witness",
    "vertex_face_ccd", "edge_edge_ccd", "sphere_sphere_ccd",
    "group_contact_events", "ContactEvent",
    "relative_speed_bound", "rotational_margin", "RigidMotionBound",
]
__version__ = "0.5.0"
