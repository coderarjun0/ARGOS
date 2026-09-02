"""Observer component for the ARGOS Brain Core subsystem.

Receives capability outputs, updates Working Memory, compares expected outcomes
against actual results, and flags discrepancies in compliance with ADS-005 Section 7.5.
"""

from dataclasses import dataclass, field
from typing import Any

from argos.brain.constants import (
    CAPABILITY_EXECUTION,
    CAPABILITY_INPUT,
    CAPABILITY_INTENT,
    CAPABILITY_PLANNING,
)
from argos.brain.working_memory import WorkingMemory
from argos.execution.execution_result import ExecutionResult
from argos.execution.execution_status import ExecutionStatus
from argos.input.parsed_request import ParsedRequest
from argos.intent.intent_result import IntentResult
from argos.planning.plan import Plan


@dataclass(slots=True)
class ObservationResult:
    """Represents the observation of a capability output.

    Attributes:
        capability_name: The name of the capability that produced the output.
        success: Whether the capability execution produced a normal outcome.
        discrepancy_detected: Whether the output deviated from expectations.
        re_reasoning_required: Whether the discrepancy warrants re-reasoning.
        details: Telemetry and metadata extracted during observation.
    """

    capability_name: str
    success: bool = True
    discrepancy_detected: bool = False
    re_reasoning_required: bool = False
    details: dict[str, Any] = field(default_factory=dict)


class Observer:
    """Lightweight component observing and recording capability outcomes.

    The Observer functions strictly as a reporter and updater of cognitive state.
    It does not own decision logic or plan actions.
    """

    def observe(
        self,
        capability_name: str,
        output: Any,
        working_memory: WorkingMemory,
    ) -> ObservationResult:
        """Observes capability output, updates working memory, and checks discrepancies.

        Args:
            capability_name: Identifier of the capability that completed execution.
            output: The output object produced by the capability.
            working_memory: Transient Working Memory instance to update.

        Returns:
            An ObservationResult recording the observation.
        """
        success: bool = True
        discrepancy_detected: bool = False
        re_reasoning_required: bool = False
        details: dict[str, Any] = {}

        if capability_name == CAPABILITY_INPUT:
            if isinstance(output, ParsedRequest):
                working_memory.parsed_request = output
            details["source"] = getattr(output, "source", "unknown")

        elif capability_name == CAPABILITY_INTENT:
            if isinstance(output, IntentResult):
                working_memory.intent_result = output
                details["intent"] = output.primary_intent.value
                details["confidence"] = output.confidence

        elif capability_name == CAPABILITY_PLANNING:
            if isinstance(output, Plan):
                working_memory.plan = output
                details["steps_count"] = len(output.steps)
                details["requires_confirmation"] = output.requires_confirmation

        elif capability_name == CAPABILITY_EXECUTION:
            if isinstance(output, ExecutionResult):
                working_memory.execution_result = output
                details["status"] = output.status.value
                details["steps_count"] = len(output.step_results)

                if output.status == ExecutionStatus.FAILED:
                    success = False
                    discrepancy_detected = True
                    re_reasoning_required = True
                elif output.status == ExecutionStatus.PARTIAL_SUCCESS:
                    success = True
                    discrepancy_detected = True
                    re_reasoning_required = True
                else:
                    success = True
                    discrepancy_detected = False
                    re_reasoning_required = False

        obs = ObservationResult(
            capability_name=capability_name,
            success=success,
            discrepancy_detected=discrepancy_detected,
            re_reasoning_required=re_reasoning_required,
            details=details,
        )
        working_memory.record_observation(obs)
        return obs
