"""Definition of the ExecutionResult dataclass.

This module provides the dataclass container representing the aggregated execution
outcomes of a plan.
"""

from dataclasses import dataclass, field
from typing import Any

from argos.execution.constants import DEFAULT_EXECUTION_ENGINE
from argos.execution.execution_status import ExecutionStatus
from argos.execution.step_result import StepResult


@dataclass(slots=True)
class ExecutionResult:
    """Represents the compiled results of an execution run.

    Attributes:
        status: The overall success status (SUCCESS, PARTIAL_SUCCESS, FAILED).
        step_results: List of individual step results collected.
        execution_engine: The engine that executed the plan.
        metadata: Pipeline benchmarking metadata.
    """

    status: ExecutionStatus
    step_results: list[StepResult] = field(default_factory=list)
    execution_engine: str = DEFAULT_EXECUTION_ENGINE
    metadata: dict[str, Any] = field(default_factory=dict)
