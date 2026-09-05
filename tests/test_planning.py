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
    assert hasattr(planning_package, "SchemaValidator")
    assert hasattr(planning_package, "PlanningError")
    assert hasattr(planning_package, "ValidationError")
    assert hasattr(planning_package, "SchemaValidationError")
    assert hasattr(planning_package, "MissingParameterError")
    assert hasattr(planning_package, "ReservedParameterError")
    assert hasattr(planning_package, "InvalidParameterError")
    assert hasattr(planning_package, "StrategyResolutionError")
    assert hasattr(planning_package, "UnsupportedActionError")
    assert hasattr(planning_package, "AmbiguousPlannerActionError")
    assert hasattr(planning_package, "ProcessingError")

    # Verify that internal components are NOT exported at the package root
    assert not hasattr(planning_package, "DefaultStrategy")
    assert not hasattr(planning_package, "FallbackStrategy")
    assert not hasattr(planning_package, "Strategy")
    assert not hasattr(planning_package, "DomainPlannerStrategy")


# =====================================================================
# ARS-004 SchemaValidator & Strategy Tests
# =====================================================================


def test_schema_validator_success() -> None:
    """Verifies SchemaValidator validates and coerces valid entity parameters."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec1 = ParameterSpec(name="app", param_type=str, required=True)
    spec2 = ParameterSpec(name="count", param_type=int, required=False, default=1)
    schema = ActionSchemaDescriptor(
        action=Action.OPEN_APP,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec1, spec2),
    )

    validated, unmapped = SchemaValidator.validate_and_coerce(
        schema, {"app": "calc", "count": "3"}
    )
    assert validated == {"app": "calc", "count": 3}
    assert unmapped == {}


def test_schema_validator_optional_default() -> None:
    """Verifies SchemaValidator injects spec.default when optional params omitted."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec = ParameterSpec(name="mode", param_type=str, required=False, default="fast")
    schema = ActionSchemaDescriptor(
        action=Action.QUERY_SYS_INFO,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec,),
    )

    validated, unmapped = SchemaValidator.validate_and_coerce(schema, {})
    assert validated == {"mode": "fast"}
    assert unmapped == {}


def test_schema_validator_missing_required() -> None:
    """Verifies SchemaValidator raises MissingParameterError."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.exceptions import MissingParameterError
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec = ParameterSpec(name="file_path", param_type=str, required=True)
    schema = ActionSchemaDescriptor(
        action=Action.READ_FILE,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec,),
    )

    with pytest.raises(MissingParameterError) as excinfo:
        SchemaValidator.validate_and_coerce(schema, {})
    assert "Required parameter 'file_path' is missing" in str(excinfo.value)


def test_schema_validator_invalid_type() -> None:
    """Verifies SchemaValidator raises InvalidParameterError on non-coercible types."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.exceptions import InvalidParameterError
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec = ParameterSpec(name="port", param_type=int, required=True)
    schema = ActionSchemaDescriptor(
        action=Action.QUERY_SYS_INFO,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec,),
    )

    with pytest.raises(InvalidParameterError) as excinfo:
        SchemaValidator.validate_and_coerce(schema, {"port": [1, 2, 3]})
    assert "must be of type 'int'" in str(excinfo.value)


def test_schema_validator_allowed_values() -> None:
    """Verifies SchemaValidator enforces allowed_values constraints."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.exceptions import InvalidParameterError
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec = ParameterSpec(
        name="format",
        param_type=str,
        required=True,
        allowed_values=("json", "xml"),
    )
    schema = ActionSchemaDescriptor(
        action=Action.QUERY_SYS_INFO,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec,),
    )

    # Valid value
    val, _ = SchemaValidator.validate_and_coerce(schema, {"format": "json"})
    assert val == {"format": "json"}

    # Disallowed value
    with pytest.raises(InvalidParameterError) as excinfo:
        SchemaValidator.validate_and_coerce(schema, {"format": "csv"})
    assert "is not in allowed values" in str(excinfo.value)


def test_schema_validator_reserved_parameter() -> None:
    """Verifies SchemaValidator raises ReservedParameterError if key starts with '_'."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.exceptions import ReservedParameterError
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import RiskClass

    schema = ActionSchemaDescriptor(
        action=Action.OPEN_APP,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(),
    )

    with pytest.raises(ReservedParameterError) as excinfo:
        SchemaValidator.validate_and_coerce(schema, {"_risk_class": "READ_ONLY"})
    assert "starts with reserved prefix '_'" in str(excinfo.value)


