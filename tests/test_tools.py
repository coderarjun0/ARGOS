"""Unit and integration test suite for ARS-002 Tool Runtime subsystem."""

from unittest.mock import Mock, patch

import pytest

from argos.brain.brain_core import BrainCore
from argos.brain.brain_status import BrainStatus
from argos.brain.capability_manager import create_default_capability_manager
from argos.execution.action_router import ActionRouter
from argos.execution.execution_engine import ExecutionEngine
from argos.execution.execution_status import ExecutionStatus
from argos.planning.action import Action
from argos.planning.plan_step import PlanStep
from argos.policy.models import (
    PolicyOutcome,
    PolicyRule,
    PolicyScope,
    RuleOperator,
)
from argos.policy.policy_engine import PolicyEngine
from argos.runtime.argos_runtime import ArgosRuntime
from argos.runtime.models import RuntimeStatus
from argos.tools.adapters.mock_adapter import MockPlatformAdapter
from argos.tools.adapters.win32_adapter import Win32PlatformAdapter
from argos.tools.application_tool import ApplicationLauncherTool
from argos.tools.base_tool import (
    RiskClass,
    SideEffectClass,
    ToolManifest,
    ToolResult,
)
from argos.tools.exceptions import (
    InvalidParameterError,
    PlatformExecutionError,
    ToolError,
    ToolNotFoundError,
    ToolRegistrationError,
)
from argos.tools.tool_executor_adapter import ToolExecutorAdapter
from argos.tools.tool_registry import ToolRegistry


def test_tool_manifest_defaults():
    """Verifies ToolManifest dataclass defaults."""
    manifest = ToolManifest(
        tool_id="test.tool",
        version="1.0.0",
        description="Test tool",
        supported_actions=("test_action",),
    )
    assert manifest.tool_id == "test.tool"
    assert manifest.side_effect == SideEffectClass.READ_ONLY
    assert manifest.is_reversible is False
    assert manifest.default_timeout_seconds == 5.0
    assert manifest.risk_class == RiskClass.READ_ONLY
    assert manifest.parameter_specs == ()


def test_tool_result_defaults():
    """Verifies ToolResult dataclass defaults."""
    res = ToolResult(success=True, message="Success")
    assert res.success is True
    assert res.message == "Success"
    assert res.metadata == {}


def test_application_launcher_tool_validation():
    """Verifies ApplicationLauncherTool parameter validation and whitelisting."""
    mock_platform = MockPlatformAdapter()
    tool = ApplicationLauncherTool(platform_adapter=mock_platform)

    assert tool.manifest.tool_id == "tool.app.launcher"
    assert tool.platform_adapter == mock_platform

    # Valid parameter
    tool.validate_parameters({"application": "calculator"})
    tool.validate_parameters({"application": "calc"})

    # Missing/invalid parameters
    with pytest.raises(InvalidParameterError):
        tool.validate_parameters({})

    with pytest.raises(InvalidParameterError):
        tool.validate_parameters({"application": ""})

    with pytest.raises(InvalidParameterError):
        tool.validate_parameters({"application": 12345})

    # Unmapped application / Injection attempt
    with pytest.raises(InvalidParameterError):
        tool.validate_parameters({"application": "cmd.exe"})

    with pytest.raises(InvalidParameterError):
        tool.validate_parameters({"application": "powershell.exe"})

    with pytest.raises(InvalidParameterError):
        tool.validate_parameters({"application": "../../calc"})


def test_application_launcher_tool_run():
    """Verifies ApplicationLauncherTool execution via platform adapter."""
    mock_platform = MockPlatformAdapter(simulated_pid=1234)
    tool = ApplicationLauncherTool(platform_adapter=mock_platform)

    result = tool.run({"application": "calculator"})
    assert result.success is True
    assert "launched successfully (PID: 1234)" in result.message
    assert result.metadata["pid"] == 1234
    assert mock_platform.launched_history == ["calculator"]

    # Platform failure
    failing_platform = MockPlatformAdapter(should_fail=True)
    failing_tool = ApplicationLauncherTool(platform_adapter=failing_platform)
    with pytest.raises(PlatformExecutionError):
        failing_tool.run({"application": "calculator"})

    # Unexpected exception mapping
    with patch.object(
        mock_platform,
        "launch_known_application",
        side_effect=RuntimeError("OS crash"),
    ):
        with pytest.raises(PlatformExecutionError):
            tool.run({"application": "calculator"})


