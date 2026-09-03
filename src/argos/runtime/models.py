"""Runtime models and data transfer objects for ARGOS."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from argos.brain.brain_result import BrainResult


class RuntimeStatus(StrEnum):
    """High-level execution status returned by ArgosRuntime."""

    SUCCESS = "success"
    MALFORMED_INPUT = "malformed_input"
    INTENT_UNRESOLVED = "intent_unresolved"
    PLANNING_FAILED = "planning_failed"
    POLICY_DENIED = "policy_denied"
    WAITING_FOR_USER = "waiting_for_user"
    EXECUTION_FAILED = "execution_failed"
    MAX_CYCLES_EXCEEDED = "max_cycles_exceeded"
    SYSTEM_ERROR = "system_error"
    SHUTDOWN = "shutdown"


@dataclass(slots=True)
class RuntimeResponse:
    """External DTO summarizing the outcome of a runtime request invocation.

    Attributes:
        status: High-level status enum of the runtime operation.
        session_id: Session identifier string for the request.
        output: Human-readable message or execution result summary.
        brain_result: Underlying BrainResult compiled outcome container.
        error_message: Optional error message string if execution failed.
        metadata: Optional metadata dictionary.
    """

    status: RuntimeStatus
    session_id: str
    output: str = ""
    brain_result: BrainResult | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
