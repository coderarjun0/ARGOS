"""Unit tests for the ARGOS execution subsystem.

This module contains the comprehensive test suite to verify the correctness,
robustness, and coverage of the execution pipeline.
"""

import logging
from datetime import UTC
from unittest.mock import Mock

import pytest

from argos.execution import (
    ExecutionEngine,
    ExecutionResult,
    ExecutionStatus,
    InvalidPlanError,
    InvalidStepError,
    ProcessingError,
    RoutingError,
    StepResult,
    ValidationError,
)
from argos.execution.action_executor import ActionExecutor
from argos.execution.action_router import ActionRouter
from argos.execution.application_executor import ApplicationExecutor
from argos.execution.constants import (
    DEFAULT_EXECUTION_ENGINE,
    MAX_PLAN_STEPS,
    MAX_STEP_MESSAGE_LENGTH,
)
from argos.execution.execution_aggregator import ExecutionAggregator
from argos.execution.file_executor import FileExecutor
from argos.execution.system_executor import SystemExecutor
from argos.execution.web_executor import WebExecutor
from argos.planning.action import Action
from argos.planning.plan import Plan
from argos.planning.plan_step import PlanStep

# =====================================================================
# ExecutionStatus Enum Tests
# =====================================================================


def test_execution_status_enum_values() -> None:
    """Verifies that ExecutionStatus contains all expected members."""
    expected_statuses = {"SUCCESS", "PARTIAL_SUCCESS", "FAILED"}
    actual_members = set(ExecutionStatus.__members__.keys())
    assert expected_statuses.issubset(actual_members)


def test_execution_status_enum_str_behavior() -> None:
    """Verifies that ExecutionStatus behaves as a StrEnum."""
    assert ExecutionStatus.SUCCESS == "success"
    assert isinstance(ExecutionStatus.SUCCESS, str)


# =====================================================================
# StepResult & ExecutionResult Dataclass Tests
# =====================================================================


def test_step_result_creation() -> None:
    """Verifies StepResult instantiation and default parameters."""
    result = StepResult(
        step_id=1,
        action=Action.OPEN_APP,
        success=True,
        message="Simulated launcher",
    )
    assert result.step_id == 1
    assert result.action == Action.OPEN_APP
    assert result.success is True
    assert result.message == "Simulated launcher"
    assert result.metadata == {}


def test_step_result_slots() -> None:
    """Verifies that slots=True prevents dynamic attribute additions on StepResult."""
    result = StepResult(
        step_id=1,
        action=Action.OPEN_APP,
        success=True,
        message="Simulated",
    )
    with pytest.raises(AttributeError):
        result.extra_attribute = "unallowed"  # type: ignore


def test_execution_result_creation() -> None:
    """Verifies ExecutionResult instantiation and default parameters."""
    result = ExecutionResult(status=ExecutionStatus.SUCCESS)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.step_results == []
    assert result.execution_engine == DEFAULT_EXECUTION_ENGINE
    assert result.metadata == {}


def test_execution_result_slots() -> None:
    """Verifies slots=True prevents dynamic attribute additions on ExecutionResult."""
    result = ExecutionResult(status=ExecutionStatus.SUCCESS)
    with pytest.raises(AttributeError):
        result.extra_attribute = "unallowed"  # type: ignore


def test_execution_result_mutable_defaults() -> None:
    """Verifies default factory prevents shared mutable states in ExecutionResult."""
    res1 = ExecutionResult(status=ExecutionStatus.SUCCESS)
    res2 = ExecutionResult(status=ExecutionStatus.SUCCESS)

    res1.step_results.append(
        StepResult(step_id=1, action=Action.OPEN_APP, success=True, message="a")
    )
    res1.metadata["test"] = True

    assert res2.step_results == []
    assert res2.metadata == {}


# =====================================================================
# ActionRouter Tests
# =====================================================================


