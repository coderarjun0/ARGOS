"""Definition of the StepResult dataclass.

This module provides the dataclass container representing the execution outcome of
an individual step in the plan.
"""

from dataclasses import dataclass, field
from typing import Any

from argos.planning.action import Action


@dataclass(slots=True)
class StepResult:
    """Represents the execution outcome of a single step.

    Attributes:
        step_id: Unique sequence identifier for the step.
        action: The action type of the step.
        success: True if execution succeeded, False otherwise.
        message: Diagnostic text or confirmation message.
        metadata: Context metrics or payloads.
    """

    step_id: int
    action: Action
    success: bool
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