def test_schema_validator_none_vs_omitted() -> None:
    """Verifies None behavior."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.exceptions import InvalidParameterError
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec = ParameterSpec(
        name="query", param_type=str, required=False, default="default"
    )
    schema = ActionSchemaDescriptor(
        action=Action.SEARCH_WEB,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec,),
    )

    # Key omitted -> injects default
    val_omitted, _ = SchemaValidator.validate_and_coerce(schema, {})
    assert val_omitted == {"query": "default"}

    # Key present with None -> type check fails
    with pytest.raises((InvalidParameterError, Exception)):
        SchemaValidator.validate_and_coerce(schema, {"query": None})


def test_schema_validator_unmapped_entities() -> None:
    """Verifies extraneous entities are collected into unmapped_entities."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    spec = ParameterSpec(name="app", param_type=str, required=True)
    schema = ActionSchemaDescriptor(
        action=Action.OPEN_APP,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(spec,),
    )

    validated, unmapped = SchemaValidator.validate_and_coerce(
        schema, {"app": "notepad", "extra_key": "extra_value"}
    )
    assert validated == {"app": "notepad"}
    assert unmapped == {"extra_key": "extra_value"}


def test_domain_planner_all_supported_actions() -> None:
    """Verifies DomainPlannerStrategy handles all 8 supported ARS-004 actions."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.capabilities.domains.application_domain import ApplicationDomain
    from argos.capabilities.domains.file_system_domain import FileSystemDomain
    from argos.capabilities.domains.system_info_domain import SystemInfoDomain
    from argos.capabilities.domains.web_domain import WebDomain
    from argos.planning.strategy import DomainPlannerStrategy
    from argos.tools.base_tool import (
        BaseTool,
        ParameterSpec,
        RiskClass,
        ToolManifest,
        ToolResult,
    )

    class FakeAppTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="fake_app_tool",
                version="1.0",
                description="Fake app tool",
                supported_actions=("open_app", "close_app"),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="application", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    class FakeFileTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="fake_file_tool",
                version="1.0",
                description="Fake file tool",
                supported_actions=(
                    "read_file",
                    "write_file",
                    "create_file",
                    "list_dir",
                ),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="file_path", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    class FakeSysTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="fake_sys_tool",
                version="1.0",
                description="Fake sys tool",
                supported_actions=("query_sys_info",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(
                    ParameterSpec(
                        name="query", param_type=str, required=False, default="all"
                    ),
                ),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    class FakeWebTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="fake_web_tool",
                version="1.0",
                description="Fake web tool",
                supported_actions=("search_web",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="query", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    registry = CapabilityRegistry()
    registry.register_domain(ApplicationDomain())
    registry.register_domain(FileSystemDomain())
    registry.register_domain(SystemInfoDomain())
    registry.register_domain(WebDomain())
    registry.index_tool(FakeAppTool())
    registry.index_tool(FakeFileTool())
    registry.index_tool(FakeSysTool())
    registry.index_tool(FakeWebTool())
    registry.freeze()

    strategy = DomainPlannerStrategy(registry)

    # 1. OPEN_APP
    r = IntentResult(Intent.OPEN_APPLICATION, 0.9, "test", {"application": ["calc"]})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.OPEN_APP
    assert steps[0].parameters == {"application": "calc"}

    # 2. CLOSE_APP
    r = IntentResult(Intent.CLOSE_APPLICATION, 0.9, "test", {"application": ["calc"]})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.CLOSE_APP

    # 3. READ_FILE
    r = IntentResult(Intent.READ_FILE, 0.9, "test", {"file": ["test.txt"]})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.READ_FILE
    assert steps[0].parameters == {"file_path": "test.txt"}

    # 4. CREATE_FILE
    r = IntentResult(Intent.CREATE_FILE, 0.9, "test", {"file": ["test.txt"]})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.CREATE_FILE

    # 5. WRITE_FILE
    r = IntentResult(Intent.WRITE_FILE, 0.9, "test", {"file": ["test.txt"]})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.WRITE_FILE

    # 6. SEARCH_WEB
    r = IntentResult(Intent.SEARCH_WEB, 0.9, "test", {"query": ["python"]})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.SEARCH_WEB
    assert steps[0].parameters == {"query": "python"}

    # 7. QUERY_SYS_INFO
    r = IntentResult(Intent.GET_INFORMATION, 0.9, "test", {})
    steps = strategy.build_steps(r)
    assert steps[0].action == Action.QUERY_SYS_INFO
    assert steps[0].parameters == {"query": "all"}


def test_domain_planner_unsupported_actions() -> None:
    """Verifies legacy unsupported actions raise UnsupportedActionError."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.planning.exceptions import UnsupportedActionError
    from argos.planning.strategy import DomainPlannerStrategy

    registry = CapabilityRegistry()
    registry.freeze()
    strategy = DomainPlannerStrategy(registry)

    # DELETE_FILE intent
    r_del = IntentResult(Intent.DELETE_FILE, 0.9, "test", {"file": ["test.txt"]})
    with pytest.raises(UnsupportedActionError):
        strategy.build_steps(r_del)

    # RUN_COMMAND intent
    r_cmd = IntentResult(Intent.RUN_COMMAND, 0.9, "test", {"command": ["dir"]})
    with pytest.raises(UnsupportedActionError):
        strategy.build_steps(r_cmd)


