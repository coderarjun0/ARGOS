"""Definition of the ApplicationExecutor class.

This module provides mock implementations of application-related execution steps,
such as launching and closing apps.
"""

from argos.execution.action_executor import ActionExecutor
from argos.execution.exceptions import InvalidStepError
from argos.execution.step_result import StepResult
from argos.planning.action import Action
from argos.planning.plan_step import PlanStep


class ApplicationExecutor(ActionExecutor):
    """Executes application action steps in simulated mode."""

    def execute(self, step: PlanStep) -> StepResult:
        """Simulates launching or closing an application.

        Args:
            step: The PlanStep target.

        Returns:
            A StepResult containing simulated confirmation messages.

        Raises:
            InvalidStepError: If step action is unmapped or parameters are missing.
        """
        if step.action not in (Action.OPEN_APP, Action.CLOSE_APP):
            raise InvalidStepError(
                f"ApplicationExecutor cannot execute action: {step.action}"
            )

        app = step.parameters.get("application")
        if not app:
            raise InvalidStepError(
                "Missing required 'application' parameter for application action."
            )

        if step.action == Action.OPEN_APP:
            msg = f"Application '{app}' launched successfully (simulated)."
        else:
            msg = f"Application '{app}' closed successfully (simulated)."

        return StepResult(
            step_id=step.step_id,
            action=step.action,
            success=True,
            message=msg,
        )
