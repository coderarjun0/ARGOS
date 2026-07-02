"""Definition of the SystemExecutor class.

This module provides mock implementations of system execution steps,
such as running terminal commands.
"""

from argos.execution.action_executor import ActionExecutor
from argos.execution.exceptions import InvalidStepError
from argos.execution.step_result import StepResult
from argos.planning.action import Action
from argos.planning.plan_step import PlanStep


class SystemExecutor(ActionExecutor):
    """Executes system command steps in simulated mode."""

    def execute(self, step: PlanStep) -> StepResult:
        """Simulates running terminal commands.

        Args:
            step: The PlanStep target.

        Returns:
            A StepResult containing simulated confirmation messages.

        Raises:
            InvalidStepError: If step action is unmapped or parameters are missing.
        """
        if step.action != Action.RUN_COMMAND:
            raise InvalidStepError(
                f"SystemExecutor cannot execute action: {step.action}"
            )

        cmd = step.parameters.get("command")
        if not cmd:
            raise InvalidStepError(
                "Missing required 'command' parameter for system action."
            )

        return StepResult(
            step_id=step.step_id,
            action=step.action,
            success=True,
            message=f"Command '{cmd}' executed successfully (simulated).",
        )