def test_action_router_success() -> None:
    """Verifies custom router registration and resolution mapping."""
    router = ActionRouter()
    mock_executor = Mock(spec=ActionExecutor)
    router.register(Action.OPEN_APP, mock_executor)
    assert router.route(Action.OPEN_APP) == mock_executor


def test_action_router_routing_error() -> None:
    """Verifies RoutingError is raised when an action has no registered mapping."""
    router = ActionRouter()
    with pytest.raises(RoutingError) as excinfo:
        router.route(Action.OPEN_APP)
    assert "No executor is registered" in str(excinfo.value)


# =====================================================================
# ExecutionAggregator Tests
# =====================================================================


def test_execution_aggregator_outcomes() -> None:
    """Verifies result compiler outcome aggregations."""
    aggregator = ExecutionAggregator()

    # Empty step results
    assert aggregator.aggregate([]) == ExecutionStatus.SUCCESS

    # All success
    steps_success = [
        StepResult(step_id=1, action=Action.OPEN_APP, success=True, message="ok"),
        StepResult(step_id=2, action=Action.CREATE_FILE, success=True, message="ok"),
    ]
    assert aggregator.aggregate(steps_success) == ExecutionStatus.SUCCESS

    # All failed
    steps_failed = [
        StepResult(step_id=1, action=Action.OPEN_APP, success=False, message="err"),
        StepResult(step_id=2, action=Action.CREATE_FILE, success=False, message="err"),
    ]
    assert aggregator.aggregate(steps_failed) == ExecutionStatus.FAILED

    # Mixed success (partial success)
    steps_mixed = [
        StepResult(step_id=1, action=Action.OPEN_APP, success=True, message="ok"),
        StepResult(step_id=2, action=Action.CREATE_FILE, success=False, message="err"),
    ]
    assert aggregator.aggregate(steps_mixed) == ExecutionStatus.PARTIAL_SUCCESS


# =====================================================================
# Concrete ActionExecutor Tests
# =====================================================================


def test_application_executor() -> None:
    """Verifies application executor success paths and parameter checks."""
    executor = ApplicationExecutor()

    # OPEN_APP success
    step_open = PlanStep(
        step_id=1, action=Action.OPEN_APP, parameters={"application": "chrome"}
    )
    res_open = executor.execute(step_open)
    assert res_open.success is True
    assert "launched successfully" in res_open.message

    # CLOSE_APP success
    step_close = PlanStep(
        step_id=2, action=Action.CLOSE_APP, parameters={"application": "chrome"}
    )
    res_close = executor.execute(step_close)
    assert res_close.success is True
    assert "closed successfully" in res_close.message

    # Missing parameters
    step_invalid_params = PlanStep(step_id=3, action=Action.OPEN_APP)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_invalid_params)
    assert "Missing required 'application'" in str(excinfo.value)

    # Action mismatch
    step_mismatch = PlanStep(step_id=4, action=Action.RUN_COMMAND)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_mismatch)
    assert "cannot execute action" in str(excinfo.value)


def test_file_executor() -> None:
    """Verifies file executor success paths and parameter checks."""
    executor = FileExecutor()

    # CREATE_FILE success
    step_create = PlanStep(
        step_id=1, action=Action.CREATE_FILE, parameters={"file_path": "a.txt"}
    )
    res_create = executor.execute(step_create)
    assert res_create.success is True
    assert Action.CREATE_FILE in res_create.message

    # DELETE_FILE success (target)
    step_del = PlanStep(
        step_id=2, action=Action.DELETE_FILE, parameters={"target": "temp_dir"}
    )
    res_del = executor.execute(step_del)
    assert res_del.success is True
    assert "deleted successfully" in res_del.message

    # DELETE_FILE success (file_path fallback)
    step_del_path = PlanStep(
        step_id=3, action=Action.DELETE_FILE, parameters={"file_path": "b.txt"}
    )
    res_del_path = executor.execute(step_del_path)
    assert res_del_path.success is True
    assert "deleted successfully" in res_del_path.message

    # Missing parameters (CREATE_FILE)
    step_invalid = PlanStep(step_id=4, action=Action.CREATE_FILE)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_invalid)
    assert "Missing required 'file_path'" in str(excinfo.value)

    # Missing parameters (DELETE_FILE)
    step_invalid_del = PlanStep(step_id=5, action=Action.DELETE_FILE)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_invalid_del)
    assert "Missing required 'target' or 'file_path'" in str(excinfo.value)

    # Action mismatch
    step_mismatch = PlanStep(step_id=6, action=Action.SEARCH_WEB)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_mismatch)
    assert "cannot execute action" in str(excinfo.value)


