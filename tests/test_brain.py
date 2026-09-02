"""Comprehensive unit tests for the ARGOS Brain Core subsystem (ADS-005).

Verifies 100% statement coverage, lifecycle transitions, deterministic reasoning,
subsystem integration, capability wrapping, exception handling, and encapsulation.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

import argos.brain
from argos.brain import (
    BrainCore,
    BrainError,
    BrainResult,
    BrainStatus,
    ProcessingError,
    ValidationError,
)
from argos.brain.brain_status import CognitiveState
from argos.brain.capability_manager import (
    CAPABILITY_EXECUTION,
    CAPABILITY_INPUT,
    CAPABILITY_INTENT,
    CAPABILITY_PLANNING,
    CapabilityManager,
    CognitiveCapability,
    ExecutionCapability,
    InputCapability,
    IntentCapability,
    PlanningCapability,
    create_default_capability_manager,
)
from argos.brain.constants import (
    CLARIFICATION_CONFIDENCE_THRESHOLD,
    CONFIRMATION_CONFIDENCE_THRESHOLD,
    DEFAULT_BRAIN_ENGINE,
    DEFAULT_MAX_COGNITIVE_CYCLES,
    MAX_GOALS_TRACKED,
)
from argos.brain.decision_engine import DecisionEngine
from argos.brain.exceptions import (
    CapabilityNotFoundError,
    MaxCyclesExceededError,
)
from argos.brain.goal_manager import Goal, GoalManager, GoalStatus
from argos.brain.observer import Observer
from argos.brain.working_memory import WorkingMemory
from argos.execution.execution_engine import ExecutionEngine
from argos.execution.execution_result import ExecutionResult
from argos.execution.execution_status import ExecutionStatus
from argos.execution.step_result import StepResult
from argos.input.input_request import InputRequest
from argos.input.parsed_request import ParsedRequest
from argos.input.processor import InputProcessor
from argos.intent.analyzer import IntentAnalyzer
from argos.intent.intent import Intent
from argos.intent.intent_result import IntentResult
from argos.planning.action import Action
from argos.planning.plan import Plan
from argos.planning.plan_step import PlanStep
from argos.planning.planner import Planner

# =====================================================================
# Public Boundary & Encapsulation Tests
# =====================================================================


def test_brain_public_api_boundary() -> None:
    """Verifies that argos.brain exports only the specified public API."""
    expected_exports = {
        "BrainCore",
        "BrainResult",
        "BrainStatus",
        "BrainError",
        "ValidationError",
        "ProcessingError",
    }
    assert set(argos.brain.__all__) == expected_exports

    # Ensure internal components are encapsulated
    assert "WorkingMemory" not in argos.brain.__all__
    assert "GoalManager" not in argos.brain.__all__
    assert "DecisionEngine" not in argos.brain.__all__
    assert "CapabilityManager" not in argos.brain.__all__
    assert "Observer" not in argos.brain.__all__


# =====================================================================
# Constants & Enums Tests
# =====================================================================


def test_constants_values() -> None:
    """Verifies that subsystem constants match specified defaults."""
    assert DEFAULT_BRAIN_ENGINE == "argos-brain-v1"
    assert DEFAULT_MAX_COGNITIVE_CYCLES == 10
    assert CONFIRMATION_CONFIDENCE_THRESHOLD == 0.80
    assert CLARIFICATION_CONFIDENCE_THRESHOLD == 0.60
    assert MAX_GOALS_TRACKED == 50
    assert CAPABILITY_INPUT == "input_processing"
    assert CAPABILITY_INTENT == "intent_analysis"
    assert CAPABILITY_PLANNING == "planning"
    assert CAPABILITY_EXECUTION == "execution"


def test_brain_status_enum() -> None:
    """Verifies BrainStatus values and string behavior."""
    assert BrainStatus.IDLE == "IDLE"
    assert BrainStatus.RUNNING == "RUNNING"
    assert BrainStatus.WAITING_FOR_USER == "WAITING_FOR_USER"
    assert BrainStatus.COMPLETED == "COMPLETED"
    assert BrainStatus.FAILED == "FAILED"
    assert BrainStatus.TERMINATED == "TERMINATED"
    assert isinstance(BrainStatus.COMPLETED, str)


def test_cognitive_state_enum() -> None:
    """Verifies CognitiveState values and string behavior."""
    states = {
        "IDLE",
        "PERCEIVING",
        "INTERPRETING",
        "REASONING",
        "PLANNING",
        "EXECUTING",
        "EVALUATING",
        "WAITING_FOR_USER",
        "COMPLETED",
        "FAILED",
        "TERMINATED",
    }
    actual = {s.value for s in CognitiveState}
    assert actual == states


# =====================================================================
# Exceptions Hierarchy Tests
# =====================================================================


def test_exception_hierarchy() -> None:
    """Verifies inheritance relations across the custom exception hierarchy."""
    assert issubclass(ValidationError, BrainError)
    assert issubclass(ProcessingError, BrainError)
    assert issubclass(CapabilityNotFoundError, ValidationError)
    assert issubclass(MaxCyclesExceededError, ProcessingError)


# =====================================================================
# BrainResult Dataclass Tests
# =====================================================================


def test_brain_result_defaults_and_slots() -> None:
    """Verifies BrainResult initialization and slot immutability constraints."""
    result = BrainResult()
    assert result.parsed_request is None
    assert result.intent_result is None
    assert result.plan is None
    assert result.execution_result is None
    assert result.decision_history == []
    assert result.final_goal == "unknown"
    assert result.brain_status == BrainStatus.IDLE
    assert result.brain_engine == DEFAULT_BRAIN_ENGINE
    assert result.metadata == {}

    # Verify slots prevent arbitrary attribute assignment
    with pytest.raises(AttributeError):
        result.non_existent_attribute = 123  # type: ignore[attr-defined]


# =====================================================================
# WorkingMemory Tests
# =====================================================================


def test_working_memory_operations() -> None:
    """Verifies WorkingMemory state transitions, decisions, and resets."""
    wm = WorkingMemory()
    assert wm.cognitive_state == CognitiveState.IDLE
    assert wm.cycle_count == 0

    wm.transition_to(CognitiveState.PERCEIVING)
    assert wm.cognitive_state == CognitiveState.PERCEIVING

    assert wm.increment_cycle() == 1
    assert wm.cycle_count == 1

    wm.record_decision("Decision 1")
    assert wm.decision_history == ["Decision 1"]

    wm.record_observation("Observation 1")
    assert wm.observations == ["Observation 1"]

    wm.set_context("key1", "val1")
    assert wm.get_context("key1") == "val1"
    assert wm.get_context("missing", "default") == "default"

    wm.reset()
    assert wm.cognitive_state == CognitiveState.IDLE
    assert wm.cycle_count == 0
    assert wm.decision_history == []
    assert wm.observations == []
    assert wm.context == {}

    # Verify slots
    with pytest.raises(AttributeError):
        wm.arbitrary_attr = "error"  # type: ignore[attr-defined]


# =====================================================================
# GoalManager Tests
# =====================================================================


def test_goal_manager_lifecycle() -> None:
    """Verifies creation, prioritization, completion, and failure of goals."""
    gm = GoalManager()
    assert gm.get_active_goal() is None
    assert not gm.has_active_goals()

    # Create first goal - automatically becomes active
    g1 = gm.create_goal("Test Goal 1", priority=1)
    assert g1.goal_id == "goal-1"
    assert g1.name == "Test Goal 1"
    assert g1.status == GoalStatus.ACTIVE
    assert gm.get_active_goal() == g1
    assert gm.has_active_goals()

    # Create second goal - status remains PENDING
    g2 = gm.create_goal("Test Goal 2", priority=5)
    assert g2.status == GoalStatus.PENDING

    # List goals
    all_goals = gm.list_goals()
    assert len(all_goals) == 2

    # Get goal
    assert gm.get_goal("goal-1") == g1
    assert gm.get_goal("non-existent") is None

    # Reprioritize goal
    gm.reprioritize_goal("goal-1", 10)
    assert g1.priority == 10

    # Explicitly activate goal 2
    gm.set_active_goal("goal-2")
    assert gm.get_active_goal() == g2
    assert g1.status == GoalStatus.PENDING
    assert g2.status == GoalStatus.ACTIVE

    # Complete active goal
    gm.complete_goal("goal-2")
    assert g2.status == GoalStatus.COMPLETED
    # Next get_active_goal should fall back to pending goal 1
    assert gm.get_active_goal() == g1

    # Fail goal
    gm.fail_goal("goal-1", reason="Network timeout")
    assert g1.status == GoalStatus.FAILED
    assert g1.metadata["failure_reason"] == "Network timeout"
    assert gm.get_active_goal() is None

    # Cancel goal
    g3 = gm.create_goal("Test Goal 3")
    gm.cancel_goal("goal-3")
    assert g3.status == GoalStatus.CANCELLED

    # Clear
    gm.clear()
    assert len(gm.list_goals()) == 0


def test_goal_manager_validations() -> None:
    """Verifies GoalManager input validation errors."""
    gm = GoalManager()

    with pytest.raises(ValidationError, match="non-empty string"):
        gm.create_goal("")

    with pytest.raises(ValidationError, match="non-negative integer"):
        gm.create_goal("Valid", priority=-1)

    with pytest.raises(ValidationError, match="untracked goal"):
        gm.set_active_goal("unknown")

    with pytest.raises(ValidationError, match="untracked goal"):
        gm.reprioritize_goal("unknown", 5)

    with pytest.raises(ValidationError, match="non-negative integer"):
        g = gm.create_goal("Valid")
        gm.reprioritize_goal(g.goal_id, -2)

    with pytest.raises(ValidationError, match="untracked goal"):
        gm.complete_goal("unknown")

    with pytest.raises(ValidationError, match="untracked goal"):
        gm.fail_goal("unknown")

    with pytest.raises(ValidationError, match="untracked goal"):
        gm.cancel_goal("unknown")


# =====================================================================
# CapabilityManager & Adapters Tests
# =====================================================================


class DummyCustomCapability(CognitiveCapability):
    """Custom capability for registry testing."""

    def __init__(self, name: str = "custom") -> None:
        """Initializes custom capability with a name."""
        self._name = name

    @property
    def name(self) -> str:
        """Returns capability name."""
        return self._name

    def execute(self, *args: object, **kwargs: object) -> str:
        """Executes custom test logic."""
        return "custom_output"


def test_capability_adapters_and_manager() -> None:
    """Verifies standard subsystem adapters and manager execution wrapping."""
    mgr = create_default_capability_manager()
    assert mgr.has(CAPABILITY_INPUT)
    assert mgr.has(CAPABILITY_INTENT)
    assert mgr.has(CAPABILITY_PLANNING)
    assert mgr.has(CAPABILITY_EXECUTION)
    assert len(mgr.list_capabilities()) == 4

    # Direct execution through adapters
    input_req = InputRequest(
        raw_text="open browser",
        source="cli",
        timestamp=datetime.now(UTC),
    )
    parsed = mgr.execute(CAPABILITY_INPUT, input_req)
    assert isinstance(parsed, ParsedRequest)

    intent_res = mgr.execute(CAPABILITY_INTENT, parsed)
    assert isinstance(intent_res, IntentResult)

    plan = mgr.execute(CAPABILITY_PLANNING, intent_res)
    assert isinstance(plan, Plan)

    exec_res = mgr.execute(CAPABILITY_EXECUTION, plan)
    assert isinstance(exec_res, ExecutionResult)


def test_capability_manager_validations_and_errors() -> None:
    """Verifies capability registration boundaries and error translation."""
    mgr = CapabilityManager()

    # Validation errors on registration
    with pytest.raises(ValidationError, match="must implement CognitiveCapability"):
        mgr.register("not_a_capability")  # type: ignore[arg-type]

    custom = DummyCustomCapability("test_cap")
    mgr.register(custom)

    with pytest.raises(ValidationError, match="already registered"):
        mgr.register(custom)

    class EmptyNameCap(CognitiveCapability):
        @property
        def name(self) -> str:
            return ""

        def execute(self, *args: object, **kwargs: object) -> None:
            pass

    with pytest.raises(ValidationError, match="non-empty string"):
        mgr.register(EmptyNameCap())

    # CapabilityNotFoundError
    with pytest.raises(CapabilityNotFoundError, match="is not registered"):
        mgr.get("missing_cap")

    with pytest.raises(CapabilityNotFoundError, match="is not registered"):
        mgr.execute("missing_cap")

    # Error wrapping in execute
    class FailingCap(CognitiveCapability):
        @property
        def name(self) -> str:
            return "failing"

        def execute(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("Subsystem crash")

    mgr.register(FailingCap())
    with pytest.raises(ProcessingError, match="unexpected error"):
        mgr.execute("failing")


# =====================================================================
# Observer Tests
# =====================================================================


def test_observer_tracking_and_discrepancy() -> None:
    """Verifies Observer updates WorkingMemory and detects discrepancies."""
    obs = Observer()
    wm = WorkingMemory()

    # Input observation
    parsed = ParsedRequest(
        normalized_text="open notepad",
        tokens=["open", "notepad"],
        source="cli",
        timestamp=datetime.now(UTC),
    )
    r1 = obs.observe(CAPABILITY_INPUT, parsed, wm)
    assert wm.parsed_request == parsed
    assert r1.success is True
    assert r1.discrepancy_detected is False

    # Intent observation
    intent_res = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.95,
        analysis_engine="rule_engine",
        entities={"application": ["notepad"]},
        metadata={},
    )
    r2 = obs.observe(CAPABILITY_INTENT, intent_res, wm)
    assert wm.intent_result == intent_res
    assert r2.success is True

    # Planning observation
    plan = Plan(
        steps=[PlanStep(step_id=1, action=Action.OPEN_APP, parameters={})],
        requires_confirmation=False,
    )
    r3 = obs.observe(CAPABILITY_PLANNING, plan, wm)
    assert wm.plan == plan
    assert r3.success is True

    # Execution observation - SUCCESS
    exec_res_success = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.OPEN_APP,
                success=True,
                message="Opened",
            )
        ],
    )
    r4 = obs.observe(CAPABILITY_EXECUTION, exec_res_success, wm)
    assert wm.execution_result == exec_res_success
    assert r4.success is True
    assert r4.discrepancy_detected is False
    assert r4.re_reasoning_required is False

    # Execution observation - FAILED
    exec_res_failed = ExecutionResult(
        status=ExecutionStatus.FAILED,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.OPEN_APP,
                success=False,
                message="Failed",
            )
        ],
    )
    r5 = obs.observe(CAPABILITY_EXECUTION, exec_res_failed, wm)
    assert r5.success is False
    assert r5.discrepancy_detected is True
    assert r5.re_reasoning_required is True

    # Execution observation - PARTIAL_SUCCESS
    exec_res_partial = ExecutionResult(
        status=ExecutionStatus.PARTIAL_SUCCESS,
        step_results=[],
    )
    r6 = obs.observe(CAPABILITY_EXECUTION, exec_res_partial, wm)
    assert r6.success is True
    assert r6.discrepancy_detected is True
    assert r6.re_reasoning_required is True


# =====================================================================
# DecisionEngine Tests
# =====================================================================


def test_decision_engine_heuristics() -> None:
    """Verifies DecisionEngine heuristic evaluation and routing logic."""
    de = DecisionEngine()
    wm = WorkingMemory()

    # Goal naming
    assert de.decide_goal_name(wm) == "PROCESS_USER_INPUT"

    wm.intent_result = IntentResult(
        primary_intent=Intent.UNKNOWN,
        confidence=0.2,
        analysis_engine="rule_engine",
        entities={},
    )
    assert de.decide_goal_name(wm) == "CLARIFY_USER_INTENT"
    assert de.evaluate_clarification_needed(wm) is True

    wm.intent_result = IntentResult(
        primary_intent=Intent.SEARCH_WEB,
        confidence=0.9,
        analysis_engine="rule_engine",
        entities={},
    )
    assert de.decide_goal_name(wm) == "EXECUTE_SEARCH_WEB"
    assert de.evaluate_clarification_needed(wm) is False

    # Clarification needed when intent is None
    wm_empty = WorkingMemory()
    assert de.evaluate_clarification_needed(wm_empty) is False

    # Confirmation needed heuristics
    assert de.evaluate_confirmation_needed(wm_empty) is False

    wm_empty.intent_result = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.70,  # in [0.60, 0.80)
        analysis_engine="rule_engine",
        entities={},
    )
    assert de.evaluate_confirmation_needed(wm_empty) is True

    wm_empty.plan = Plan(steps=[], requires_confirmation=False)
    assert de.evaluate_confirmation_needed(wm_empty) is False

    wm_empty.plan.requires_confirmation = True
    assert de.evaluate_confirmation_needed(wm_empty) is True

    # Transition capability progression
    wm_cycle = WorkingMemory()
    assert de.decide_next_capability(wm_cycle) == CAPABILITY_INPUT

    wm_cycle.parsed_request = Mock(spec=ParsedRequest)
    assert de.decide_next_capability(wm_cycle) == CAPABILITY_INTENT

    wm_cycle.intent_result = Mock(spec=IntentResult)
    wm_cycle.intent_result.confidence = 0.95
    assert de.decide_next_capability(wm_cycle) == CAPABILITY_PLANNING

    wm_cycle.plan = Plan(steps=[], requires_confirmation=False)
    assert de.decide_next_capability(wm_cycle) == CAPABILITY_EXECUTION

    wm_cycle.plan.requires_confirmation = True
    assert de.decide_next_capability(wm_cycle) is None  # Pauses for confirmation

    wm_cycle.plan.requires_confirmation = False
    wm_cycle.execution_result = Mock(spec=ExecutionResult)
    assert de.decide_next_capability(wm_cycle) is None  # Finished


def test_decision_engine_terminal_statuses() -> None:
    """Verifies terminal BrainStatus resolution under various scenarios."""
    de = DecisionEngine()
    wm = WorkingMemory()

    # Default without execution
    assert de.decide_terminal_status(wm) == BrainStatus.COMPLETED

    # Plan with clarification step
    wm.plan = Plan(
        steps=[PlanStep(step_id=1, action=Action.ASK_CLARIFICATION, parameters={})],
        requires_confirmation=False,
    )
    assert de.decide_terminal_status(wm) == BrainStatus.WAITING_FOR_USER

    # Plan requiring confirmation without execution
    wm.plan = Plan(steps=[], requires_confirmation=True)
    assert de.decide_terminal_status(wm) == BrainStatus.WAITING_FOR_USER

    # Execution failed
    wm.execution_result = ExecutionResult(
        status=ExecutionStatus.FAILED,
        step_results=[],
    )
    assert de.decide_terminal_status(wm) == BrainStatus.FAILED

    # Execution with clarification step executed
    wm.execution_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.ASK_CLARIFICATION,
                success=True,
                message="Clarify?",
            )
        ],
    )
    assert de.decide_terminal_status(wm) == BrainStatus.WAITING_FOR_USER

    # Execution normal success
    wm.execution_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.OPEN_APP,
                success=True,
                message="Opened",
            )
        ],
    )
    assert de.decide_terminal_status(wm) == BrainStatus.COMPLETED


# =====================================================================
# BrainCore End-to-End & Lifecycle Tests
# =====================================================================


def test_brain_core_initialization_and_properties() -> None:
    """Verifies BrainCore constructor validation and exposed properties."""
    brain = BrainCore()
    assert brain.brain_engine == DEFAULT_BRAIN_ENGINE
    assert isinstance(brain.capability_manager, CapabilityManager)
    assert isinstance(brain.decision_engine, DecisionEngine)
    assert isinstance(brain.goal_manager, GoalManager)
    assert isinstance(brain.observer, Observer)
    assert isinstance(brain.working_memory, WorkingMemory)

    with pytest.raises(ValidationError, match="positive integer"):
        BrainCore(max_cycles=0)

    with pytest.raises(ValidationError, match="non-empty string"):
        BrainCore(brain_engine="")


def test_brain_core_process_happy_path() -> None:
    """Verifies standard cognitive cycle completing successfully."""
    brain = BrainCore()
    result = brain.process("open notepad")

    assert isinstance(result, BrainResult)
    assert result.brain_status == BrainStatus.COMPLETED
    assert result.final_goal == "EXECUTE_OPEN_APPLICATION"
    assert result.parsed_request is not None
    assert result.intent_result is not None
    assert result.plan is not None
    assert result.execution_result is not None
    assert result.execution_result.status == ExecutionStatus.SUCCESS
    assert len(result.decision_history) > 0
    assert result.metadata["cycle_count"] >= 1


def test_brain_core_process_with_input_request() -> None:
    """Verifies processing when an explicit InputRequest object is supplied."""
    brain = BrainCore()
    req = InputRequest(
        raw_text="search google.com",
        source="cli",
        timestamp=datetime.now(UTC),
    )
    result = brain.process(req)
    assert result.brain_status == BrainStatus.COMPLETED
    assert result.final_goal == "EXECUTE_SEARCH_WEB"


def test_brain_core_input_validations() -> None:
    """Verifies validation errors on malformed user inputs."""
    brain = BrainCore()

    with pytest.raises(ValidationError, match="Input must be an InputRequest or str"):
        brain.process(12345)  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="empty or whitespace"):
        brain.process("   ")

    invalid_req = InputRequest(
        raw_text="",
        source="cli",
        timestamp=datetime.now(UTC),
    )
    with pytest.raises(ValidationError, match="raw_text must be a non-empty string"):
        brain.process(invalid_req)


def test_brain_core_clarification_flow() -> None:
    """Verifies ambiguous intent triggers clarification and WAITING_FOR_USER."""
    brain = BrainCore()
    # "asdfghjk" produces UNKNOWN intent with 0.0 confidence
    result = brain.process("asdfghjk")

    assert result.brain_status == BrainStatus.WAITING_FOR_USER
    assert result.final_goal == "CLARIFY_USER_INTENT"
    assert result.plan is not None
    assert any(s.action == Action.ASK_CLARIFICATION for s in result.plan.steps)


def test_brain_core_confirmation_flow() -> None:
    """Verifies confirmation-mandated plan pauses at WAITING_FOR_USER."""
    # Mock Planner to return a plan requiring confirmation
    mock_planner = Mock(spec=Planner)
    plan_with_confirmation = Plan(
        steps=[PlanStep(step_id=1, action=Action.DELETE_FILE, parameters={})],
        requires_confirmation=True,
    )
    mock_planner.plan.return_value = plan_with_confirmation

    brain = BrainCore(planner=mock_planner)
    result = brain.process("delete file test.txt")

    assert result.brain_status == BrainStatus.WAITING_FOR_USER
    # Execution should not have taken place
    assert result.execution_result is None


def test_brain_core_execution_failure_flow() -> None:
    """Verifies that execution failure updates goal status to FAILED."""
    mock_engine = Mock(spec=ExecutionEngine)
    failed_result = ExecutionResult(
        status=ExecutionStatus.FAILED,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.OPEN_APP,
                success=False,
                message="Process crashed",
            )
        ],
    )
    mock_engine.execute.return_value = failed_result

    brain = BrainCore(execution_engine=mock_engine)
    result = brain.process("open calculator")

    assert result.brain_status == BrainStatus.FAILED
    assert result.execution_result == failed_result


def test_brain_core_execution_partial_success_flow() -> None:
    """Verifies partial execution outcome completes goal with partial success."""
    mock_engine = Mock(spec=ExecutionEngine)
    partial_result = ExecutionResult(
        status=ExecutionStatus.PARTIAL_SUCCESS,
        step_results=[],
    )
    mock_engine.execute.return_value = partial_result

    brain = BrainCore(execution_engine=mock_engine)
    result = brain.process("open calculator")

    assert result.brain_status == BrainStatus.COMPLETED
    assert result.execution_result == partial_result


def test_brain_core_subsystem_exception_translation() -> None:
    """Verifies low-level subsystem errors are wrapped in ProcessingError."""
    mock_processor = Mock(spec=InputProcessor)
    mock_processor.process.side_effect = RuntimeError("Encoding failure")

    brain = BrainCore(input_processor=mock_processor)
    with pytest.raises(ProcessingError, match="unexpected error"):
        brain.process("open browser")


def test_brain_core_max_cycles_safeguard() -> None:
    """Verifies infinite loop safeguard raises MaxCyclesExceededError."""
    # Custom DecisionEngine that perpetually requests planning without executing
    class InfiniteLoopDecisionEngine(DecisionEngine):
        def decide_next_capability(self, working_memory: WorkingMemory) -> str | None:
            return CAPABILITY_PLANNING

        def should_continue_reasoning(self, working_memory: WorkingMemory) -> bool:
            return True

    brain = BrainCore(
        decision_engine=InfiniteLoopDecisionEngine(),
        max_cycles=3,
    )

    with pytest.raises(MaxCyclesExceededError, match="limit of 3 cycles"):
        brain.process("open browser")


def test_brain_core_default_capability_adapters_direct() -> None:
    """Verifies default capability wrappers directly with custom components."""
    proc = InputProcessor()
    analyzer = IntentAnalyzer()
    planner = Planner()
    engine = ExecutionEngine()

    cap_input = InputCapability(proc)
    cap_intent = IntentCapability(analyzer)
    cap_plan = PlanningCapability(planner)
    cap_exec = ExecutionCapability(engine)

    assert cap_input.name == CAPABILITY_INPUT
    assert cap_intent.name == CAPABILITY_INTENT
    assert cap_plan.name == CAPABILITY_PLANNING
    assert cap_exec.name == CAPABILITY_EXECUTION


def test_capability_manager_subsystem_error_wrapping() -> None:
    """Verifies capability manager translates explicit subsystem errors."""
    from argos.input.exceptions import EmptyInputError

    mgr = CapabilityManager()

    class SubsystemFailingCap(CognitiveCapability):
        @property
        def name(self) -> str:
            return "subsystem_fail"

        def execute(self, *args: object, **kwargs: object) -> None:
            raise EmptyInputError("Empty text")

    mgr.register(SubsystemFailingCap())
    with pytest.raises(ProcessingError, match="subsystem error"):
        mgr.execute("subsystem_fail")


def test_brain_core_paused_awaiting_user_confirmation_at_decision_step() -> None:
    """Verifies BrainCore pauses when confirmation is needed before planning."""
    class ConfirmationDecisionEngine(DecisionEngine):
        def decide_next_capability(self, working_memory: WorkingMemory) -> str | None:
            if working_memory.intent_result is not None:
                return None
            return super().decide_next_capability(working_memory)

        def evaluate_confirmation_needed(self, working_memory: WorkingMemory) -> bool:
            return True

    brain = BrainCore(decision_engine=ConfirmationDecisionEngine())
    res = brain.process("open notepad")
    assert res.brain_status == BrainStatus.WAITING_FOR_USER
    assert any("user confirmation" in d.lower() for d in res.decision_history)


def test_brain_core_reflect_without_active_goal() -> None:
    """Verifies reflection handles cases where active goal was cleared or absent."""
    class NoActiveGoalManager(GoalManager):
        def get_active_goal(self) -> Goal | None:
            return None

    brain = BrainCore(goal_manager=NoActiveGoalManager())
    res = brain.process("open notepad")
    assert res.brain_status == BrainStatus.COMPLETED


def test_brain_core_terminated_status_transition() -> None:
    """Verifies BrainCore transitions to TERMINATED when appropriate."""
    class TerminatedDecisionEngine(DecisionEngine):
        def decide_terminal_status(self, working_memory: WorkingMemory) -> BrainStatus:
            return BrainStatus.TERMINATED

    brain = BrainCore(decision_engine=TerminatedDecisionEngine())
    res = brain.process("open notepad")
    assert res.brain_status == BrainStatus.TERMINATED

