"""Unit tests for the ARGOS planning subsystem.

This module contains the comprehensive test suite to verify the correctness,
robustness, and coverage of the planning pipeline.
"""

import logging
from unittest.mock import Mock

import pytest

from argos.intent import Intent
from argos.intent.intent_result import IntentResult
from argos.planning import (
    Action,
    InvalidIntentResultError,
    Plan,
    Planner,
    PlanStep,
    ProcessingError,
    StrategyResolutionError,
    ValidationError,
)
from argos.planning.constants import (
    DEFAULT_PLANNING_ENGINE,
)
from argos.planning.strategy import DefaultStrategy, FallbackStrategy, Strategy

# =====================================================================
# Action Enum Tests
# =====================================================================


def test_action_enum_values() -> None:
    """Verifies that the canonical Action enum contains all expected members."""
    expected_actions = {
        "OPEN_APP",
        "CLOSE_APP",
        "CREATE_FILE",
        "DELETE_FILE",
        "READ_FILE",
        "WRITE_FILE",
        "SEARCH_WEB",
        "RUN_COMMAND",
        "ASK_CLARIFICATION",
    }
    actual_members = set(Action.__members__.keys())
    assert expected_actions.issubset(actual_members)


def test_action_enum_str_behavior() -> None:
    """Verifies that Action behaves as a StrEnum."""
    assert Action.OPEN_APP == "open_app"
    assert isinstance(Action.OPEN_APP, str)
    assert f"{Action.SEARCH_WEB}" == "search_web"


# =====================================================================
# PlanStep & Plan Dataclass Tests
# =====================================================================


def test_plan_step_creation() -> None:
    """Verifies PlanStep instantiation and default parameters."""
    step = PlanStep(step_id=1, action=Action.OPEN_APP, parameters={"app": "chrome"})
    assert step.step_id == 1
    assert step.action == Action.OPEN_APP
    assert step.parameters == {"app": "chrome"}


def test_plan_step_slots() -> None:
    """Verifies that slots=True prevents dynamic attribute additions on PlanStep."""
    step = PlanStep(step_id=1, action=Action.OPEN_APP)
    with pytest.raises(AttributeError):
        step.extra_attribute = "unallowed"  # type: ignore


def test_plan_creation() -> None:
    """Verifies Plan instantiation and default parameters."""
    plan = Plan(primary_intent=Intent.OPEN_APPLICATION, confidence=0.9)
    assert plan.primary_intent == Intent.OPEN_APPLICATION
    assert plan.confidence == 0.9
    assert plan.steps == []
    assert plan.requires_confirmation is False
    assert plan.planning_engine == DEFAULT_PLANNING_ENGINE
    assert plan.metadata == {}


def test_plan_slots() -> None:
    """Verifies that slots=True prevents dynamic attribute additions on Plan."""
    plan = Plan()
    with pytest.raises(AttributeError):
        plan.extra_attribute = "unallowed"  # type: ignore


def test_plan_mutable_defaults() -> None:
    """Verifies that default factory prevents shared mutable states in Plan."""
    plan1 = Plan()
    plan2 = Plan()

    plan1.steps.append(PlanStep(step_id=1, action=Action.OPEN_APP))
    plan1.metadata["test"] = True

    assert plan2.steps == []
    assert plan2.metadata == {}


# =====================================================================
# Strategy Tests
# =====================================================================


