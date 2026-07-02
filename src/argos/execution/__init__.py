"""Public API boundary for the ARGOS Execution subsystem.

This module exposes only the components intended for public consumption by other
subsystems (e.g., the Brain Core). All internal helper modules (executors, routers,
aggregators) remain encapsulated.
"""

from argos.execution.exceptions import (
    ExecutionError,
    ExecutorError,
    InvalidPlanError,
    InvalidStepError,
    ProcessingError,
    RoutingError,
    ValidationError,
)
from argos.execution.execution_engine import ExecutionEngine
from argos.execution.execution_result import ExecutionResult
from argos.execution.execution_status import ExecutionStatus
from argos.execution.step_result import StepResult

__all__ = [
    "ExecutionEngine",
    "ExecutionResult",
    "ExecutionStatus",
    "StepResult",
    "ExecutionError",
    "ValidationError",
    "InvalidPlanError",
    "InvalidStepError",
    "RoutingError",
    "ExecutorError",
    "ProcessingError",
]