def test_domain_planner_ambiguity_resolution() -> None:
    """Verifies ambiguous action resolution with and without tool hints."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.capabilities.domains.application_domain import ApplicationDomain
    from argos.planning.strategy import DomainPlannerStrategy
    from argos.tools.base_tool import (
        BaseTool,
        ParameterSpec,
        RiskClass,
        ToolManifest,
        ToolResult,
    )

    class ToolA(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="tool_a",
                version="1.0",
                description="Tool A",
                supported_actions=("open_app",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="application", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    class ToolB(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="tool_b",
                version="1.0",
                description="Tool B",
                supported_actions=("open_app",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="application", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    registry = CapabilityRegistry()
    registry.register_domain(ApplicationDomain())
    registry.index_tool(ToolA())
    registry.index_tool(ToolB())
    registry.freeze()

    strategy = DomainPlannerStrategy(registry)

    # 1. Ambiguous action without tool hint -> ASK_CLARIFICATION
    r_no_hint = IntentResult(
        Intent.OPEN_APPLICATION, 0.9, "test", {"application": ["calc"]}
    )
    steps1 = strategy.build_steps(r_no_hint)
    assert len(steps1) == 1
    assert steps1[0].action == Action.ASK_CLARIFICATION
    assert "Multiple tools for action" in steps1[0].parameters["message"]

    # 2. Ambiguous action with valid tool hint -> Resolves matching schema
    r_valid_hint = IntentResult(
        Intent.OPEN_APPLICATION,
        0.9,
        "test",
        {"application": ["calc"], "tool_id": ["tool_b"]},
    )
    steps2 = strategy.build_steps(r_valid_hint)
    assert len(steps2) == 1
    assert steps2[0].action == Action.OPEN_APP
    assert steps2[0].parameters == {"application": "calc"}

    # 3. Ambiguous action with invalid tool hint -> ASK_CLARIFICATION
    r_invalid_hint = IntentResult(
        Intent.OPEN_APPLICATION,
        0.9,
        "test",
        {"application": ["calc"], "tool_id": ["invalid_tool"]},
    )
    steps3 = strategy.build_steps(r_invalid_hint)
    assert len(steps3) == 1
    assert steps3[0].action == Action.ASK_CLARIFICATION


def test_planner_constructor_and_orchestration() -> None:
    """Verifies Planner constructor decision tree and fallback orchestration."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.planning.exceptions import ReservedParameterError
    from argos.planning.strategy import (
        DefaultStrategy,
        DomainPlannerStrategy,
        FallbackStrategy,
    )

    # Case A: capability_registry supplied -> uses DomainPlannerStrategy
    reg = CapabilityRegistry()
    p_a = Planner(capability_registry=reg)
    assert isinstance(p_a._default_strategy, DomainPlannerStrategy)

    # Case B: capability_registry omitted -> uses DefaultStrategy
    p_b = Planner()
    assert isinstance(p_b._default_strategy, DefaultStrategy)

    # Case C: explicit default_strategy supplied -> uses explicit strategy
    custom_strat = DefaultStrategy()
    p_c = Planner(capability_registry=reg, default_strategy=custom_strat)
    assert p_c._default_strategy is custom_strat

    # Case D: explicit fallback_strategy supplied -> uses explicit fallback
    custom_fb = FallbackStrategy()
    p_d = Planner(fallback_strategy=custom_fb)
    assert p_d._fallback_strategy is custom_fb

    # Security Invariant: ReservedParameterError halts planning immediately
    class ReservedErrorStrategy(Strategy):
        def build_steps(self, intent_result: IntentResult) -> list[PlanStep]:
            raise ReservedParameterError("Reserved prefix '_' detected.")

    p_res = Planner(default_strategy=ReservedErrorStrategy())
    r_norm = IntentResult(Intent.OPEN_APPLICATION, 0.9, "test", {})
    with pytest.raises(ReservedParameterError):
        p_res.plan(r_norm)


