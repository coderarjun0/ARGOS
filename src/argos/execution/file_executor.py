"""Definition of the FileExecutor class.

This module provides mock implementations of file-related execution steps,
such as reading, writing, creating, and deleting files.
"""

from argos.execution.action_executor import ActionExecutor
from argos.execution.exceptions import InvalidStepError
from argos.execution.step_result import StepResult
from argos.planning.action import Action
from argos.planning.plan_step import PlanStep


class FileExecutor(ActionExecutor):
    """Executes file action steps in simulated mode."""

    def execute(self, step: PlanStep) -> StepResult:
        """Simulates executing file operations.

        Args:
            step: The PlanStep target.

        Returns:
            A StepResult containing simulated confirmation messages.

        Raises:
            InvalidStepError: If step action is unmapped or parameters are missing.
        """
        valid_actions = (
            Action.CREATE_FILE,
            Action.READ_FILE,
            Action.WRITE_FILE,
            Action.DELETE_FILE,
        )
        if step.action not in valid_actions:
            raise InvalidStepError(
                f"FileExecutor cannot execute action: {step.action}"
            )

        if step.action == Action.DELETE_FILE:
            target = step.parameters.get("target") or step.parameters.get(
                "file_path"
            )
            if not target:
                raise InvalidStepError(
                    "Missing required 'target' or 'file_path' parameter "
                    "for file delete action."
                )
            msg = f"File/folder '{target}' deleted successfully (simulated)."
        else:
            file_path = step.parameters.get("file_path")
            if not file_path:
                raise InvalidStepError(
                    f"Missing required 'file_path' parameter for action: {step.action}"
                )
            msg = (
                f"File operation '{step.action}' on '{file_path}' "
                "succeeded (simulated)."
            )

        return StepResult(
            step_id=step.step_id,
            action=step.action,
            success=True,
            message=msg,
        )
