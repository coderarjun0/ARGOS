"""Public API boundary for the ARGOS Brain Core subsystem.

This module exposes only the components intended for public consumption by external
clients and applications. All internal helper modules (GoalManager, WorkingMemory,
DecisionEngine, CapabilityManager, Observer) remain encapsulated.
"""

from argos.brain.brain_core import BrainCore
from argos.brain.brain_result import BrainResult
from argos.brain.brain_status import BrainStatus
from argos.brain.exceptions import (
    BrainError,
    ProcessingError,
    ValidationError,
)

__all__ = [
    "BrainCore",
    "BrainResult",
    "BrainStatus",
    "BrainError",
    "ValidationError",
    "ProcessingError",
]