def test_runtime_composition_root_integration() -> None:
    """Verifies ArgosRuntime.create_default() injects CapabilityRegistry."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.runtime.argos_runtime import ArgosRuntime

    runtime = ArgosRuntime.create_default(db_path=":memory:")
    try:
        assert runtime.capability_registry is not None
        assert isinstance(runtime.capability_registry, CapabilityRegistry)
        # Check Planner wiring inside PlanningCapability
        planning_cap = runtime.brain_core.capability_manager.get("planning")
        planner = planning_cap._planner  # type: ignore
        assert planner.capability_registry is runtime.capability_registry
    finally:
        runtime.close()


def test_planner_unsupported_action_fallback() -> None:
    """Verifies UnsupportedActionError delegates to FallbackStrategy."""
    from argos.capabilities.capability_registry import CapabilityRegistry

    reg = CapabilityRegistry()
    reg.freeze()
    planner = Planner(capability_registry=reg)

    # DELETE_FILE is unsupported in ARS-004 DomainPlannerStrategy
    result = IntentResult(
        primary_intent=Intent.DELETE_FILE,
        confidence=0.9,
        analysis_engine="test",
        entities={"file": ["old.txt"]},
    )
    plan = planner.plan(result)
    assert len(plan.steps) == 1
    assert plan.steps[0].action == Action.ASK_CLARIFICATION


def test_domain_planner_missing_registry_and_not_found() -> None:
    """Verifies DomainPlannerStrategy error handling when registry is None or empty."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.planning.exceptions import UnsupportedActionError
    from argos.planning.strategy import DomainPlannerStrategy

    # Case 1: None registry
    strat_none = DomainPlannerStrategy(None)
    assert strat_none.capability_registry is None
    with pytest.raises(UnsupportedActionError) as exc1:
        strat_none.build_steps(
            IntentResult(Intent.OPEN_APPLICATION, 0.9, "test", {})
        )
    assert "CapabilityRegistry is not configured" in str(exc1.value)

    # Case 2: Empty registry (action not found)
    reg = CapabilityRegistry()
    reg.freeze()
    strat_empty = DomainPlannerStrategy(reg)
    with pytest.raises(UnsupportedActionError) as exc2:
        strat_empty.build_steps(
            IntentResult(Intent.OPEN_APPLICATION, 0.9, "test", {})
        )
    assert "unsupported by capability domains" in str(exc2.value)