def test_default_strategy_open_application() -> None:
    """Verifies DefaultStrategy resolves OPEN_APPLICATION intent."""
    strategy = DefaultStrategy()

    # Success path with app entities
    result = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.9,
        analysis_engine="test",
        entities={"application": ["chrome", "vscode"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 2
    assert steps[0].action == Action.OPEN_APP
    assert steps[0].parameters == {"application": "chrome"}
    assert steps[1].action == Action.OPEN_APP
    assert steps[1].parameters == {"application": "vscode"}

    # Failure path with missing apps
    result_empty = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION
    assert "specify an application" in steps_empty[0].parameters["message"]


def test_default_strategy_close_application() -> None:
    """Verifies DefaultStrategy resolves CLOSE_APPLICATION intent."""
    strategy = DefaultStrategy()

    # Success path
    result = IntentResult(
        primary_intent=Intent.CLOSE_APPLICATION,
        confidence=0.9,
        analysis_engine="test",
        entities={"application": ["chrome"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.CLOSE_APP
    assert steps[0].parameters == {"application": "chrome"}

    # Failure path
    result_empty = IntentResult(
        primary_intent=Intent.CLOSE_APPLICATION,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_read_file() -> None:
    """Verifies DefaultStrategy resolves READ_FILE and OPEN_FILE intents."""
    strategy = DefaultStrategy()

    result = IntentResult(
        primary_intent=Intent.OPEN_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={"file": ["notes.txt"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.READ_FILE
    assert steps[0].parameters == {"file_path": "notes.txt"}

    # Empty file list
    result_empty = IntentResult(
        primary_intent=Intent.READ_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_create_file() -> None:
    """Verifies DefaultStrategy resolves CREATE_FILE intent."""
    strategy = DefaultStrategy()

    result = IntentResult(
        primary_intent=Intent.CREATE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={"file": ["data.csv"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.CREATE_FILE
    assert steps[0].parameters == {"file_path": "data.csv"}

    # Empty
    result_empty = IntentResult(
        primary_intent=Intent.CREATE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_delete_file() -> None:
    """Verifies DefaultStrategy resolves DELETE_FILE intent."""
    strategy = DefaultStrategy()

    result = IntentResult(
        primary_intent=Intent.DELETE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={"file": ["notes.txt"], "folder": ["temp_dir"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 2
    assert steps[0].action == Action.DELETE_FILE
    assert steps[0].parameters == {"target": "notes.txt"}
    assert steps[1].action == Action.DELETE_FILE
    assert steps[1].parameters == {"target": "temp_dir"}

    # Empty targets
    result_empty = IntentResult(
        primary_intent=Intent.DELETE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_write_file() -> None:
    """Verifies DefaultStrategy resolves WRITE_FILE intent."""
    strategy = DefaultStrategy()

    result = IntentResult(
        primary_intent=Intent.WRITE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={"file": ["data.csv"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.WRITE_FILE
    assert steps[0].parameters == {"file_path": "data.csv"}

    # Empty
    result_empty = IntentResult(
        primary_intent=Intent.WRITE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_search_web() -> None:
    """Verifies DefaultStrategy resolves SEARCH_WEB intent."""
    strategy = DefaultStrategy()

    result = IntentResult(
        primary_intent=Intent.SEARCH_WEB,
        confidence=0.9,
        analysis_engine="test",
        entities={"website": ["google.com"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.SEARCH_WEB
    assert steps[0].parameters == {"query": "google.com"}

    # Empty
    result_empty = IntentResult(
        primary_intent=Intent.SEARCH_WEB,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_run_command() -> None:
    """Verifies DefaultStrategy resolves RUN_COMMAND intent."""
    strategy = DefaultStrategy()

    result = IntentResult(
        primary_intent=Intent.RUN_COMMAND,
        confidence=0.9,
        analysis_engine="test",
        entities={"command": ["pytest"]},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.RUN_COMMAND
    assert steps[0].parameters == {"command": "pytest"}

    # Empty
    result_empty = IntentResult(
        primary_intent=Intent.RUN_COMMAND,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps_empty = strategy.build_steps(result_empty)
    assert len(steps_empty) == 1
    assert steps_empty[0].action == Action.ASK_CLARIFICATION


def test_default_strategy_unmapped_intent() -> None:
    """Verifies DefaultStrategy resolves unmapped intents to ask_clarification."""
    strategy = DefaultStrategy()
    result = IntentResult(
        primary_intent=Intent.CONTROL_SYSTEM,
        confidence=0.9,
        analysis_engine="test",
        entities={},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.ASK_CLARIFICATION
    assert "requires manual confirmation" in steps[0].parameters["message"]


def test_fallback_strategy() -> None:
    """Verifies FallbackStrategy constructs clarification steps."""
    strategy = FallbackStrategy()
    result = IntentResult(
        primary_intent=Intent.UNKNOWN,
        confidence=0.2,
        analysis_engine="test",
        entities={},
    )
    steps = strategy.build_steps(result)
    assert len(steps) == 1
    assert steps[0].action == Action.ASK_CLARIFICATION
    assert "Could not resolve intent" in steps[0].parameters["message"]


# =====================================================================
# Planner Orchestrator Tests
# =====================================================================


def test_planner_validation() -> None:
    """Verifies Planner validates input parameter types."""
    planner = Planner()
    with pytest.raises(InvalidIntentResultError) as excinfo:
        planner.plan("not an IntentResult")  # type: ignore
    assert "must be an instance of IntentResult" in str(excinfo.value)


def test_planner_normal_path() -> None:
    """Verifies standard path routing with high confidence."""
    planner = Planner()
    result = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.9,
        analysis_engine="test_engine",
        entities={"application": ["chrome"]},
    )
    plan = planner.plan(result)
    assert isinstance(plan, Plan)
    assert plan.requires_confirmation is False
    assert len(plan.steps) == 1
    assert plan.steps[0].action == Action.OPEN_APP


def test_planner_confirmation_path() -> None:
    """Verifies path routing with medium confidence requires confirmation."""
    planner = Planner()
    result = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.7,  # Between 0.60 and 0.80
        analysis_engine="test_engine",
        entities={"application": ["chrome"]},
    )
    plan = planner.plan(result)
    assert plan.requires_confirmation is True
    assert len(plan.steps) == 1
    assert plan.steps[0].action == Action.OPEN_APP


def test_planner_clarification_path() -> None:
    """Verifies path routing with low confidence or unknown intent triggers fallback."""
    planner = Planner()

    # Low confidence
    result1 = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.5,  # Below 0.60
        analysis_engine="test_engine",
        entities={"application": ["chrome"]},
    )
    plan1 = planner.plan(result1)
    assert plan1.requires_confirmation is False
    assert len(plan1.steps) == 1
    assert plan1.steps[0].action == Action.ASK_CLARIFICATION
    assert "Could not resolve" in plan1.steps[0].parameters["message"]

    # Unknown intent
    result2 = IntentResult(
        primary_intent=Intent.UNKNOWN,
        confidence=0.9,
        analysis_engine="test_engine",
        entities={},
    )
    plan2 = planner.plan(result2)
    assert plan2.requires_confirmation is False
    assert len(plan2.steps) == 1
    assert plan2.steps[0].action == Action.ASK_CLARIFICATION


def test_planner_dependency_injection() -> None:
    """Verifies injected custom strategies are invoked."""
    mock_default = Mock(spec=Strategy)
    mock_fallback = Mock(spec=Strategy)

    step = PlanStep(step_id=1, action=Action.RUN_COMMAND)
    mock_default.build_steps.return_value = [step]

    planner = Planner(default_strategy=mock_default, fallback_strategy=mock_fallback)
    result = IntentResult(
        primary_intent=Intent.RUN_COMMAND,
        confidence=0.95,
        analysis_engine="test",
        entities={},
    )
    plan = planner.plan(result)
    mock_default.build_steps.assert_called_once_with(result)
    mock_fallback.build_steps.assert_not_called()
    assert plan.steps == [step]


def test_planner_error_wrapping() -> None:
    """Verifies unexpected runtime crashes are caught and wrapped in ProcessingError."""
    mock_default = Mock(spec=Strategy)
    mock_default.build_steps.side_effect = RuntimeError("Fatal hardware memory fault")

    planner = Planner(default_strategy=mock_default)
    result = IntentResult(
        primary_intent=Intent.RUN_COMMAND,
        confidence=0.95,
        analysis_engine="test",
        entities={},
    )

    with pytest.raises(ProcessingError) as excinfo:
        planner.plan(result)
    assert "Fatal hardware memory fault" in str(excinfo.value)
    assert "unexpected error occurred" in str(excinfo.value)


def test_planner_re_raise_planning_error() -> None:
    """Verifies subsystem PlanningError subclass exceptions are raised directly."""
    mock_default = Mock(spec=Strategy)
    mock_default.build_steps.side_effect = StrategyResolutionError("Failed matching")

    planner = Planner(default_strategy=mock_default)
    result = IntentResult(
        primary_intent=Intent.RUN_COMMAND,
        confidence=0.95,
        analysis_engine="test",
        entities={},
    )

    with pytest.raises(StrategyResolutionError) as excinfo:
        planner.plan(result)
    assert "Failed matching" in str(excinfo.value)


def test_planner_logging_behavior(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies logs are correctly emitted and filter out sensitive payloads at INFO."""
    planner = Planner()
    result = IntentResult(
        primary_intent=Intent.WRITE_FILE,
        confidence=0.95,
        analysis_engine="test_engine",
        entities={"file": ["confidential_salaries.csv"]},
    )

    with caplog.at_level(logging.INFO):
        planner.plan(result)

    log_messages = [record.message for record in caplog.records]
    assert any("Planning started for primary intent" in msg for msg in log_messages)
    assert any(
        "Plan steps generation completed successfully" in msg
        for msg in log_messages
    )
    assert any("Plan construction completed" in msg for msg in log_messages)

    # Privacy verification: Raw confidential values must not leak to INFO
    assert not any("confidential_salaries.csv" in msg for msg in log_messages)

    # Verify failure logs
    caplog.clear()
    mock_default = Mock(spec=Strategy)
    mock_default.build_steps.side_effect = ValidationError("Invalid configuration")
    err_planner = Planner(default_strategy=mock_default)

    with pytest.raises(ValidationError):
        err_planner.plan(result)

    error_logs = [record.message for record in caplog.records]
    assert any("Planning subsystem exception occurred" in msg for msg in error_logs)


# =====================================================================
# Public API & Encapsulation Boundary Tests
# =====================================================================


def test_public_api_exports() -> None:
    """Verifies all public subsystem exports are importable from argos.planning."""
    import argos.planning as planning_package

    # Verify expected public components
    assert hasattr(planning_package, "Planner")
    assert hasattr(planning_package, "Plan")
    assert hasattr(planning_package, "PlanStep")
    assert hasattr(planning_package, "Action")
    assert hasattr(planning_package, "PlanningError")
    assert hasattr(planning_package, "ValidationError")
    assert hasattr(planning_package, "ProcessingError")

    # Verify that internal components are NOT exported at the package root
    assert not hasattr(planning_package, "DefaultStrategy")
    assert not hasattr(planning_package, "FallbackStrategy")
    assert not hasattr(planning_package, "Strategy")
