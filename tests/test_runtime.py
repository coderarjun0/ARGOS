"""Integration test suite for ARS-001 ARGOS Runtime Subsystem."""

import runpy
import sys
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from argos.brain.brain_core import BrainCore
from argos.brain.brain_status import BrainStatus
from argos.brain.capability_manager import create_default_capability_manager
from argos.brain.exceptions import MaxCyclesExceededError, ProcessingError
from argos.execution.exceptions import ExecutionError
from argos.execution.execution_result import ExecutionResult
from argos.execution.execution_status import ExecutionStatus
from argos.execution.step_result import StepResult
from argos.intent.exceptions import IntentAnalysisError
from argos.memory.models import AuthorizationRecord, AuthorizationType
from argos.planning.action import Action
from argos.planning.exceptions import PlanningError
from argos.policy.exceptions import PolicyEvaluationError
from argos.policy.models import (
    PolicyOutcome,
    PolicyRule,
    PolicyScope,
    RuleOperator,
)
from argos.policy.policy_engine import PolicyEngine
from argos.runtime.argos_runtime import ArgosRuntime
from argos.runtime.cli import main as cli_main
from argos.runtime.exceptions import (
    RuntimeError,
    RuntimeInitializationError,
    RuntimeShutdownError,
)
from argos.runtime.models import RuntimeResponse, RuntimeStatus


def test_runtime_construction_and_wiring():
    """Verifies ArgosRuntime construction, factory instantiation, and getters."""
    runtime = ArgosRuntime.create_default(db_path=":memory:")
    assert runtime.brain_core is not None
    assert runtime.memory_engine is not None
    assert runtime.policy_engine is not None
    assert not runtime.is_shutdown
    runtime.close()
    assert runtime.is_shutdown


def test_runtime_non_win32_platform_default():
    """Verifies default platform adapter creation on non-win32 platforms."""
    with patch("sys.platform", "linux"):
        runtime = ArgosRuntime.create_default(db_path=":memory:")
        assert runtime.brain_core is not None
        runtime.close()


def test_runtime_single_request_open_app():
    """Verifies end-to-end execution of 'open calculator' returning SUCCESS."""
    with ArgosRuntime.create_default(db_path=":memory:") as runtime:
        response: RuntimeResponse = runtime.handle("open calculator")
        assert response.status == RuntimeStatus.SUCCESS
        assert response.session_id == "default"
        assert "calculator" in response.output.lower()
        assert response.brain_result is not None
        assert response.brain_result.brain_status == BrainStatus.COMPLETED


def test_runtime_sequential_session_requests():
    """Verifies multiple requests in the same session maintain turn history."""
    with ArgosRuntime.create_default(db_path=":memory:") as runtime:
        res1 = runtime.handle("open calculator", session_id="session_100")
        assert res1.status == RuntimeStatus.SUCCESS

        res2 = runtime.handle("open notepad", session_id="session_100")
        assert res2.status == RuntimeStatus.SUCCESS
        assert res2.brain_result is not None


def test_runtime_policy_denial_flow():
    """Verifies destructive system commands require confirmation or policy handling."""
    with ArgosRuntime.create_default(db_path=":memory:") as runtime:
        response = runtime.handle("rm -rf /")
        assert response.status in (
            RuntimeStatus.POLICY_DENIED,
            RuntimeStatus.WAITING_FOR_USER,
        )
        assert response.brain_result is not None


def test_runtime_waiting_for_user_policy_confirmation():
    """Verifies policy requiring confirmation returns WAITING_FOR_USER."""
    p_engine = PolicyEngine()
    p_engine.register_user_rule(
        PolicyRule(
            rule_id="CONFIRM_CALC",
            scope=PolicyScope.USER_POLICY,
            target_capability="execution",
            target_action="*",
            parameter_name=None,
            operator=RuleOperator.EQUALS,
            expected_value="*",
            outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
            explanation="Require explicit confirmation before launching calculator",
        )
    )
    cap_mgr = create_default_capability_manager(policy_engine=p_engine)
    brain = BrainCore(capability_manager=cap_mgr)
    runtime = ArgosRuntime(brain_core=brain, policy_engine=p_engine)

    response = runtime.handle("open calculator", session_id="sess_confirm")
    assert response.status == RuntimeStatus.WAITING_FOR_USER
    assert response.brain_result is not None
    assert response.brain_result.brain_status == BrainStatus.WAITING_FOR_USER
    runtime.close()