def test_web_executor() -> None:
    """Verifies web search executor success paths and parameter checks."""
    executor = WebExecutor()

    # Success (query)
    step_query = PlanStep(
        step_id=1, action=Action.SEARCH_WEB, parameters={"query": "python"}
    )
    res_query = executor.execute(step_query)
    assert res_query.success is True
    assert "python" in res_query.message

    # Success (url fallback)
    step_url = PlanStep(
        step_id=2, action=Action.SEARCH_WEB, parameters={"url": "google.com"}
    )
    res_url = executor.execute(step_url)
    assert res_url.success is True
    assert "google.com" in res_url.message

    # Success (website fallback)
    step_website = PlanStep(
        step_id=3, action=Action.SEARCH_WEB, parameters={"website": "github"}
    )
    res_website = executor.execute(step_website)
    assert res_website.success is True
    assert "github" in res_website.message

    # Missing parameters
    step_invalid = PlanStep(step_id=4, action=Action.SEARCH_WEB)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_invalid)
    assert "Missing required 'query', 'url', or 'website'" in str(excinfo.value)

    # Action mismatch
    step_mismatch = PlanStep(step_id=5, action=Action.OPEN_APP)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_mismatch)
    assert "cannot execute action" in str(excinfo.value)


def test_system_executor() -> None:
    """Verifies system command executor success paths and parameter checks."""
    executor = SystemExecutor()

    # Success
    step = PlanStep(
        step_id=1, action=Action.RUN_COMMAND, parameters={"command": "pytest"}
    )
    res = executor.execute(step)
    assert res.success is True
    assert "pytest" in res.message

    # Missing parameters
    step_invalid = PlanStep(step_id=2, action=Action.RUN_COMMAND)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_invalid)
    assert "Missing required 'command'" in str(excinfo.value)

    # Action mismatch
    step_mismatch = PlanStep(step_id=3, action=Action.OPEN_APP)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step_mismatch)
    assert "cannot execute action" in str(excinfo.value)


# =====================================================================
# ExecutionEngine Orchestrator Tests
# =====================================================================


def test_engine_validation() -> None:
    """Verifies that non-Plan instances raise InvalidPlanError."""
    engine = ExecutionEngine()
    with pytest.raises(InvalidPlanError) as excinfo:
        engine.execute("not a Plan")  # type: ignore
    assert "must be an instance of Plan" in str(excinfo.value)


def test_engine_threshold_limits() -> None:
    """Verifies validation checking for maximum step threshold counts."""
    engine = ExecutionEngine()
    steps = [
        PlanStep(step_id=i, action=Action.OPEN_APP)
        for i in range(MAX_PLAN_STEPS + 5)
    ]
    plan = Plan(steps=steps)
    with pytest.raises(ValidationError) as excinfo:
        engine.execute(plan)
    assert "exceeds maximum limit" in str(excinfo.value)


def test_engine_normal_execution() -> None:
    """Verifies successful end-to-end routing, aggregation, and execution."""
    from datetime import datetime

    from argos.memory.models import AuthorizationRecord, AuthorizationType

    engine = ExecutionEngine()
    plan = Plan(
        steps=[
            PlanStep(
                step_id=1,
                action=Action.OPEN_APP,
                parameters={"application": "chrome"},
            ),
            PlanStep(
                step_id=2,
                action=Action.RUN_COMMAND,
                parameters={
                    "command": "pytest",
                    "authorization": AuthorizationRecord(
                        granted=True,
                        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
                        granted_at=datetime.now(UTC),
                    ),
                },
            ),
            PlanStep(
                step_id=3,
                action=Action.ASK_CLARIFICATION,
                parameters={"message": "Please confirm details"},
            ),
        ]
    )
    result = engine.execute(plan)
    assert isinstance(result, ExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.step_results) == 3
    assert result.step_results[0].success is True
    assert "chrome" in result.step_results[0].message
    assert "pytest" in result.step_results[1].message
    assert "Please confirm details" in result.step_results[2].message


