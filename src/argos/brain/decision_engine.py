"""Decision engine for the ARGOS Brain Core subsystem.

Performs deterministic cognitive decision-making, evaluating Working Memory to determine
capability transitions, clarification needs, user confirmations, and termination status
in compliance with ADS-005 Section 7.3 and Section 12.
"""

from argos.brain.brain_status import BrainStatus
from argos.brain.constants import (
    CAPABILITY_EXECUTION,
    CAPABILITY_INPUT,
    CAPABILITY_INTENT,
    CAPABILITY_PLANNING,
    CLARIFICATION_CONFIDENCE_THRESHOLD,
    CONFIRMATION_CONFIDENCE_THRESHOLD,
)
from argos.brain.working_memory import WorkingMemory
from argos.execution.execution_status import ExecutionStatus
from argos.intent.intent import Intent
from argos.planning.action import Action


class DecisionEngine:
    """Evaluates cognitive state and makes deterministic reasoning decisions.

    The DecisionEngine is strictly an evaluator and reasoning component.
    It does not orchestrate loops, invoke capabilities, or mutate execution state.
    """

    def decide_goal_name(self, working_memory: WorkingMemory) -> str:
        """Derives the session goal name from current working memory state.

        Args:
            working_memory: The active WorkingMemory instance.

        Returns:
            A descriptive goal name string.
        """
        if working_memory.intent_result is not None:
            intent = working_memory.intent_result.primary_intent
            if intent == Intent.UNKNOWN:
                return "CLARIFY_USER_INTENT"
            return f"EXECUTE_{intent.name}"
        return "PROCESS_USER_INPUT"

    def evaluate_clarification_needed(self, working_memory: WorkingMemory) -> bool:
        """Evaluates whether the user's intent requires clarification.

        Args:
            working_memory: The active WorkingMemory instance.

        Returns:
            True if intent is UNKNOWN or confidence falls below threshold.
        """
        if working_memory.intent_result is None:
            return False

        intent = working_memory.intent_result.primary_intent
        confidence = working_memory.intent_result.confidence

        return (
            intent == Intent.UNKNOWN
            or confidence < CLARIFICATION_CONFIDENCE_THRESHOLD
        )

    def evaluate_confirmation_needed(self, working_memory: WorkingMemory) -> bool:
        """Evaluates whether user confirmation is required before execution.

        Args:
            working_memory: The active WorkingMemory instance.

        Returns:
            True if the plan or intent indicates user confirmation is mandatory.
        """
        if working_memory.plan is not None:
            return working_memory.plan.requires_confirmation

        if working_memory.intent_result is not None:
            conf = working_memory.intent_result.confidence
            is_in_range = (
                CLARIFICATION_CONFIDENCE_THRESHOLD
                <= conf
                < CONFIRMATION_CONFIDENCE_THRESHOLD
            )
            return is_in_range

        return False

    def decide_next_capability(self, working_memory: WorkingMemory) -> str | None:
        """Determines the next capability to invoke based on working memory state.

        Args:
            working_memory: The active WorkingMemory instance.

        Returns:
            Capability name string, or None if reasoning should pause or terminate.
        """
        if working_memory.parsed_request is None:
            return CAPABILITY_INPUT

        if working_memory.intent_result is None:
            return CAPABILITY_INTENT

        # Check if a non-pipeline capability execution is requested in working memory
        pending_cap = working_memory.get_context("pending_capability")
        if (
            pending_cap
            and isinstance(pending_cap, str)
            and pending_cap.strip()
            and not working_memory.get_context("pending_capability_executed")
        ):
            return pending_cap.strip()

        if working_memory.plan is None:
            return CAPABILITY_PLANNING

        # If confirmation is required, pause before execution
        if self.evaluate_confirmation_needed(working_memory):
            return None

        if working_memory.execution_result is None:
            return CAPABILITY_EXECUTION

        return None

    def decide_terminal_status(self, working_memory: WorkingMemory) -> BrainStatus:
        """Resolves the final BrainStatus for the session.

        Args:
            working_memory: The active WorkingMemory instance.

        Returns:
            The appropriate BrainStatus enum value.
        """
        # If user confirmation was required and execution did not run
        if (
            self.evaluate_confirmation_needed(working_memory)
            and working_memory.execution_result is None
        ):
            return BrainStatus.WAITING_FOR_USER

        # If execution occurred, evaluate outcomes
        if working_memory.execution_result is not None:
            status = working_memory.execution_result.status
            if status == ExecutionStatus.FAILED:
                return BrainStatus.FAILED

            # Check if any executed step was a clarification request
            has_clarification_step = any(
                sr.action == Action.ASK_CLARIFICATION
                for sr in working_memory.execution_result.step_results
            )
            if has_clarification_step:
                return BrainStatus.WAITING_FOR_USER

            return BrainStatus.COMPLETED

        # If plan has an explicit clarification step
        if working_memory.plan is not None and any(
            step.action == Action.ASK_CLARIFICATION
            for step in working_memory.plan.steps
        ):
            return BrainStatus.WAITING_FOR_USER

        return BrainStatus.COMPLETED

    def should_continue_reasoning(self, working_memory: WorkingMemory) -> bool:
        """Determines whether another cognitive loop cycle should execute.

        Args:
            working_memory: The active WorkingMemory instance.

        Returns:
            True if further capability execution is required, False otherwise.
        """
        next_cap = self.decide_next_capability(working_memory)
        return next_cap is not None
