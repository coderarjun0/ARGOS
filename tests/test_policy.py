"""Comprehensive Unit & Integration Test Suite for ADS-007 Policy Engine Subsystem."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from argos.brain.brain_core import BrainCore
from argos.brain.brain_status import BrainStatus
from argos.brain.capability_manager import (
    create_default_capability_manager,
)
from argos.brain.exceptions import ProcessingError
from argos.execution.execution_engine import ExecutionEngine
from argos.input.input_request import InputRequest
from argos.memory.models import AuthorizationRecord, AuthorizationType
from argos.planning.action import Action
from argos.planning.plan import Plan
from argos.planning.plan_step import PlanStep
from argos.policy.constants import (
    CAPABILITY_POLICY,
    WILDCARD_SYMBOL,
)
from argos.policy.evaluator import (
    evaluate_rule_condition,
    get_rule_specificity,
    resolve_canonical_decision,
)
from argos.policy.exceptions import (
    PolicyEngineError,
    PolicyEvaluationError,
    PolicyInitializationError,
    PolicyValidationError,
)
from argos.policy.models import (
    PolicyDecision,
    PolicyOutcome,
    PolicyRule,
    PolicyScope,
    RuleOperator,
)
from argos.policy.policy_capability import PolicyCapability
from argos.policy.policy_engine import PolicyEngine
from argos.policy.predicates import (
    is_arbitrary_code_payload,
    is_destructive_system_command,
    is_system_directory_path,
)


class DummyMemoryRecord:
    """Dummy MemoryRecord container for testing."""

    def __init__(self, value: dict):
        """Initializes DummyMemoryRecord with dictionary value."""
        self.value = value


class MockMemoryEngine:
    """Mock MemoryEngine for policy testing."""

    def __init__(self, records: list | None = None, fail: bool = False):
        """Initializes MockMemoryEngine."""
        self._records = records or []
        self._fail = fail

    def list_by_category(self, category: str) -> list:
        """Mock list_by_category implementation."""
        if self._fail:
            raise RuntimeError("Database connection failed.")
        return self._records


# ============================================================================
# 1. FOUNDATION TESTS
# ============================================================================


def test_policy_enums():
    """Verifies policy enums."""
    assert PolicyOutcome.ALLOW.value == "allow"
    assert PolicyOutcome.DENY.value == "deny"
    assert PolicyOutcome.REQUIRE_CONFIRMATION.value == "require_confirmation"
    assert PolicyOutcome.REQUIRE_AUTHORIZATION.value == "require_authorization"

    assert PolicyScope.CONSTITUTION.value == "constitution"
    assert PolicyScope.SYSTEM_IMMUTABLE.value == "system_immutable"
    assert PolicyScope.SYSTEM_SECURITY.value == "system_security"
    assert PolicyScope.USER_POLICY.value == "user_policy"
    assert PolicyScope.CONTEXTUAL.value == "contextual"
    assert PolicyScope.DEFAULT_FALLBACK.value == "default_fallback"

    assert RuleOperator.EQUALS.value == "equals"
    assert RuleOperator.REGEX_MATCH.value == "regex_match"


def test_policy_rule_and_decision_models():
    """Verifies PolicyRule and PolicyDecision models."""
    rule = PolicyRule(
        rule_id="RULE_001",
        scope=PolicyScope.USER_POLICY,
        target_capability="execution",
        target_action="run_command",
        parameter_name="command",
        operator=RuleOperator.CONTAINS,
        expected_value="sudo",
        outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
        explanation="Require confirmation for sudo commands.",
    )
    assert rule.rule_id == "RULE_001"
    assert rule.scope == PolicyScope.USER_POLICY

    now = datetime.now(UTC)
    decision = PolicyDecision(
        outcome=PolicyOutcome.ALLOW,
        matched_rule_id="RULE_001",
        scope=PolicyScope.USER_POLICY,
        explanation="Allowed by user rule.",
        timestamp=now,
    )
    assert decision.outcome == PolicyOutcome.ALLOW
    assert decision.matched_rule_id == "RULE_001"


def test_policy_exceptions():
    """Verifies policy exception hierarchy."""
    err = PolicyEngineError("Base policy error")
    assert isinstance(err, Exception)

    init_err = PolicyInitializationError("Init failed")
    assert isinstance(init_err, PolicyEngineError)

    val_err = PolicyValidationError("Invalid rule")
    assert isinstance(val_err, PolicyEngineError)

    eval_err = PolicyEvaluationError("Denied")
    assert isinstance(eval_err, PolicyEngineError)


# ============================================================================
# 2. EVALUATOR & OPERATORS TESTS
# ============================================================================


def test_rule_operator_matching():
    """Verifies rule operator condition matching logic."""
    # EQUALS / NOT_EQUALS
    r_eq = PolicyRule(
        "1",
        PolicyScope.USER_POLICY,
        "execution",
        "delete_file",
        "target",
        RuleOperator.EQUALS,
        "test.txt",
        PolicyOutcome.DENY,
        "exp",
    )
    assert evaluate_rule_condition(
        r_eq, "execution", "delete_file", {"target": "test.txt"}
    ) is True
    assert evaluate_rule_condition(
        r_eq, "execution", "delete_file", {"target": "other.txt"}
    ) is False

    r_neq = PolicyRule(
        "2",
        PolicyScope.USER_POLICY,
        "execution",
        "delete_file",
        "target",
        RuleOperator.NOT_EQUALS,
        "test.txt",
        PolicyOutcome.DENY,
        "exp",
    )
    assert evaluate_rule_condition(
        r_neq, "execution", "delete_file", {"target": "other.txt"}
    ) is True

    # CONTAINS / NOT_CONTAINS
    r_cont = PolicyRule(
        "3",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.CONTAINS,
        "format",
        PolicyOutcome.DENY,
        "exp",
    )
    assert evaluate_rule_condition(
        r_cont, "execution", "run_command", {"command": "format c:"}
    ) is True
    assert evaluate_rule_condition(
        r_cont, "execution", "run_command", {"command": "dir"}
    ) is False

    r_ncont = PolicyRule(
        "4",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.NOT_CONTAINS,
        "format",
        PolicyOutcome.DENY,
        "exp",
    )
    assert evaluate_rule_condition(
        r_ncont, "execution", "run_command", {"command": "dir"}
    ) is True

    # PREFIX_MATCH / SUFFIX_MATCH
    r_pref = PolicyRule(
        "5",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.PREFIX_MATCH,
        "git",
        PolicyOutcome.ALLOW,
        "exp",
    )
    assert evaluate_rule_condition(
        r_pref, "execution", "run_command", {"command": "git status"}
    ) is True

    r_suff = PolicyRule(
        "6",
        PolicyScope.USER_POLICY,
        "execution",
        "write_file",
        "target",
        RuleOperator.SUFFIX_MATCH,
        ".py",
        PolicyOutcome.ALLOW,
        "exp",
    )
    assert evaluate_rule_condition(
        r_suff, "execution", "write_file", {"target": "main.py"}
    ) is True

    # REGEX_MATCH
    r_reg = PolicyRule(
        "7",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.REGEX_MATCH,
        r"^rm\s+-rf",
        PolicyOutcome.DENY,
        "exp",
    )
    assert evaluate_rule_condition(
        r_reg, "execution", "run_command", {"command": "rm -rf /tmp"}
    ) is True

    # IN_LIST / NOT_IN_LIST
    r_in = PolicyRule(
        "8",
        PolicyScope.USER_POLICY,
        "execution",
        "open_app",
        "target",
        RuleOperator.IN_LIST,
        "notepad, calc, cmd",
        PolicyOutcome.ALLOW,
        "exp",
    )
    assert (
        evaluate_rule_condition(
            r_in, "execution", "open_app", {"target": "notepad"}
        )
        is True
    )
    assert (
        evaluate_rule_condition(
            r_in, "execution", "open_app", {"target": "browser"}
        )
        is False
    )

    r_nin = PolicyRule(
        "9",
        PolicyScope.USER_POLICY,
        "execution",
        "open_app",
        "target",
        RuleOperator.NOT_IN_LIST,
        "notepad, calc",
        PolicyOutcome.DENY,
        "exp",
    )
    assert (
        evaluate_rule_condition(
            r_nin, "execution", "open_app", {"target": "malware"}
        )
        is True
    )


def test_rule_specificity_ranking():
    """Verifies rule specificity ranking logic."""
    r0 = PolicyRule(
        "R0",
        PolicyScope.USER_POLICY,
        WILDCARD_SYMBOL,
        WILDCARD_SYMBOL,
        None,
        RuleOperator.EQUALS,
        "x",
        PolicyOutcome.ALLOW,
        "",
    )
    r1 = PolicyRule(
        "R1",
        PolicyScope.USER_POLICY,
        "execution",
        WILDCARD_SYMBOL,
        None,
        RuleOperator.EQUALS,
        "x",
        PolicyOutcome.ALLOW,
        "",
    )
    r2 = PolicyRule(
        "R2",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        None,
        RuleOperator.EQUALS,
        "x",
        PolicyOutcome.ALLOW,
        "",
    )
    r3 = PolicyRule(
        "R3",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.EQUALS,
        "x",
        PolicyOutcome.ALLOW,
        "",
    )

    assert get_rule_specificity(r0) == 0
    assert get_rule_specificity(r1) == 1
    assert get_rule_specificity(r2) == 2
    assert get_rule_specificity(r3) == 3


def test_canonical_conflict_resolution():
    """Verifies canonical 4-step conflict resolution algorithm."""
    r_sys = PolicyRule(
        "SYS_001",
        PolicyScope.SYSTEM_IMMUTABLE,
        "execution",
        "run_command",
        "command",
        RuleOperator.CONTAINS,
        "format",
        PolicyOutcome.DENY,
        "System deny",
    )
    r_usr = PolicyRule(
        "USR_001",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.CONTAINS,
        "format",
        PolicyOutcome.ALLOW,
        "User allow",
    )

    # Scope Precedence: SYSTEM_IMMUTABLE beats USER_POLICY
    winner = resolve_canonical_decision([r_usr, r_sys])
    assert winner is not None
    assert winner.rule_id == "SYS_001"
    assert winner.outcome == PolicyOutcome.DENY

    # Deny-Override at same scope
    r_u1 = PolicyRule(
        "A_USR_001",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.CONTAINS,
        "sudo",
        PolicyOutcome.ALLOW,
        "Allow",
    )
    r_u2 = PolicyRule(
        "B_USR_002",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        "command",
        RuleOperator.CONTAINS,
        "sudo",
        PolicyOutcome.DENY,
        "Deny",
    )
    winner2 = resolve_canonical_decision([r_u1, r_u2])
    assert winner2 is not None
    assert winner2.outcome == PolicyOutcome.DENY

    # Deterministic Tie-break by rule_id when same scope, specificity, and severity
    r_t1 = PolicyRule(
        "RULE_B",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        None,
        RuleOperator.EQUALS,
        WILDCARD_SYMBOL,
        PolicyOutcome.REQUIRE_CONFIRMATION,
        "Exp B",
    )
    r_t2 = PolicyRule(
        "RULE_A",
        PolicyScope.USER_POLICY,
        "execution",
        "run_command",
        None,
        RuleOperator.EQUALS,
        WILDCARD_SYMBOL,
        PolicyOutcome.REQUIRE_CONFIRMATION,
        "Exp A",
    )
    winner3 = resolve_canonical_decision([r_t1, r_t2])
    assert winner3 is not None
    assert winner3.rule_id == "RULE_A"


# ============================================================================
# 3. PREDICATES & SYSTEM RULES TESTS
# ============================================================================


def test_safety_predicates():
    """Verifies inspectable safety predicates."""
    assert is_system_directory_path("C:\\Windows\\System32\\cmd.exe") is True
    assert is_system_directory_path("C:\\Program Files\\App\\run.exe") is True
    assert is_system_directory_path("/etc/passwd") is True
    assert is_system_directory_path("/usr/local/bin") is True
    assert is_system_directory_path("C:\\Users\\Ram kishor\\document.txt") is False

    assert is_destructive_system_command("rm -rf /") is True
    assert is_destructive_system_command("format C:") is True
    assert is_destructive_system_command("git status") is False

    assert is_arbitrary_code_payload("eval('import os')") is True
    assert is_arbitrary_code_payload("exec('system')") is True
    assert is_arbitrary_code_payload("hello world") is False


def test_policy_engine_builtin_evaluations():
    """Verifies built-in evaluation logic."""
    engine = PolicyEngine()

    # System directory deletion attempt -> DENY
    d1 = engine.evaluate_action(
        "delete_file", target="C:\\Windows\\System32\\kernel.dll"
    )
    assert d1.outcome == PolicyOutcome.DENY
    assert d1.scope in (PolicyScope.CONSTITUTION, PolicyScope.SYSTEM_IMMUTABLE)

    # Destructive format command -> DENY
    d2 = engine.evaluate_action("run_command", parameters={"command": "format C:"})
    assert d2.outcome == PolicyOutcome.DENY

    # Executable file creation -> REQUIRE_CONFIRMATION
    d3 = engine.evaluate_action("write_file", target="script.bat")
    assert d3.outcome == PolicyOutcome.REQUIRE_CONFIRMATION

    # Safe perception input -> ALLOW
    d4 = engine.evaluate_capability("input", "process")
    assert d4.outcome == PolicyOutcome.ALLOW


# ============================================================================
# 4. STORAGE INTEGRATION & USER RULES TESTS
# ============================================================================


def test_policy_engine_user_rule_registration_and_reload():
    """Verifies user rule registration and reloading."""
    rec = DummyMemoryRecord({
        "rule_id": "USR_ALLOW_GIT",
        "scope": "user_policy",
        "target_capability": "execution",
        "target_action": "run_command",
        "parameter_name": "command",
        "operator": "prefix_match",
        "expected_value": "git",
        "outcome": "allow",
        "explanation": "Allow git commands.",
    })
    mock_mem = MockMemoryEngine([rec])
    engine = PolicyEngine(memory_engine=mock_mem)

    # Should allow git command based on loaded user rule
    dec = engine.evaluate_action("run_command", parameters={"command": "git status"})
    assert dec.outcome == PolicyOutcome.ALLOW
    assert dec.matched_rule_id == "USR_ALLOW_GIT"


def test_register_user_rule_validation():
    """Verifies rule registration validation."""
    engine = PolicyEngine()
    invalid_rule = PolicyRule(
        rule_id="SYS_OVERRIDE",
        scope=PolicyScope.SYSTEM_IMMUTABLE,
        target_capability="execution",
        target_action="run_command",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.ALLOW,
        explanation="Attempted invalid override",
    )
    with pytest.raises(PolicyValidationError):
        engine.register_user_rule(invalid_rule)


def test_storage_failure_failsafe_semantics():
    """Verifies storage failure failsafe semantics."""
    mock_fail_mem = MockMemoryEngine(fail=True)
    engine = PolicyEngine(memory_engine=mock_fail_mem)
    assert engine._storage_available is False

    # Safe perception read should still be ALLOW
    d_safe = engine.evaluate_capability("input", "process")
    assert d_safe.outcome == PolicyOutcome.ALLOW

    # High-risk write action without storage should fail closed DENY
    d_risk = engine.evaluate_action("write_file", target="data.bin")
    assert d_risk.outcome == PolicyOutcome.DENY


# ============================================================================
# 5. CAPABILITYMANAGER GATEWAY (LAYER 1) TESTS
# ============================================================================


def test_capability_manager_layer1_policy_gateway():
    """Verifies CapabilityManager Layer 1 Policy Gateway."""
    p_engine = PolicyEngine()

    # User rule to DENY intent analysis capability
    deny_intent_rule = PolicyRule(
        rule_id="DENY_INTENT_CAP",
        scope=PolicyScope.USER_POLICY,
        target_capability="intent",
        target_action="*",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.DENY,
        explanation="Intent capability denied by policy.",
    )
    p_engine.register_user_rule(deny_intent_rule)

    mgr = create_default_capability_manager(policy_engine=p_engine)

    # Invoking intent capability should raise ProcessingError due to Policy DENY
    with pytest.raises(ProcessingError, match="failed with policy DENY"):
        mgr.execute("intent", "analyze")


def test_policy_capability_adapter():
    """Verifies PolicyCapability adapter."""
    engine = PolicyEngine()
    cap = PolicyCapability(engine)
    assert cap.name == CAPABILITY_POLICY
    assert cap.engine is engine

    dec = cap.execute(
        "evaluate_capability", capability_name="input", action="process"
    )
    assert isinstance(dec, PolicyDecision)
    assert dec.outcome == PolicyOutcome.ALLOW


# ============================================================================
# 6. EXECUTIONENGINE GATEWAY (LAYER 2) TESTS
# ============================================================================


def test_execution_engine_layer2_policy_gateway():
    """Verifies ExecutionEngine Layer 2 Policy Gateway."""
    p_engine = PolicyEngine()
    engine = ExecutionEngine(policy_engine=p_engine)

    # Create a plan containing a destructive command
    step = PlanStep(
        step_id=1, action=Action.RUN_COMMAND, parameters={"command": "format C:"}
    )
    plan = Plan(steps=[step])

    res = engine.execute(plan)
    assert res.status.value == "failed"
    assert res.step_results[0].success is False
    assert "Policy DENY" in res.step_results[0].message


# ============================================================================
# 7. BRAINCORE INTEGRATION & MONOTONIC COMPOSITION TESTS
# ============================================================================


def test_brain_core_policy_confirmation_waiting_for_user():
    """Verifies BrainCore waiting for user state on policy confirmation."""
    p_engine = PolicyEngine()

    # User policy mandating confirmation for input execution
    confirm_rule = PolicyRule(
        rule_id="CONFIRM_INPUT",
        scope=PolicyScope.USER_POLICY,
        target_capability="input",
        target_action="*",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
        explanation="Input requires confirmation.",
    )
    p_engine.register_user_rule(confirm_rule)

    cap_mgr = create_default_capability_manager(policy_engine=p_engine)
    brain = BrainCore(capability_manager=cap_mgr)

    # Initial processing should transition to WAITING_FOR_USER
    req = InputRequest(
        raw_text="open notepad", source="cli", timestamp=datetime.now(UTC)
    )
    res = brain.process(req)
    assert res.brain_status == BrainStatus.WAITING_FOR_USER

    # Resume with authorization granted
    auth = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at=datetime.now(UTC),
    )
    res_resumed = brain.process(
        InputRequest(
            raw_text="open notepad", source="cli", timestamp=datetime.now(UTC)
        ),
        authorization=auth,
    )
    assert res_resumed.brain_status == BrainStatus.COMPLETED


def test_brain_core_policy_deny_fails_goal():
    """Verifies BrainCore goal failure on Policy DENY."""
    p_engine = PolicyEngine()
    deny_planning = PolicyRule(
        rule_id="DENY_PLANNING",
        scope=PolicyScope.USER_POLICY,
        target_capability="planning",
        target_action="*",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.DENY,
        explanation="Planning capability blocked by policy.",
    )
    p_engine.register_user_rule(deny_planning)

    cap_mgr = create_default_capability_manager(policy_engine=p_engine)
    brain = BrainCore(capability_manager=cap_mgr)

    with pytest.raises(ProcessingError, match="failed with policy DENY"):
        brain.process(
            InputRequest(
                raw_text="Plan something", source="cli", timestamp=datetime.now(UTC)
            )
        )


def test_policy_capability_adapter_execution():
    """Verifies PolicyCapability adapter execution methods."""
    from argos.policy.exceptions import PolicyValidationError
    from argos.policy.policy_capability import PolicyCapability

    cap = PolicyCapability()
    assert cap.name == "policy"
    assert isinstance(cap.engine, PolicyEngine)

    # evaluate_capability
    dec = cap.execute(
        "evaluate_capability", capability_name="execution", action="open_app"
    )
    assert dec.outcome == PolicyOutcome.ALLOW

    # evaluate_capability via kwargs
    dec_kw = cap.execute(
        operation="evaluate_capability", capability_name="memory", action="get_exact"
    )
    assert dec_kw.outcome == PolicyOutcome.ALLOW

    # evaluate_action
    dec_act = cap.execute("evaluate_action", action="read_file", target="notes.txt")
    assert dec_act.outcome == PolicyOutcome.ALLOW

    # register_user_rule
    rule = PolicyRule(
        rule_id="RULE_TEST",
        scope=PolicyScope.USER_POLICY,
        target_capability="execution",
        target_action="*",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.ALLOW,
        explanation="Test rule",
    )
    cap.execute("register_user_rule", rule)

    with pytest.raises(PolicyValidationError, match="requires a PolicyRule"):
        cap.execute("register_user_rule")

    # reload_user_rules
    cap.execute("reload_user_rules")

    # unsupported operation
    with pytest.raises(PolicyValidationError, match="Unsupported policy action"):
        cap.execute("unsupported_op")


def test_policy_engine_edge_cases_and_parsing():
    """Verifies PolicyEngine parsing and edge cases."""

    # Mock MemoryEngine for reload_user_rules
    class MockRecord:
        def __init__(self, value):
            self.value = value

        def export_to_dict(self):
            return {"value": self.value}

    class MockMemoryEngine:
        def list_by_category(self, category):
            return [
                MockRecord({
                    "rule_id": "RELOADED_USER_RULE",
                    "scope": "user_policy",
                    "target_capability": "execution",
                    "target_action": "run_command",
                    "operator": "equals",
                    "expected_value": "*",
                    "outcome": "allow",
                    "explanation": "Reloaded user rule",
                }),
                MockRecord("invalid_non_dict_record"),
            ]

    pe = PolicyEngine(memory_engine=MockMemoryEngine())
    assert len(pe._user_rules) == 1
    assert pe._user_rules[0].rule_id == "RELOADED_USER_RULE"

    # Invalid rule registration
    with pytest.raises(PolicyValidationError, match="must specify valid rule_id"):
        pe.register_user_rule(
            PolicyRule(
                rule_id="",
                scope=PolicyScope.USER_POLICY,
                target_capability="execution",
                target_action="*",
                parameter_name=None,
                operator=RuleOperator.EQUALS,
                expected_value="*",
                outcome=PolicyOutcome.ALLOW,
                explanation="",
            )
        )

    with pytest.raises(PolicyValidationError, match="invalid code injection"):
        pe.register_user_rule(
            PolicyRule(
                rule_id="INJECTION_RULE",
                scope=PolicyScope.USER_POLICY,
                target_capability="execution",
                target_action="*",
                parameter_name=None,
                operator=RuleOperator.EQUALS,
                expected_value="__import__('os').system('dir')",
                outcome=PolicyOutcome.ALLOW,
                explanation="",
            )
        )

    # Payload code injection predicate evaluation
    dec_inj = pe.evaluate_action(action="run_command", target="__import__('os')")
    assert dec_inj.outcome == PolicyOutcome.DENY
    assert dec_inj.matched_rule_id == "PREDICATE_CODE_INJECTION_DENY"

    # Malformed rule evaluation handling
    class MalformedRule(PolicyRule):
        pass

    pe._user_rules.append(
        MalformedRule(
            rule_id="BROKEN",
            scope=PolicyScope.USER_POLICY,
            target_capability="custom",
            target_action="custom",
            parameter_name=None,
            operator=RuleOperator.EQUALS,
            expected_value=None,
            outcome=PolicyOutcome.ALLOW,
            explanation="Broken rule",
        )
    )
    # Evaluate capability with custom action that triggers rule check
    dec_mal = pe._evaluate("custom", "custom", {"val": 123})
    assert dec_mal.outcome in (PolicyOutcome.REQUIRE_CONFIRMATION, PolicyOutcome.ALLOW)

    # Storage unavailable fallback
    pe._storage_available = False
    dec_no_store = pe._evaluate("execution", "delete_file", {})
    assert dec_no_store.outcome == PolicyOutcome.DENY
    assert dec_no_store.matched_rule_id == "FAILSAFE_STORAGE_UNAVAILABLE_DENY"

    # Unrecognized action fallback
    pe._storage_available = True
    dec_unrec = pe._evaluate("unknown_cap", "unknown_action", {})
    assert dec_unrec.outcome == PolicyOutcome.ALLOW

    # Fallback for unrecognized run_command action
    dec_unrec_cmd = pe._evaluate("unknown_cap", "run_command", {})
    assert dec_unrec_cmd.outcome == PolicyOutcome.REQUIRE_CONFIRMATION

    # Test _parse_record_to_rule with invalid object and exception
    assert pe._parse_record_to_rule(object()) is None
    bad_rule_dict = {"rule_id": "INVALID_SCOPE", "scope": "nonexistent_scope"}
    assert pe._parse_record_to_rule(bad_rule_dict) is None


def test_predicates_and_evaluator_uncovered_branches():
    """Verifies predicates and evaluator uncovered branches."""
    from argos.policy.evaluator import (
        evaluate_rule_condition,
        normalize_capability_name,
        resolve_canonical_decision,
    )
    from argos.policy.predicates import (
        is_arbitrary_code_payload,
        is_system_directory_path,
    )

    assert is_system_directory_path(12345) is False
    assert is_arbitrary_code_payload(12345) is False
    assert normalize_capability_name(12345) == ""

    # Unknown operator handling in evaluate_rule_condition
    rule = PolicyRule(
        rule_id="UNKNOWN_OP_RULE",
        scope=PolicyScope.USER_POLICY,
        target_capability="execution",
        target_action="*",
        parameter_name="param",
        operator="nonexistent_op",
        expected_value="val",
        outcome=PolicyOutcome.ALLOW,
        explanation="",
    )
    res = evaluate_rule_condition(
        rule, "execution", "run_command", {"param": "val"}
    )
    assert res is False

    # resolve_canonical_decision with empty list
    assert resolve_canonical_decision([]) is None

    # is_destructive_system_command non-string input (L45)
    assert is_destructive_system_command(12345) is False
    assert is_destructive_system_command(None) is False

    # Invalid regex pattern handling in evaluate_rule_condition (L120-122)
    invalid_regex_rule = PolicyRule(
        rule_id="BAD_REGEX",
        scope=PolicyScope.USER_POLICY,
        target_capability="execution",
        target_action="*",
        parameter_name="target",
        operator=RuleOperator.REGEX_MATCH,
        expected_value="[invalid regex",
        outcome=PolicyOutcome.DENY,
        explanation="",
    )
    res_invalid_regex = evaluate_rule_condition(
        invalid_regex_rule, "execution", "run_command", {"target": "sample"}
    )
    assert res_invalid_regex is False

    # resolve_canonical_decision defensive return None for unrecognized scope (L171)
    unrec_scope_rule = PolicyRule(
        rule_id="UNREC_SCOPE",
        scope="nonexistent_scope",
        target_capability="execution",
        target_action="*",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value="*",
        outcome=PolicyOutcome.ALLOW,
        explanation="",
    )
    assert resolve_canonical_decision([unrec_scope_rule]) is None


def test_policy_engine_record_exception_and_malformed_rule_failsafe():
    """Verifies storage record exception handling and malformed rule fail-safe."""
    # 1. Record parsing exception in reload_user_rules (L63-64)
    class MockRecord:
        pass

    class MockEngineWithRecord:
        def list_by_category(self, category):
            return [MockRecord()]

    pe_corr = PolicyEngine(memory_engine=MockEngineWithRecord())
    # Mock _parse_record_to_rule to raise exception inside iteration loop
    pe_corr._parse_record_to_rule = Mock(side_effect=RuntimeError("Corrupted record"))
    pe_corr.reload_user_rules()
    assert len(pe_corr._user_rules) == 0

    # 2. Malformed rule exception handling in _evaluate (L200-201)
    class BrokenMatchingRule:
        rule_id = "BROKEN_PROPERTY_RULE"
        scope = PolicyScope.USER_POLICY
        outcome = PolicyOutcome.DENY
        explanation = "Broken rule"

        @property
        def target_capability(self):
            raise RuntimeError("Property access failure during matching")

    pe_broken = PolicyEngine()
    pe_broken._user_rules.append(BrokenMatchingRule())
    decision = pe_broken._evaluate("execution", "run_command", {"command": "test"})
    # Safety Invariant Check: Malformed user policy MUST NOT silently yield ALLOW
    assert decision.outcome == PolicyOutcome.REQUIRE_CONFIRMATION
    assert decision.outcome != PolicyOutcome.ALLOW
    assert "Malformed policy rule" in decision.explanation