def test_engine_truncation() -> None:
    """Verifies that step message descriptions exceeding limits are truncated."""
    engine = ExecutionEngine()
    long_msg = "x" * (MAX_STEP_MESSAGE_LENGTH + 100)
    plan = Plan(
        steps=[
            PlanStep(
                step_id=1,
                action=Action.ASK_CLARIFICATION,
                parameters={"message": long_msg},
            )
        ]
    )
    result = engine.execute(plan)
    assert len(result.step_results[0].message) == MAX_STEP_MESSAGE_LENGTH
    assert result.step_results[0].message == long_msg[:MAX_STEP_MESSAGE_LENGTH]


def test_engine_dependency_injection() -> None:
    """Verifies injected custom ActionRouter is invoked."""
    mock_router = Mock(spec=ActionRouter)
    mock_executor = Mock(spec=ActionExecutor)

    mock_router.route.return_value = mock_executor
    mock_executor.execute.return_value = StepResult(
        step_id=1, action=Action.OPEN_APP, success=True, message="mocked success"
    )

    engine = ExecutionEngine(router=mock_router)
    plan = Plan(steps=[PlanStep(step_id=1, action=Action.OPEN_APP)])
    result = engine.execute(plan)

    mock_router.route.assert_called_once_with(Action.OPEN_APP)
    mock_executor.execute.assert_called_once()
    assert result.status == ExecutionStatus.SUCCESS
    assert result.step_results[0].message == "mocked success"


def test_engine_unexpected_crashes() -> None:
    """Verifies unexpected exceptions are wrapped in a ProcessingError."""
    mock_router = Mock(spec=ActionRouter)
    mock_router.route.side_effect = RuntimeError("Hardware database failure")

    engine = ExecutionEngine(router=mock_router)
    plan = Plan(steps=[PlanStep(step_id=1, action=Action.OPEN_APP)])

    with pytest.raises(ProcessingError) as excinfo:
        engine.execute(plan)
    assert "An unexpected error occurred" in str(excinfo.value)
    assert "Hardware database" in str(excinfo.value)


def test_engine_re_raise_execution_error() -> None:
    """Verifies subsystem base exceptions are raised directly."""
    mock_router = Mock(spec=ActionRouter)
    mock_router.route.side_effect = RoutingError("Lookup failed")

    engine = ExecutionEngine(router=mock_router)
    plan = Plan(steps=[PlanStep(step_id=1, action=Action.OPEN_APP)])

    with pytest.raises(RoutingError) as excinfo:
        engine.execute(plan)
    assert "Lookup failed" in str(excinfo.value)


