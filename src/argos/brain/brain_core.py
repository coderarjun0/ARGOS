"""Brain Core facade orchestrator for the ARGOS Cognitive Operating System.

Coordinates the Cognitive Loop (Perceive -> Understand -> Reason -> Decide -> Act
-> Observe -> Reflect -> Repeat), managing working memory, goals, decisions, and
pluggable capabilities in compliance with ADS-005 and ADS-006.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from argos.brain.brain_result import BrainResult
from argos.brain.brain_status import BrainStatus, CognitiveState
from argos.brain.capability_manager import (
    CAPABILITY_EXECUTION,
    CAPABILITY_INPUT,
    CAPABILITY_INTENT,
    CAPABILITY_PLANNING,
    CapabilityManager,
    create_default_capability_manager,
)
from argos.brain.constants import (
    CAPABILITY_MEMORY,
    DEFAULT_BRAIN_ENGINE,
    DEFAULT_MAX_COGNITIVE_CYCLES,
)
from argos.brain.decision_engine import DecisionEngine
from argos.brain.exceptions import (
    MaxCyclesExceededError,
    ValidationError,
)
from argos.brain.goal_manager import GoalManager
from argos.brain.observer import Observer
from argos.brain.working_memory import WorkingMemory
from argos.execution.execution_engine import ExecutionEngine
from argos.execution.execution_status import ExecutionStatus
from argos.input.input_request import InputRequest
from argos.input.processor import InputProcessor
from argos.intent.analyzer import IntentAnalyzer
from argos.memory.constants import DEFAULT_SESSION_ID
from argos.memory.models import AuthorizationRecord, SessionTurn
from argos.planning.planner import Planner

logger = logging.getLogger(__name__)


class BrainCore:
    """Public facade orchestrator for the ARGOS Brain Core.

    Owns and coordinates the cognitive lifecycle, executing reasoning loops
    and driving capability invocation without coupling to details.
    """

    def __init__(
        self,
        capability_manager: CapabilityManager | None = None,
        decision_engine: DecisionEngine | None = None,
        goal_manager: GoalManager | None = None,
        observer: Observer | None = None,
        working_memory: WorkingMemory | None = None,
        input_processor: InputProcessor | None = None,
        intent_analyzer: IntentAnalyzer | None = None,
        planner: Planner | None = None,
        execution_engine: ExecutionEngine | None = None,
        max_cycles: int = DEFAULT_MAX_COGNITIVE_CYCLES,
        brain_engine: str = DEFAULT_BRAIN_ENGINE,
    ) -> None:
        """Initializes the BrainCore with optional dependency injection.

        Args:
            capability_manager: Optional custom CapabilityManager.
            decision_engine: Optional custom DecisionEngine.
            goal_manager: Optional custom GoalManager.
            observer: Optional custom Observer.
            working_memory: Optional custom WorkingMemory.
            input_processor: Optional custom InputProcessor for default capabilities.
            intent_analyzer: Optional custom IntentAnalyzer for default capabilities.
            planner: Optional custom Planner for default capabilities.
            execution_engine: Optional custom ExecutionEngine for default capabilities.
            max_cycles: Maximum cognitive loop iterations before halting.
            brain_engine: Engine identifier string.

        Raises:
            ValidationError: If max_cycles or brain_engine parameters are invalid.
        """
        if not isinstance(max_cycles, int) or max_cycles < 1:
            raise ValidationError("max_cycles must be a positive integer.")
        if not isinstance(brain_engine, str) or not brain_engine.strip():
            raise ValidationError("brain_engine must be a non-empty string.")

        self._max_cycles = max_cycles
        self._brain_engine = brain_engine.strip()
        self._capability_manager = (
            capability_manager
            or create_default_capability_manager(
                input_processor=input_processor,
                intent_analyzer=intent_analyzer,
                planner=planner,
                execution_engine=execution_engine,
            )
        )
        self._decision_engine = decision_engine or DecisionEngine()
        self._goal_manager = goal_manager or GoalManager()
        self._observer = observer or Observer()
        self._working_memory = working_memory or WorkingMemory()

    @property
    def brain_engine(self) -> str:
        """Returns the identifier of this BrainCore engine."""
        return self._brain_engine

    @property
    def capability_manager(self) -> CapabilityManager:
        """Returns the registered CapabilityManager instance."""
        return self._capability_manager

    @property
    def decision_engine(self) -> DecisionEngine:
        """Returns the active DecisionEngine instance."""
        return self._decision_engine

    @property
    def goal_manager(self) -> GoalManager:
        """Returns the active GoalManager instance."""
        return self._goal_manager

    @property
    def observer(self) -> Observer:
        """Returns the active Observer instance."""
        return self._observer

    @property
    def working_memory(self) -> WorkingMemory:
        """Returns the active WorkingMemory instance."""
        return self._working_memory

    def process(
        self,
        request: InputRequest | str,
        authorization: AuthorizationRecord | None = None,
        session_id: str = DEFAULT_SESSION_ID,
        context: dict[str, Any] | None = None,
    ) -> BrainResult:
        """Executes the complete cognitive loop for a user request.

        Performs the cognitive reasoning lifecycle:
        Perceive -> Understand -> Reason -> Decide -> Act -> Observe -> Reflect.

        Args:
            request: An InputRequest instance or a raw text string.
            authorization: Optional user authorization record for memory operations.
            session_id: Session identifier string.
            context: Optional initial context key-value pairs for WorkingMemory.

        Returns:
            A compiled BrainResult container.

        Raises:
            ValidationError: If request validation fails.
            ProcessingError: If capability invocation or boundary operations fail.
            MaxCyclesExceededError: If the cognitive cycle limit is exceeded.
        """
        normalized_request = self._validate_and_normalize_request(request)
        wm = self._working_memory

        # Reset working memory unless resuming WAITING_FOR_USER with auth
        if (
            wm.cognitive_state != CognitiveState.WAITING_FOR_USER
            or authorization is None
        ):
            wm.reset()

        if context:
            for k, v in context.items():
                wm.set_context(k, v)

        wm.raw_input = normalized_request

        logger.debug("Cognitive session initialized.")

        while True:
            if wm.cycle_count >= self._max_cycles:
                logger.error("Maximum cognitive cycles limit exceeded.")
                raise MaxCyclesExceededError(
                    f"Cognitive loop exceeded limit of {self._max_cycles} cycles."
                )

            wm.increment_cycle()

            # 1. PERCEIVE
            self._transition(CognitiveState.PERCEIVING)
            if wm.parsed_request is None:
                parsed = self._capability_manager.execute(
                    CAPABILITY_INPUT, wm.raw_input
                )
                self._observer.observe(CAPABILITY_INPUT, parsed, wm)
                wm.record_decision("Perceived and parsed raw input.")

            # 2. UNDERSTAND
            self._transition(CognitiveState.INTERPRETING)
            if wm.intent_result is None:
                intent_res = self._capability_manager.execute(
                    CAPABILITY_INTENT, wm.parsed_request
                )
                self._observer.observe(CAPABILITY_INTENT, intent_res, wm)
                wm.record_decision("Interpreted semantic intent.")

            # 3. REASON
            self._transition(CognitiveState.REASONING)
            goal_name = self._decision_engine.decide_goal_name(wm)
            goal = self._goal_manager.create_goal(name=goal_name)
            wm.active_goal_id = goal.goal_id
            wm.active_goal_name = goal.name
            logger.info("Active Goal resolved: %s", goal.name)
            wm.record_decision(f"Reasoned active goal: {goal.name}")

            # Explicit Session Memory Recall Request (if requested in context)
            if (
                wm.get_context("recall_session_memory")
                and not wm.get_context("session_turns")
                and not wm.get_context("pending_capability_executed")
            ):
                wm.set_context("pending_capability", CAPABILITY_MEMORY)
                wm.set_context("pending_capability_action", "get_session_turns")
                wm.set_context(
                    "pending_capability_kwargs", {"session_id": session_id}
                )

            # Explicit Persistent Record Retrieval Request (if requested in context)
            cat = wm.get_context("memory_category")
            key = wm.get_context("memory_key")
            if (
                cat
                and key
                and not wm.get_context("retrieved_memory")
                and not wm.get_context("pending_capability_executed")
            ):
                wm.set_context("pending_capability", CAPABILITY_MEMORY)
                wm.set_context("pending_capability_action", "get_exact")
                wm.set_context(
                    "pending_capability_kwargs", {"category": cat, "key": key}
                )

            # Persistent Memory Mutation Request Staging
            pending_mutation = wm.get_context("pending_memory_mutation")
            if pending_mutation and not wm.get_context(
                "pending_capability_executed"
            ):
                op = pending_mutation.get("operation", "store_persistent")
                p_cat = pending_mutation["category"]
                p_key = pending_mutation["key"]
                p_kwargs = {"category": p_cat, "key": p_key}
                if op == "update_persistent":
                    p_kwargs["new_value"] = pending_mutation.get("value")
                elif op == "store_persistent":
                    p_kwargs["value"] = pending_mutation.get("value")

                wm.set_context("pending_capability", CAPABILITY_MEMORY)
                wm.set_context("pending_capability_action", op)
                wm.set_context("pending_capability_kwargs", p_kwargs)
                wm.set_context("pending_capability_requires_consent", True)

            # Check if clarification is needed
            if self._decision_engine.evaluate_clarification_needed(wm):
                wm.record_decision(
                    "Clarification required due to low confidence or unknown intent."
                )

            # 4. DECIDE
            next_cap = self._decision_engine.decide_next_capability(wm)

            # Check if confirmation is required before planning or execution
            confirmation_needed = (
                self._decision_engine.evaluate_confirmation_needed(wm)
            )
            if next_cap is None and confirmation_needed:
                self._transition(CognitiveState.WAITING_FOR_USER)
                wm.record_decision("Paused execution awaiting user confirmation.")
                break

            # Handle non-pipeline generic capability dispatch (Memory, Policy, Tools)
            if (
                next_cap
                and next_cap
                not in (
                    CAPABILITY_INPUT,
                    CAPABILITY_INTENT,
                    CAPABILITY_PLANNING,
                    CAPABILITY_EXECUTION,
                )
                and self._capability_manager.has(next_cap)
            ):
                action = wm.get_context("pending_capability_action")
                args = wm.get_context("pending_capability_args") or ()
                kwargs = dict(wm.get_context("pending_capability_kwargs") or {})
                requires_consent = wm.get_context(
                    "pending_capability_requires_consent"
                )

                if requires_consent:
                    if authorization is None:
                        self._transition(CognitiveState.WAITING_FOR_USER)
                        wm.record_decision(
                            "Paused execution awaiting explicit user consent."
                        )
                        break

                    if not authorization.granted:
                        wm.record_decision(
                            "User denied memory consent. Persistent mutation aborted."
                        )
                        wm.set_context("pending_capability_executed", True)
                        active_goal = self._goal_manager.get_active_goal()
                        if active_goal:
                            self._goal_manager.complete_goal(active_goal.goal_id)
                        break

                    kwargs["authorization"] = authorization

                try:
                    res = self._capability_manager.execute(
                        next_cap, action, *args, **kwargs
                    )
                    if action == "get_session_turns":
                        wm.set_context("session_turns", res)
                    elif action == "get_exact":
                        wm.set_context("retrieved_memory", res)
                    elif action in ("store_persistent", "update_persistent"):
                        wm.set_context("committed_memory", res)
                    elif action == "delete_persistent":
                        wm.set_context("deleted_memory", res)
                    else:
                        wm.set_context(f"{next_cap}_result", res)

                    wm.record_decision(
                        f"Executed capability '{next_cap}' with action '{action}'."
                    )
                    active_goal = self._goal_manager.get_active_goal()
                    if active_goal and requires_consent:
                        self._goal_manager.complete_goal(active_goal.goal_id)
                except Exception as err:
                    if action in ("get_session_turns", "get_exact"):
                        logger.debug("Optional memory recall skipped: %s", err)
                    else:
                        logger.error(
                            "Capability '%s' execution failed: %s", next_cap, err
                        )
                        raise

                wm.set_context("pending_capability_executed", True)
                if requires_consent:
                    break

            # 5. ACT & OBSERVE (PLANNING)
            if next_cap == CAPABILITY_PLANNING:
                self._transition(CognitiveState.PLANNING)
                plan = self._capability_manager.execute(
                    CAPABILITY_PLANNING, wm.intent_result
                )
                self._observer.observe(CAPABILITY_PLANNING, plan, wm)
                wm.record_decision("Assembled action plan from intent.")

                # Check if newly generated plan mandates confirmation
                if self._decision_engine.evaluate_confirmation_needed(wm):
                    self._transition(CognitiveState.WAITING_FOR_USER)
                    wm.record_decision("Plan mandates explicit user confirmation.")
                    break

                # Progress decision to next capability (e.g. execution)
                next_cap = self._decision_engine.decide_next_capability(wm)

            # 6. ACT & OBSERVE (EXECUTION)
            if next_cap == CAPABILITY_EXECUTION:
                self._transition(CognitiveState.EXECUTING)
                exec_result = self._capability_manager.execute(
                    CAPABILITY_EXECUTION, wm.plan
                )
                self._observer.observe(CAPABILITY_EXECUTION, exec_result, wm)
                wm.record_decision(
                    f"Executed action plan with status: {exec_result.status.value}"
                )

            # 7. REFLECT (EVALUATING)
            self._transition(CognitiveState.EVALUATING)
            self._reflect_and_update_goals(wm)

            # 8. REPEAT OR TERMINATE
            if not self._decision_engine.should_continue_reasoning(wm):
                break

        # Record session turn in SessionStore if Memory capability is present
        if self._capability_manager.has(CAPABILITY_MEMORY):
            try:
                turn = SessionTurn(
                    turn_id=wm.cycle_count,
                    session_id=session_id,
                    user_input=wm.raw_input.raw_text if wm.raw_input else "",
                    normalized_text=(
                        wm.parsed_request.normalized_text
                        if wm.parsed_request
                        else ""
                    ),
                    intent_name=(
                        wm.intent_result.primary_intent.name
                        if wm.intent_result
                        else None
                    ),
                    plan_summary=(
                        wm.plan.steps[0].action.value
                        if (wm.plan and wm.plan.steps)
                        else None
                    ),
                    execution_status=(
                        wm.execution_result.status.value
                        if wm.execution_result
                        else None
                    ),
                    timestamp=datetime.now(UTC),
                )
                self._capability_manager.execute(
                    CAPABILITY_MEMORY, "record_turn", turn
                )
            except Exception as err:
                logger.debug("Session turn recording skipped: %s", err)

        return self._compile_result(wm)

    def _validate_and_normalize_request(
        self,
        request: Any,
    ) -> InputRequest:
        """Validates and normalizes user input into an InputRequest instance."""
        if isinstance(request, str):
            clean_text = request.strip()
            if not clean_text:
                msg = "Input string cannot be empty or whitespace only."
                raise ValidationError(msg)
            return InputRequest(
                raw_text=clean_text,
                source="cli",
                timestamp=datetime.now(UTC),
            )

        if isinstance(request, InputRequest):
            if not isinstance(request.raw_text, str) or not request.raw_text.strip():
                raise ValidationError(
                    "InputRequest raw_text must be a non-empty string."
                )
            return request

        raise ValidationError(
            f"Input must be an InputRequest or str, got {type(request).__name__}."
        )

    def _transition(self, new_state: CognitiveState) -> None:
        """Transitions working memory state and logs lifecycle event."""
        self._working_memory.transition_to(new_state)
        logger.info("Brain Core transitioned to state: %s", new_state.value)

    def _reflect_and_update_goals(self, wm: WorkingMemory) -> None:
        """Evaluates goal completion status based on execution outcomes."""
        active_goal = self._goal_manager.get_active_goal()
        if not active_goal:
            return

        if wm.execution_result is not None:
            status = wm.execution_result.status
            if status == ExecutionStatus.SUCCESS:
                self._goal_manager.complete_goal(active_goal.goal_id)
                wm.record_decision("Goal completed successfully.")
            elif status == ExecutionStatus.FAILED:
                self._goal_manager.fail_goal(
                    active_goal.goal_id, reason="Execution failed"
                )
                wm.record_decision("Goal failed due to execution error.")
            elif status == ExecutionStatus.PARTIAL_SUCCESS:
                self._goal_manager.complete_goal(active_goal.goal_id)
                wm.record_decision("Goal completed with partial execution success.")

    def _compile_result(self, wm: WorkingMemory) -> BrainResult:
        """Compiles the final BrainResult and sets the terminal status."""
        if wm.cognitive_state == CognitiveState.WAITING_FOR_USER:
            brain_status = BrainStatus.WAITING_FOR_USER
        else:
            brain_status = self._decision_engine.decide_terminal_status(wm)

        if brain_status == BrainStatus.COMPLETED:
            self._transition(CognitiveState.COMPLETED)
            logger.info("Cognitive loop completed successfully.")
        elif brain_status == BrainStatus.FAILED:
            self._transition(CognitiveState.FAILED)
            logger.info("Cognitive loop terminated with failure.")
        elif brain_status == BrainStatus.WAITING_FOR_USER:
            self._transition(CognitiveState.WAITING_FOR_USER)
            logger.info("Cognitive loop paused waiting for user.")
        else:
            self._transition(CognitiveState.TERMINATED)
            logger.info("Cognitive loop terminated.")

        final_goal_name = wm.active_goal_name or "unknown"

        return BrainResult(
            parsed_request=wm.parsed_request,
            intent_result=wm.intent_result,
            plan=wm.plan,
            execution_result=wm.execution_result,
            decision_history=list(wm.decision_history),
            final_goal=final_goal_name,
            brain_status=brain_status,
            brain_engine=self._brain_engine,
            metadata={"cycle_count": wm.cycle_count},
        )
