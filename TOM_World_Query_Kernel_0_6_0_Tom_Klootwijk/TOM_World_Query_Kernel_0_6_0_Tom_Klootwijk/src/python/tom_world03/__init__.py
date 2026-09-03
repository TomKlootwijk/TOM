"""TOM World & Query Kernel 0.3 interval-event extension."""
from .baseline import trusted_affine_baseline
from .interval import ClosedInterval
from .model import AffineTrajectory, IntervalWorld, Relation
from .rational import Q
from .solver import certify_crossing, certified_events, events_certificate, next_event_set
from .transitions import TransitionConflict, apply_event_set, merge_transition_ops

__all__ = [
    "Q", "ClosedInterval", "AffineTrajectory", "IntervalWorld", "Relation",
    "certify_crossing", "certified_events", "events_certificate", "next_event_set",
    "apply_event_set", "merge_transition_ops", "TransitionConflict",
    "trusted_affine_baseline",
]
__version__ = "0.3.0"
