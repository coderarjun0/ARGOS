"""Definition of the ActionExecutor Abstract Base Class (ABC).

This module defines the execution contract interface implemented by all concrete
action executors.
"""

from abc import ABC, abstractmethod

from argos.execution.step_result import StepResult
from argos.planning.plan_step import PlanStep


class ActionExecutor(ABC):
    """Abstract interface defining the execution protocol."""

    @abstractmethod
    def execute(self, step: PlanStep) -> StepResult:
        """Executes a single plan step and returns its outcome.

        Args:
            step: The PlanStep object containing action name and parameters.

        Returns:
            A StepResult containing execution status.
        """
