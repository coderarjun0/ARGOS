"""Definition of the WebExecutor class.

This module provides mock implementations of web-related execution steps,
such as web searches.
"""

from argos.execution.action_executor import ActionExecutor
from argos.execution.exceptions import InvalidStepError
from argos.execution.step_result import StepResult
from argos.planning.action import Action
from argos.planning.plan_step import PlanStep


class WebExecutor(ActionExecutor):
    """Executes web action steps in simulated mode."""

    def execute(self, step: PlanStep) -> StepResult:
        """Simulates executing web searches.

        Args:
            step: The PlanStep target.

        Returns:
            A StepResult containing simulated confirmation messages.

        Raises:
            InvalidStepError: If step action is unmapped or parameters are missing.
        """
        if step.action != Action.SEARCH_WEB:
            raise InvalidStepError(
                f"WebExecutor cannot execute action: {step.action}"
            )

        query = (
            step.parameters.get("query")
            or step.parameters.get("url")
            or step.parameters.get("website")
        )
        if not query:
            raise InvalidStepError(
                "Missing required 'query', 'url', or 'website' parameter "
                "for web search action."
            )

        return StepResult(
            step_id=step.step_id,
            action=step.action,
            success=True,
            message=f"Web search for '{query}' executed successfully (simulated).",
        )