def test_runtime_authorization_resume_flow():
    """Verifies resuming a WAITING_FOR_USER session with AuthorizationRecord."""
    p_engine = PolicyEngine()
    p_engine.register_user_rule(
        PolicyRule(
            rule_id="CONFIRM_NOTEPAD",
            scope=PolicyScope.USER_POLICY,
            target_capability="execution",
            target_action="*",
            parameter_name=None,
            operator=RuleOperator.EQUALS,
            expected_value="*",
            outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
            explanation="Require confirmation for notepad",
        )
    )
    cap_mgr = create_default_capability_manager(policy_engine=p_engine)
    brain = BrainCore(capability_manager=cap_mgr)
    runtime = ArgosRuntime(brain_core=brain, policy_engine=p_engine)

    # First turn pauses at WAITING_FOR_USER
    res1 = runtime.handle("open notepad", session_id="sess_auth")
    assert res1.status == RuntimeStatus.WAITING_FOR_USER

    # Second turn with authorization completes execution
    auth = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at=datetime.now(UTC),
    )
    res2 = runtime.handle(
        "open notepad", session_id="sess_auth", authorization=auth
    )
    assert res2.status == RuntimeStatus.SUCCESS
    assert res2.brain_result is not None
    assert res2.brain_result.brain_status == BrainStatus.COMPLETED
    runtime.close()


def test_runtime_malformed_input_error_handling():
    """Verifies empty input request returns MALFORMED_INPUT."""
    with ArgosRuntime.create_default(db_path=":memory:") as runtime:
        response = runtime.handle("")
        assert response.status == RuntimeStatus.MALFORMED_INPUT
        assert response.error_message is not None


def test_runtime_execution_failure_handling():
    """Verifies step execution failure returns EXECUTION_FAILED."""
    with ArgosRuntime.create_default(db_path=":memory:") as runtime:
        failed_exec_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            step_results=[
                StepResult(
                    step_id=1,
                    action=Action.OPEN_APP,
                    success=False,
                    message="Process launch failed",
                )
            ],
            metadata={"error": "Process launch failed"},
        )
        exec_cap = runtime.brain_core._capability_manager.get("execution")
        with patch.object(
            exec_cap._engine, "execute", return_value=failed_exec_result
        ):
            response = runtime.handle("open calculator")
            assert response.status == RuntimeStatus.EXECUTION_FAILED
            assert response.error_message == "Process launch failed"


def test_runtime_layer2_policy_denial_handling():
    """Verifies Layer 2 policy denial inside ExecutionEngine returns POLICY_DENIED."""
    p_engine = PolicyEngine()
    p_engine.register_user_rule(
        PolicyRule(
            rule_id="DENY_CALC_EXEC",
            scope=PolicyScope.USER_POLICY,
            target_capability="execution",
            target_action="open_app",
            parameter_name="application",
            operator=RuleOperator.EQUALS,
            expected_value="calculator",
            outcome=PolicyOutcome.DENY,
            explanation="Deny calculator execution",
        )
    )
    cap_mgr = create_default_capability_manager(policy_engine=p_engine)
    brain = BrainCore(capability_manager=cap_mgr)
    runtime = ArgosRuntime(brain_core=brain, policy_engine=p_engine)

    response = runtime.handle("open calculator")
    assert response.status == RuntimeStatus.POLICY_DENIED
    assert response.brain_result is not None
    runtime.close()


