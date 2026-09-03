"""TOM Learner 0.1 reference API / World & Query Kernel 0.5.1.

This host package is the independent reference oracle and evidence-store API.
The corrected learner authority is the seeded formal TOMAGI definition graph.
"""
from .learner import LearningRun, learn_observation_set
from .model import ObservationSet
from .store import LearnerStore

__all__ = ["LearningRun", "ObservationSet", "LearnerStore", "learn_observation_set"]
__version__ = "0.5.1"
