"""Definition of the PlanStep dataclass.

This module provides the dataclass container representing a single atomic step
within a system plan.
"""

from dataclasses import dataclass, field
from typing import Any

from argos.planning.action import Action


@dataclass(slots=True)
class PlanStep:
    """Represents a single step in a plan.

    Attributes:
        step_id: Unique sequence identifier for the step (1-indexed).
        action: The atomic action to be performed.
        parameters: Configuration key-value parameters required for the action.
    """

    step_id: int
    action: Action
    parameters: dict[str, Any] = field(default_factory=dict)