def test_runtime_domain_exception_handling():
    """Verifies Intent, Planning, and Execution exception mappings."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)

    with patch.object(
        brain, "process", side_effect=IntentAnalysisError("Unresolved intent")
    ):
        res_intent = runtime.handle("asdfghjkl")
        assert res_intent.status == RuntimeStatus.INTENT_UNRESOLVED

    with patch.object(
        brain, "process", side_effect=PlanningError("Planner broken")
    ):
        res_plan = runtime.handle("open calculator")
        assert res_plan.status == RuntimeStatus.PLANNING_FAILED

    with patch.object(
        brain, "process", side_effect=ExecutionError("Router error")
    ):
        res_exec = runtime.handle("open calculator")
        assert res_exec.status == RuntimeStatus.EXECUTION_FAILED

    with patch.object(
        brain, "process", side_effect=RuntimeError("System core failure")
    ):
        res_sys = runtime.handle("open calculator")
        assert res_sys.status == RuntimeStatus.SYSTEM_ERROR

    runtime.close()


def test_runtime_graceful_shutdown():
    """Verifies close() marks is_shutdown and cleans up resources."""
    runtime = ArgosRuntime.create_default(db_path=":memory:")
    assert not runtime.is_shutdown
    runtime.close()
    assert runtime.is_shutdown


def test_runtime_idempotent_shutdown():
    """Verifies multiple calls to close() are idempotent."""
    runtime = ArgosRuntime.create_default(db_path=":memory:")
    runtime.close()
    runtime.close()
    assert runtime.is_shutdown


def test_runtime_handle_after_shutdown_raises_exception():
    """Verifies calling handle() after close() raises RuntimeShutdownError."""
    runtime = ArgosRuntime.create_default(db_path=":memory:")
    runtime.close()
    with pytest.raises(RuntimeShutdownError):
        runtime.handle("open calculator")


def test_runtime_context_manager_usage():
    """Verifies runtime context manager auto-closes on exit."""
    with ArgosRuntime.create_default(db_path=":memory:") as runtime:
        assert not runtime.is_shutdown
    assert runtime.is_shutdown


def test_runtime_initialization_error():
    """Verifies factory failure raises RuntimeInitializationError."""
    with patch(
        "argos.runtime.argos_runtime.MemoryEngine",
        side_effect=RuntimeError("DB access denied"),
    ):
        with pytest.raises(RuntimeInitializationError):
            ArgosRuntime.create_default(db_path="invalid_path")


def test_cli_main_run_subcommand(capsys):
    """Verifies CLI run subcommand executes request and outputs result."""
    exit_code = cli_main(["run", "open calculator"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Status: success" in captured.out
    assert "Output:" in captured.out


def test_cli_main_no_args_and_help(capsys):
    """Verifies CLI without subcommands prints help and exits cleanly."""
    exit_code = cli_main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "argos" in captured.out.lower()


def test_cli_main_interactive_mode(capsys):
    """Verifies CLI interactive REPL loop processes inputs until exit."""
    user_inputs = ["open calculator", "exit"]
    with patch("builtins.input", side_effect=user_inputs):
        exit_code = cli_main(["interactive"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "ARGOS Interactive Session" in captured.out
        assert "[success]" in captured.out
        assert "Ending session." in captured.out


def test_runtime_max_cycles_and_policy_eval_exception_mapping():
    """Verifies MaxCyclesExceededError and PolicyEvaluationError handling."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)

    with patch.object(
        brain, "process", side_effect=MaxCyclesExceededError("Max cycles limit")
    ):
        res_max = runtime.handle("open calculator")
        assert res_max.status == RuntimeStatus.MAX_CYCLES_EXCEEDED
        assert res_max.error_message == "Max cycles limit"

    with patch.object(
        brain, "process", side_effect=PolicyEvaluationError("Policy req auth")
    ):
        res_pol = runtime.handle("open calculator")
        assert res_pol.status == RuntimeStatus.WAITING_FOR_USER
        assert res_pol.output == "Policy req auth"

    with patch.object(
        brain, "process", side_effect=ProcessingError("Capability crash")
    ):
        res_proc = runtime.handle("open calculator")
        assert res_proc.status == RuntimeStatus.SYSTEM_ERROR
        assert res_proc.error_message == "Capability crash"

    runtime.close()