def test_tool_executor_adapter():
    """Verifies ToolExecutorAdapter bridges ActionExecutor contract."""
    mock_platform = MockPlatformAdapter()
    app_tool = ApplicationLauncherTool(platform_adapter=mock_platform)
    adapter = ToolExecutorAdapter(tool=app_tool)

    assert adapter.tool == app_tool

    # Success step
    step_ok = PlanStep(
        step_id=1, action=Action.OPEN_APP, parameters={"application": "calculator"}
    )
    step_res = adapter.execute(step_ok)
    assert step_res.success is True
    assert "launched successfully" in step_res.message

    # Parameter validation error step
    step_bad = PlanStep(
        step_id=2, action=Action.OPEN_APP, parameters={"application": "malware"}
    )
    step_bad_res = adapter.execute(step_bad)
    assert step_bad_res.success is False
    assert "Parameter validation failed" in step_bad_res.message

    # Tool error step
    with patch.object(
        app_tool, "run", side_effect=ToolError("Tool execution crash")
    ):
        step_err_res = adapter.execute(step_ok)
        assert step_err_res.success is False
        assert "Tool execution error" in step_err_res.message

    # Unexpected exception step
    with patch.object(
        app_tool, "run", side_effect=RuntimeError("System crash")
    ):
        step_uncaught_res = adapter.execute(step_ok)
        assert step_uncaught_res.success is False
        assert "Unexpected error during tool execution" in step_uncaught_res.message


def test_tool_registry():
    """Verifies ToolRegistry registration and lookup."""
    registry = ToolRegistry()
    mock_platform = MockPlatformAdapter()
    app_tool = ApplicationLauncherTool(platform_adapter=mock_platform)

    registry.register(app_tool)
    assert registry.get_tool("tool.app.launcher") == app_tool
    assert registry.list_tools() == [app_tool]

    # Duplicate registration
    with pytest.raises(ToolRegistrationError):
        registry.register(app_tool)

    # Tool not found
    with pytest.raises(ToolNotFoundError):
        registry.get_tool("nonexistent.tool")

    # Get tools for action
    assert registry.get_tools_for_action("open_app") == [app_tool]
    assert registry.get_tools_for_action("unmapped_action") == []


def test_win32_platform_adapter():
    """Verifies Win32PlatformAdapter application resolution and process invocation."""
    adapter = Win32PlatformAdapter()
    assert adapter.platform_name == "win32"

    # Unmapped application
    with pytest.raises(PlatformExecutionError):
        adapter.launch_known_application("unknown_app")

    # Mock subprocess.Popen to verify shell=False and argument list
    mock_proc = Mock(pid=5555)
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        res = adapter.launch_known_application("calculator")
        assert res["pid"] == 5555
        assert res["binary"] == "calc.exe"
        assert res["detached"] is True
        mock_popen.assert_called_once_with(["calc.exe"], shell=False)

    # Subprocess failure handling
    with patch("subprocess.Popen", side_effect=OSError("Access denied")):
        with pytest.raises(PlatformExecutionError):
            adapter.launch_known_application("calculator")


def test_policy_layer1_and_layer2_tool_gate():
    """Verifies Layer 1 and Layer 2 Policy Gate enforcement with real tool adapter."""
    p_engine = PolicyEngine()
    mock_platform = MockPlatformAdapter()
    app_tool = ApplicationLauncherTool(platform_adapter=mock_platform)
    app_adapter = ToolExecutorAdapter(tool=app_tool)

    router = ActionRouter()
    router.register(Action.OPEN_APP, app_adapter)

    exec_engine = ExecutionEngine(router=router, policy_engine=p_engine)
    cap_mgr = create_default_capability_manager(
        execution_engine=exec_engine, policy_engine=p_engine
    )
    brain = BrainCore(capability_manager=cap_mgr)

    # 1. ALLOW outcome -> Real tool execution
    res_allow = brain.process("open calculator")
    assert res_allow.brain_status == BrainStatus.COMPLETED
    assert res_allow.execution_result.status == ExecutionStatus.SUCCESS
    assert "launched successfully" in res_allow.execution_result.step_results[0].message
    assert mock_platform.launched_history == ["calculator"]

    # 2. DENY outcome -> Blocked at Layer 2 policy gate
    p_engine.register_user_rule(
        PolicyRule(
            rule_id="DENY_CALC",
            scope=PolicyScope.USER_POLICY,
            target_capability="execution",
            target_action="open_app",
            parameter_name="application",
            operator=RuleOperator.EQUALS,
            expected_value="calculator",
            outcome=PolicyOutcome.DENY,
            explanation="Prohibited by user policy",
        )
    )

    res_deny = brain.process("open calculator")
    assert res_deny.execution_result.status == ExecutionStatus.FAILED
    assert "Policy DENY" in res_deny.execution_result.step_results[0].message


def test_mock_platform_adapter_coverage():
    """Verifies MockPlatformAdapter platform_name and unmapped application handling."""
    mock_platform = MockPlatformAdapter()
    assert mock_platform.platform_name == "mock"

    with pytest.raises(PlatformExecutionError) as exc_info:
        mock_platform.launch_known_application("unmapped_app")
    assert "is not in the mock approved list" in str(exc_info.value)


def test_runtime_end_to_end_real_tool_launch():
    """Verifies ArgosRuntime end-to-end execution with MockPlatformAdapter."""
    mock_platform = MockPlatformAdapter(simulated_pid=7777)
    with ArgosRuntime.create_default(
        db_path=":memory:", platform_adapter=mock_platform
    ) as runtime:
        response = runtime.handle("open calculator")
        assert response.status == RuntimeStatus.SUCCESS
        assert "launched successfully (PID: 7777)" in response.output
        assert "(simulated)" not in response.output
        assert mock_platform.launched_history == ["calculator"]