def test_engine_logging_behavior(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies logs are emitted correctly and hide sensitive parameters from INFO."""
    engine = ExecutionEngine()
    plan = Plan(
        steps=[
            PlanStep(
                step_id=1,
                action=Action.WRITE_FILE,
                parameters={"file_path": "confidential_salaries.csv"},
            )
        ]
    )

    with caplog.at_level(logging.INFO):
        engine.execute(plan)

    log_messages = [record.message for record in caplog.records]
    assert any("Execution started for engine" in msg for msg in log_messages)
    assert any("Executing step ID: 1" in msg for msg in log_messages)
    assert any("Execution completed with status" in msg for msg in log_messages)

    # Privacy verification: Raw sensitive parameters must not leak to INFO
    assert not any("confidential_salaries.csv" in msg for msg in log_messages)

    # Verify failure logs
    caplog.clear()
    mock_router = Mock(spec=ActionRouter)
    mock_router.route.side_effect = ValidationError("Invalid setup")
    err_engine = ExecutionEngine(router=mock_router)

    with pytest.raises(ValidationError):
        err_engine.execute(plan)

    error_logs = [record.message for record in caplog.records]
    assert any("Execution subsystem exception occurred" in msg for msg in error_logs)


# =====================================================================
# Public API & Encapsulation Boundary Tests
# =====================================================================


def test_public_api_exports() -> None:
    """Verifies all public subsystem exports are importable from argos.execution."""
    import argos.execution as execution_package

    # Verify expected public components
    assert hasattr(execution_package, "ExecutionEngine")
    assert hasattr(execution_package, "ExecutionResult")
    assert hasattr(execution_package, "ExecutionStatus")
    assert hasattr(execution_package, "StepResult")
    assert hasattr(execution_package, "ExecutionError")
    assert hasattr(execution_package, "ValidationError")
    assert hasattr(execution_package, "ProcessingError")

    # Verify that internal components are NOT exported at the package root
    assert not hasattr(execution_package, "ActionRouter")
    assert not hasattr(execution_package, "ExecutionAggregator")
    assert not hasattr(execution_package, "ApplicationExecutor")


def test_clarification_executor_mismatch() -> None:
    """Verifies _ClarificationExecutor raises InvalidStepError on action mismatch."""
    from argos.execution.execution_engine import _ClarificationExecutor
    executor = _ClarificationExecutor()
    step = PlanStep(step_id=1, action=Action.OPEN_APP)
    with pytest.raises(InvalidStepError) as excinfo:
        executor.execute(step)
    assert "cannot execute action" in str(excinfo.value)


def test_execution_engine_edge_cases_and_policy() -> None:
    """Verifies ExecutionEngine policy confirmation requirement and error handling."""
    from argos.execution.exceptions import ExecutionError
    from argos.policy.models import PolicyOutcome, PolicyRule, PolicyScope, RuleOperator
    from argos.policy.policy_engine import PolicyEngine

    pe = PolicyEngine()
    pe.register_user_rule(PolicyRule(
        rule_id="CONFIRM_APP",
        scope=PolicyScope.USER_POLICY,
        target_capability="tool_execution",
        target_action="open_app",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
        explanation="App open confirmation required",
    ))

    engine = ExecutionEngine(policy_engine=pe)
    assert engine.policy_engine is pe

    # Plan with step requiring confirmation without authorization
    step = PlanStep(
        step_id=1, action=Action.OPEN_APP, parameters={"application": "notepad"}
    )
    plan = Plan(steps=[step])
    res = engine.execute(plan)
    assert len(res.step_results) == 1
    assert "Policy requirement" in res.step_results[0].message

    # Unexpected exception during step execution
    mock_router = Mock()
    mock_router.route.side_effect = RuntimeError("System crash")
    failing_engine = ExecutionEngine(router=mock_router)
    msg = "An unexpected error occurred during execution"
    with pytest.raises(ExecutionError, match=msg):
        failing_engine.execute(plan)


def test_execution_engine_step_failure_stops_loop() -> None:
    """Verifies that step failure stops plan execution loop (L229 break)."""
    mock_executor = Mock()
    mock_executor.execute.return_value = StepResult(
        step_id=1, action=Action.OPEN_APP, success=False, message="App launch failed"
    )
    mock_router = Mock()
    mock_router.route.return_value = mock_executor

    engine = ExecutionEngine(router=mock_router)
    step1 = PlanStep(
        step_id=1, action=Action.OPEN_APP, parameters={"application": "calc"}
    )
    step2 = PlanStep(
        step_id=2, action=Action.OPEN_APP, parameters={"application": "notepad"}
    )
    plan = Plan(steps=[step1, step2])
    res = engine.execute(plan)
    assert res.status == ExecutionStatus.FAILED
    assert len(res.step_results) == 1
    assert res.step_results[0].success is False
