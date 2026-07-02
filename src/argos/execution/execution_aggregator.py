"""Definition of the ExecutionAggregator class.

This module provides the result aggregation logic to compile step execution
outcomes into a unified ExecutionStatus.
"""

from argos.execution.execution_status import ExecutionStatus
from argos.execution.step_result import StepResult


class ExecutionAggregator:
    """Aggregates StepResult collection outcomes into a final status."""

    def aggregate(self, step_results: list[StepResult]) -> ExecutionStatus:
        """Determines the overall execution status from step results.

        Args:
            step_results: A list of StepResult objects.

        Returns:
            An ExecutionStatus (SUCCESS, PARTIAL_SUCCESS, FAILED).
        """
        if not step_results:
            return ExecutionStatus.SUCCESS

        total_steps = len(step_results)
        successful_steps = sum(1 for r in step_results if r.success)

        if successful_steps == total_steps:
            return ExecutionStatus.SUCCESS
        if successful_steps == 0:
            return ExecutionStatus.FAILED

        return ExecutionStatus.PARTIAL_SUCCESS