def test_runtime_map_brain_result_max_cycles_and_no_exec():
    """Verifies brain_status TERMINATED and empty result formatting."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)

    # 1. TERMINATED brain status
    b_res_max = Mock(
        brain_status=BrainStatus.TERMINATED,
        execution_result=None,
        decision_history=["Decision 1"],
    )
    with patch.object(brain, "process", return_value=b_res_max):
        res_max = runtime.handle("open calculator")
        assert res_max.status == RuntimeStatus.MAX_CYCLES_EXCEEDED
        assert res_max.output == "Decision 1"

    # 2. No execution result and empty decision history -> 'Operation completed.'
    b_res_empty = Mock(
        brain_status=BrainStatus.COMPLETED,
        execution_result=None,
        decision_history=[],
    )
    with patch.object(brain, "process", return_value=b_res_empty):
        res_empty = runtime.handle("open calculator")
        assert res_empty.status == RuntimeStatus.SUCCESS
        assert res_empty.output == "Operation completed."

    runtime.close()


def test_runtime_close_memory_engine_exception():
    """Verifies MemoryEngine close exception is safely caught during close."""
    mem_mock = Mock()
    mem_mock.close.side_effect = RuntimeError("Close failed")
    runtime = ArgosRuntime(brain_core=BrainCore(), memory_engine=mem_mock)
    runtime.close()
    assert runtime.is_shutdown


def test_cli_main_run_with_error_and_invalid_command(capsys):
    """Verifies CLI run output with error message, and unknown command."""
    with patch.object(
        ArgosRuntime,
        "handle",
        return_value=Mock(
            status=RuntimeStatus.POLICY_DENIED,
            output="",
            error_message="Policy denied",
        ),
    ):
        exit_code = cli_main(["run", "rm -rf /"])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Status: policy_denied" in captured.out
        assert "Error:  Policy denied" in captured.out

    with pytest.raises(SystemExit):
        cli_main(["unknown_command"])


def test_cli_main_interactive_empty_input_and_eof(capsys):
    """Verifies CLI interactive mode handles empty input and KeyboardInterrupt."""
    inputs = ["", "open calculator", "quit"]
    with patch("builtins.input", side_effect=inputs):
        exit_code = cli_main(["interactive"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "ARGOS Interactive Session" in captured.out

    with patch("builtins.input", side_effect=KeyboardInterrupt):
        exit_code_int = cli_main(["interactive"])
        assert exit_code_int == 0
        captured_int = capsys.readouterr()
        assert "Ending session." in captured_int.out


def test_runtime_processing_error_policy_deny():
    """Verifies ProcessingError with DENY in message hits POLICY_DENIED block."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)
    err = ProcessingError("Capability policy DENY: Action blocked")
    with patch.object(brain, "process", side_effect=err):
        res = runtime.handle("open calculator")
        assert res.status == RuntimeStatus.POLICY_DENIED
        assert "DENY" in res.error_message
    runtime.close()


def test_runtime_completed_status_with_failed_execution_no_metadata_error():
    """Verifies COMPLETED status with failed execution and metadata fallback."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)
    failed_exec = ExecutionResult(
        status=ExecutionStatus.FAILED,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.OPEN_APP,
                success=False,
                message="App execution failed cleanly",
            )
        ],
        metadata={},
    )
    b_res = Mock(brain_status=BrainStatus.COMPLETED, execution_result=failed_exec)
    with patch.object(brain, "process", return_value=b_res):
        res = runtime.handle("open calculator")
        assert res.status == RuntimeStatus.EXECUTION_FAILED
        assert res.error_message == "App execution failed cleanly"
    runtime.close()


def test_runtime_completed_status_with_policy_deny_execution():
    """Verifies COMPLETED status with policy DENY execution step maps correctly."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)
    failed_exec = ExecutionResult(
        status=ExecutionStatus.FAILED,
        step_results=[
            StepResult(
                step_id=1,
                action=Action.OPEN_APP,
                success=False,
                message="Policy DENY: Action blocked",
            )
        ],
        metadata={},
    )
    b_res = Mock(brain_status=BrainStatus.COMPLETED, execution_result=failed_exec)
    with patch.object(brain, "process", return_value=b_res):
        res = runtime.handle("open calculator")
        assert res.status == RuntimeStatus.POLICY_DENIED
        assert res.error_message == "Policy DENY: Action blocked"
    runtime.close()


def test_runtime_completed_status_with_failed_execution():
    """Verifies COMPLETED status with failed execution maps to EXECUTION_FAILED."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)
    failed_exec = Mock(
        status=ExecutionStatus.FAILED,
        metadata={"error": "Step error"},
        step_results=[Mock(message="Step error")],
    )
    b_res = Mock(brain_status=BrainStatus.COMPLETED, execution_result=failed_exec)
    with patch.object(brain, "process", return_value=b_res):
        res = runtime.handle("open calculator")
        assert res.status == RuntimeStatus.EXECUTION_FAILED
        assert res.error_message == "Step error"
    runtime.close()


def test_runtime_map_brain_result_fallback_status():
    """Verifies fallback RuntimeResponse return for unmapped brain status."""
    brain = BrainCore()
    runtime = ArgosRuntime(brain_core=brain)
    b_res = Mock(
        brain_status=BrainStatus.RUNNING, execution_result=None, decision_history=[]
    )
    with patch.object(brain, "process", return_value=b_res):
        res = runtime.handle("open calculator")
        assert res.status == RuntimeStatus.SUCCESS
    runtime.close()


def test_cli_main_fallback_and_module_execution(capsys):
    """Verifies CLI fallback return 0 and __main__ module execution."""
    with patch(
        "argparse.ArgumentParser.parse_args", return_value=Mock(command="unhandled")
    ):
        assert cli_main([]) == 0

    with patch.object(sys, "argv", ["argos", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("argos.runtime.cli", run_name="__main__")
        assert exc_info.value.code == 0
