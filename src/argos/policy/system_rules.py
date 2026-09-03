"""Built-in immutable system prohibitions, security rules, and baseline fallbacks."""

from argos.policy.constants import WILDCARD_SYMBOL
from argos.policy.models import PolicyOutcome, PolicyRule, PolicyScope, RuleOperator

BUILTIN_SYSTEM_RULES: list[PolicyRule] = [
    # CONSTITUTION / SYSTEM_IMMUTABLE Rules
    PolicyRule(
        rule_id="SYS_IMMUTABLE_001_SYSTEM_DIR_PROTECTION",
        scope=PolicyScope.SYSTEM_IMMUTABLE,
        target_capability=WILDCARD_SYMBOL,
        target_action="delete_file",
        parameter_name="target",
        operator=RuleOperator.REGEX_MATCH,
        expected_value=(
            r"^[a-zA-Z]:\\(Windows|Program Files|Program Files \(x86\))"
            r"|^\/(etc|usr|var|bin|sbin|boot|sys)"
        ),
        outcome=PolicyOutcome.DENY,
        explanation=(
            "Immutable system prohibition: Modification or deletion of system "
            "operating directory is strictly forbidden."
        ),
    ),
    PolicyRule(
        rule_id="SYS_IMMUTABLE_002_DESTRUCTIVE_COMMAND",
        scope=PolicyScope.SYSTEM_IMMUTABLE,
        target_capability=WILDCARD_SYMBOL,
        target_action="run_command",
        parameter_name="command",
        operator=RuleOperator.REGEX_MATCH,
        expected_value=r"\b(rm\s+-rf\s+/|format\s+[a-zA-Z]:|mkfs|dd\s+if=)",
        outcome=PolicyOutcome.DENY,
        explanation=(
            "Immutable system prohibition: Execution of destructive drive format "
            "or disk wipe commands is strictly forbidden."
        ),
    ),
    PolicyRule(
        rule_id="SYS_IMMUTABLE_003_NO_EVAL_CODE",
        scope=PolicyScope.SYSTEM_IMMUTABLE,
        target_capability=WILDCARD_SYMBOL,
        target_action=WILDCARD_SYMBOL,
        parameter_name="code",
        operator=RuleOperator.REGEX_MATCH,
        expected_value=r"eval\(|exec\(|__import__",
        outcome=PolicyOutcome.DENY,
        explanation=(
            "Immutable system prohibition: Dynamic code evaluation (eval/exec) "
            "from unauthenticated inputs is strictly prohibited."
        ),
    ),
    # SYSTEM_SECURITY Rules
    PolicyRule(
        rule_id="SYS_SEC_001_SENSITIVE_FILE_WRITE",
        scope=PolicyScope.SYSTEM_SECURITY,
        target_capability="execution",
        target_action="write_file",
        parameter_name="target",
        operator=RuleOperator.REGEX_MATCH,
        expected_value=r"\.(exe|dll|bat|cmd|sh|ps1)$",
        outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
        explanation=(
            "System security rule: Creation or modification of executable files "
            "requires explicit human confirmation."
        ),
    ),
    PolicyRule(
        rule_id="SYS_SEC_002_SYSTEM_COMMAND_EXECUTION",
        scope=PolicyScope.SYSTEM_SECURITY,
        target_capability="execution",
        target_action="run_command",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value=WILDCARD_SYMBOL,
        outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
        explanation=(
            "System security rule: Execution of terminal commands requires "
            "human confirmation."
        ),
    ),
    # DEFAULT_FALLBACK Baseline Rules
    PolicyRule(
        rule_id="FALLBACK_001_SAFE_INPUT_PERCEPTION",
        scope=PolicyScope.DEFAULT_FALLBACK,
        target_capability="input",
        target_action=WILDCARD_SYMBOL,
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value=WILDCARD_SYMBOL,
        outcome=PolicyOutcome.ALLOW,
        explanation=(
            "Default safe baseline: Perception and input normalization are permitted."
        ),
    ),
    PolicyRule(
        rule_id="FALLBACK_002_SAFE_INTENT_ANALYSIS",
        scope=PolicyScope.DEFAULT_FALLBACK,
        target_capability="intent",
        target_action=WILDCARD_SYMBOL,
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value=WILDCARD_SYMBOL,
        outcome=PolicyOutcome.ALLOW,
        explanation="Default safe baseline: Semantic intent analysis is permitted.",
    ),
    PolicyRule(
        rule_id="FALLBACK_003_SAFE_PLANNING",
        scope=PolicyScope.DEFAULT_FALLBACK,
        target_capability="planning",
        target_action=WILDCARD_SYMBOL,
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value=WILDCARD_SYMBOL,
        outcome=PolicyOutcome.ALLOW,
        explanation=(
            "Default safe baseline: Cognitive plan recipe generation is permitted."
        ),
    ),
    PolicyRule(
        rule_id="FALLBACK_004_SAFE_MEMORY_READ",
        scope=PolicyScope.DEFAULT_FALLBACK,
        target_capability="memory",
        target_action="get_session_turns",
        parameter_name=None,
        operator=RuleOperator.EQUALS,
        expected_value=WILDCARD_SYMBOL,
        outcome=PolicyOutcome.ALLOW,
        explanation=(
            "Default safe baseline: Reading transient session memory turns "
            "is permitted."
        ),
    ),
]
