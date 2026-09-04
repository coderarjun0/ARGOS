"""Definition of the ToolExecutorAdapter class.

This module provides the adapter bridging frozen ADS-004 ActionExecutor step invocations
to real BaseTool execution instances.
"""

from argos.execution.action_executor import ActionExecutor
from argos.execution.step_result import StepResult
from argos.planning.plan_step import PlanStep
from argos.tools.base_tool import BaseTool
from argos.tools.exceptions import InvalidParameterError, ToolError


class ToolExecutorAdapter(ActionExecutor):
    """Concrete ActionExecutor implementation wrapping a real BaseTool instance.

    Adapts the frozen ActionExecutor contract (execute(step: PlanStep) -> StepResult)
    to the underlying BaseTool execution interface without performing policy decisions.
    """

    def __init__(self, tool: BaseTool) -> None:
        """Initializes ToolExecutorAdapter with an injected BaseTool.

        Args:
            tool: Concrete BaseTool instance to delegate execution to.
        """
        self._tool = tool

    @property
    def tool(self) -> BaseTool:
        """Public access to underlying BaseTool instance."""
        return self._tool

    def execute(self, step: PlanStep) -> StepResult:
        """Executes a PlanStep by delegating to the wrapped BaseTool instance.

        Args:
            step: The PlanStep target carrying parameters.

        Returns:
            A StepResult converted from the underlying ToolResult.
        """
        try:
            self._tool.validate_parameters(step.parameters)
            tool_result = self._tool.run(step.parameters)
            return StepResult(
                step_id=step.step_id,
                action=step.action,
                success=tool_result.success,
                message=tool_result.message,
                metadata=tool_result.metadata,
            )
        except InvalidParameterError as err:
            return StepResult(
                step_id=step.step_id,
                action=step.action,
                success=False,
                message=f"Parameter validation failed: {err}",
            )
        except ToolError as err:
            return StepResult(
                step_id=step.step_id,
                action=step.action,
                success=False,
                message=f"Tool execution error: {err}",
            )
        except Exception as err:
            return StepResult(
                step_id=step.step_id,
                action=step.action,
                success=False,
                message=f"Unexpected error during tool execution: {err}",
            )