def test_domain_planner_schema_validation_failure_and_unmapped() -> None:
    """Verifies DomainPlannerStrategy validation failure and unmapped entities."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.capabilities.domains.application_domain import ApplicationDomain
    from argos.planning.strategy import DomainPlannerStrategy
    from argos.tools.base_tool import (
        BaseTool,
        ParameterSpec,
        RiskClass,
        ToolManifest,
        ToolResult,
    )

    class StubAppTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="stub_app",
                version="1.0",
                description="Stub app tool",
                supported_actions=("open_app",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="application", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    reg = CapabilityRegistry()
    reg.register_domain(ApplicationDomain())
    reg.index_tool(StubAppTool())
    reg.freeze()

    strat = DomainPlannerStrategy(reg)

    # Validation failure: missing required parameter
    r_missing = IntentResult(Intent.OPEN_APPLICATION, 0.9, "test", {})
    steps_err = strat.build_steps(r_missing)
    assert len(steps_err) == 1
    assert steps_err[0].action == Action.ASK_CLARIFICATION
    assert (
        "Required parameter 'application' is missing"
        in steps_err[0].parameters["message"]
    )

    # Unmapped extra entities collected in metadata
    r_unmapped = IntentResult(
        Intent.OPEN_APPLICATION, 0.9, "test", {"application": ["calc"], "foo": ["bar"]}
    )
    steps_ok = strat.build_steps(r_unmapped)
    assert len(steps_ok) == 1
    assert steps_ok[0].action == Action.OPEN_APP
    assert steps_ok[0].metadata == {"unmapped_entities": {"foo": "bar"}}


def test_domain_planner_entity_aliases() -> None:
    """Verifies domain planner parameter key alias extractions."""
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.capabilities.domains.application_domain import ApplicationDomain
    from argos.capabilities.domains.file_system_domain import FileSystemDomain
    from argos.capabilities.domains.web_domain import WebDomain
    from argos.planning.strategy import DomainPlannerStrategy
    from argos.tools.base_tool import (
        BaseTool,
        ParameterSpec,
        RiskClass,
        ToolManifest,
        ToolResult,
    )

    class StubAppTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="stub_app_alias",
                version="1.0",
                description="Stub app tool",
                supported_actions=("open_app",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="application", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    class StubFileTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="stub_file",
                version="1.0",
                description="Stub file tool",
                supported_actions=("read_file",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="file_path", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    class StubWebTool(BaseTool):
        @property
        def manifest(self) -> ToolManifest:
            return ToolManifest(
                tool_id="stub_web",
                version="1.0",
                description="Stub web tool",
                supported_actions=("search_web",),
                risk_class=RiskClass.READ_ONLY,
                parameter_specs=(ParameterSpec(name="query", param_type=str),),
            )

        def validate_parameters(self, parameters: dict) -> None: ...
        def run(self, parameters: dict) -> ToolResult: return ToolResult(True, "ok")

    reg = CapabilityRegistry()
    reg.register_domain(ApplicationDomain())
    reg.register_domain(FileSystemDomain())
    reg.register_domain(WebDomain())
    reg.index_tool(StubAppTool())
    reg.index_tool(StubFileTool())
    reg.index_tool(StubWebTool())
    reg.freeze()

    strat = DomainPlannerStrategy(reg)

    # Alias 'app' -> 'application'
    r_app = IntentResult(Intent.OPEN_APPLICATION, 0.9, "test", {"app": ["calc"]})
    steps0 = strat.build_steps(r_app)
    assert steps0[0].parameters == {"application": "calc"}

    # Alias 'target' -> 'file_path'
    r_target = IntentResult(Intent.READ_FILE, 0.9, "test", {"target": ["doc.pdf"]})
    steps1 = strat.build_steps(r_target)
    assert steps1[0].parameters == {"file_path": "doc.pdf"}

    # Alias 'url' -> 'query'
    r_url = IntentResult(Intent.SEARCH_WEB, 0.9, "test", {"url": ["example.com"]})
    steps2 = strat.build_steps(r_url)
    assert steps2[0].parameters == {"query": "example.com"}

    # Alias 'website' -> 'query'
    r_site = IntentResult(Intent.SEARCH_WEB, 0.9, "test", {"website": ["example.org"]})
    steps3 = strat.build_steps(r_site)
    assert steps3[0].parameters == {"query": "example.org"}


def test_schema_validator_full_type_coercion_branches() -> None:
    """Verifies all SchemaValidator type coercion and error branches."""
    from argos.capabilities.models import ActionSchemaDescriptor
    from argos.planning.exceptions import (
        InvalidParameterError,
        MissingParameterError,
    )
    from argos.planning.validator import SchemaValidator
    from argos.tools.base_tool import ParameterSpec, RiskClass

    # 1. str parameter coercing int
    spec_str = ParameterSpec(name="text", param_type=str)
    schema_str = ActionSchemaDescriptor(
        Action.OPEN_APP, "tool", RiskClass.READ_ONLY, (spec_str,)
    )
    v1, _ = SchemaValidator.validate_and_coerce(schema_str, {"text": 123})
    assert v1 == {"text": "123"}

    # 2. int parameter failing string coercion
    spec_int = ParameterSpec(name="count", param_type=int)
    schema_int = ActionSchemaDescriptor(
        Action.OPEN_APP, "tool", RiskClass.READ_ONLY, (spec_int,)
    )
    with pytest.raises(InvalidParameterError):
        SchemaValidator.validate_and_coerce(schema_int, {"count": "not_an_int"})

    # 3. float parameter coercing int and float string, and failing
    spec_flt = ParameterSpec(name="ratio", param_type=float)
    schema_flt = ActionSchemaDescriptor(
        Action.OPEN_APP, "tool", RiskClass.READ_ONLY, (spec_flt,)
    )
    v_flt1, _ = SchemaValidator.validate_and_coerce(schema_flt, {"ratio": 42})
    assert v_flt1 == {"ratio": 42.0}
    v_flt2, _ = SchemaValidator.validate_and_coerce(schema_flt, {"ratio": "3.14"})
    assert v_flt2 == {"ratio": 3.14}
    with pytest.raises(InvalidParameterError):
        SchemaValidator.validate_and_coerce(schema_flt, {"ratio": "not_a_float"})

    # 4. bool parameter coercing strings
    spec_bool = ParameterSpec(name="flag", param_type=bool)
    schema_bool = ActionSchemaDescriptor(
        Action.OPEN_APP, "tool", RiskClass.READ_ONLY, (spec_bool,)
    )
    v_b1, _ = SchemaValidator.validate_and_coerce(schema_bool, {"flag": "true"})
    assert v_b1 == {"flag": True}
    v_b2, _ = SchemaValidator.validate_and_coerce(schema_bool, {"flag": "0"})
    assert v_b2 == {"flag": False}
    with pytest.raises(InvalidParameterError):
        SchemaValidator.validate_and_coerce(schema_bool, {"flag": "maybe"})

    # 5. Required parameter with value None -> MissingParameterError
    spec_req = ParameterSpec(name="path", param_type=str, required=True, default=None)
    schema_req = ActionSchemaDescriptor(
        Action.OPEN_APP, "tool", RiskClass.READ_ONLY, (spec_req,)
    )
    with pytest.raises(MissingParameterError):
        SchemaValidator.validate_and_coerce(schema_req, {"path": None})

    # 6. NoneType param_type accepting None
    spec_none = ParameterSpec(name="empty", param_type=type(None), required=False)
    schema_none = ActionSchemaDescriptor(
        Action.OPEN_APP, "tool", RiskClass.READ_ONLY, (spec_none,)
    )
    v_none, _ = SchemaValidator.validate_and_coerce(schema_none, {"empty": None})
    assert v_none == {"empty": None}



