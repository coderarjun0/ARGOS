"""Public facade and orchestrator for the ARGOS Policy Engine Subsystem."""

from datetime import UTC, datetime
from typing import Any

from argos.policy.constants import DEFAULT_POLICY_CATEGORY, WILDCARD_SYMBOL
from argos.policy.evaluator import (
    evaluate_rule_condition,
    normalize_capability_name,
    resolve_canonical_decision,
)
from argos.policy.exceptions import PolicyValidationError
from argos.policy.models import (
    PolicyDecision,
    PolicyOutcome,
    PolicyRule,
    PolicyScope,
    RuleOperator,
)
from argos.policy.predicates import (
    is_arbitrary_code_payload,
    is_destructive_system_command,
    is_system_directory_path,
)
from argos.policy.system_rules import BUILTIN_SYSTEM_RULES


class PolicyEngine:
    """Public facade for the ARGOS Policy Engine Subsystem.

    Evaluates cognitive capabilities and low-level execution actions against
    deterministic rules. Evaluation is side-effect-free and stateless.
    Maintains an in-memory rule snapshot cache loaded from built-ins and MemoryEngine.
    """

    def __init__(self, memory_engine: Any | None = None) -> None:
        """Initializes PolicyEngine, loading system rules and optional user policies.

        Args:
            memory_engine: Optional MemoryEngine instance for loading user policy rules.
        """
        self._memory_engine = memory_engine
        self._system_rules: list[PolicyRule] = list(BUILTIN_SYSTEM_RULES)
        self._user_rules: list[PolicyRule] = []
        self._storage_available: bool = True

        if self._memory_engine is not None:
            self.reload_user_rules()

    def reload_user_rules(self) -> None:
        """Reloads user policy rules from PersistentStore via MemoryEngine."""
        if self._memory_engine is None:
            return

        self._user_rules.clear()
        try:
            records = self._memory_engine.list_by_category(DEFAULT_POLICY_CATEGORY)
            for record in records:
                try:
                    rule = self._parse_record_to_rule(record)
                    if rule is not None:
                        self._user_rules.append(rule)
                except Exception:
                    continue
            self._storage_available = True
        except Exception:
            self._storage_available = False

    def register_user_rule(self, rule: PolicyRule) -> None:
        """Registers a user-defined policy rule in the memory cache.

        Args:
            rule: PolicyRule instance to register.

        Raises:
            PolicyValidationError: If rule scope attempts to override system rules.
        """
        if rule.scope in (PolicyScope.CONSTITUTION, PolicyScope.SYSTEM_IMMUTABLE):
            raise PolicyValidationError(
                f"Cannot register user rule '{rule.rule_id}' with system scope "
                f"'{rule.scope.value}'."
            )
        if not rule.rule_id or not rule.target_capability or not rule.target_action:
            raise PolicyValidationError(
                "PolicyRule must specify valid rule_id, target_capability, "
                "and target_action."
            )

        if is_arbitrary_code_payload(rule.expected_value):
            raise PolicyValidationError(
                "PolicyRule expected_value contains invalid code injection keywords."
            )

        self._user_rules = [r for r in self._user_rules if r.rule_id != rule.rule_id]
        self._user_rules.append(rule)

    def evaluate_capability(
        self, capability_name: str, action: str, kwargs: dict[str, Any] | None = None
    ) -> PolicyDecision:
        """Evaluates whether a capability invocation is permitted by policy (Layer 1).

        Args:
            capability_name: Target capability name (e.g. 'memory', 'execution').
            action: Capability action identifier.
            kwargs: Keyword arguments passed to capability.

        Returns:
            PolicyDecision container with evaluation outcome.
        """
        params = dict(kwargs) if kwargs else {}
        return self._evaluate(
            capability_name=capability_name, action=action, parameters=params
        )

    def evaluate_action(
        self,
        action: str,
        target: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Evaluates whether a low-level action step is permitted by policy (Layer 2).

        Args:
            action: Execution action string (e.g. 'run_command', 'delete_file').
            target: Resource target string (e.g. file path, URL, application name).
            parameters: Action parameters dictionary.

        Returns:
            PolicyDecision container with evaluation outcome.
        """
        params = dict(parameters) if parameters else {}
        if target is not None:
            params["target"] = target
        return self._evaluate(
            capability_name="tool_execution", action=action, parameters=params
        )

    def _evaluate(
        self, capability_name: str, action: str, parameters: dict[str, Any]
    ) -> PolicyDecision:
        """Internal deterministic evaluation kernel."""
        now = datetime.now(UTC)

        # 1. Hardcoded Direct Predicate Safety Checks (CONSTITUTION Scope)
        target_val = (
            parameters.get("target")
            or parameters.get("path")
            or parameters.get("file_path")
        )
        if (
            target_val
            and is_system_directory_path(str(target_val))
            and action in ("delete_file", "write_file")
        ):
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                matched_rule_id="PREDICATE_SYSTEM_PATH_DENY",
                scope=PolicyScope.CONSTITUTION,
                explanation=(
                    "Immutable safety predicate: Modification of protected operating "
                    "system path is strictly forbidden."
                ),
                timestamp=now,
            )

        cmd_val = parameters.get("command") or parameters.get("cmd")
        if cmd_val and is_destructive_system_command(str(cmd_val)):
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                matched_rule_id="PREDICATE_DESTRUCTIVE_CMD_DENY",
                scope=PolicyScope.CONSTITUTION,
                explanation=(
                    "Immutable safety predicate: Execution of destructive disk format "
                    "command is strictly forbidden."
                ),
                timestamp=now,
            )

        for val in parameters.values():
            if is_arbitrary_code_payload(val):
                return PolicyDecision(
                    outcome=PolicyOutcome.DENY,
                    matched_rule_id="PREDICATE_CODE_INJECTION_DENY",
                    scope=PolicyScope.CONSTITUTION,
                    explanation=(
                        "Immutable safety predicate: Unsafe dynamic code "
                        "injection keyword detected in payload."
                    ),
                    timestamp=now,
                )

        # 2. Gather All Matching Rules from System & User Rule Snapshots
        all_rules = self._system_rules + self._user_rules
        matched_rules: list[PolicyRule] = []

        for rule in all_rules:
            try:
                if evaluate_rule_condition(rule, capability_name, action, parameters):
                    matched_rules.append(rule)
            except Exception:
                return PolicyDecision(
                    outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
                    matched_rule_id=rule.rule_id,
                    scope=rule.scope,
                    explanation=(
                        f"Malformed policy rule encountered for '{action}'. "
                        "Human confirmation required."
                    ),
                    timestamp=now,
                )

        # 3. Apply Canonical 4-Step Resolution Algorithm
        winning_rule = resolve_canonical_decision(matched_rules)

        if winning_rule is not None:
            return PolicyDecision(
                outcome=winning_rule.outcome,
                matched_rule_id=winning_rule.rule_id,
                scope=winning_rule.scope,
                explanation=winning_rule.explanation,
                timestamp=now,
            )

        # 4. Fallback Handling if No Specific Rule Matched
        if not self._storage_available and action in (
            "delete_file",
            "write_file",
            "run_command",
            "store_persistent",
        ):
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                matched_rule_id="FAILSAFE_STORAGE_UNAVAILABLE_DENY",
                scope=PolicyScope.DEFAULT_FALLBACK,
                explanation=(
                    "Policy storage unavailable: High-risk system modification "
                    "failed closed."
                ),
                timestamp=now,
            )

        norm_cap = normalize_capability_name(capability_name)
        safe_caps = (
            "input_processing",
            "intent_analysis",
            "planning",
            "execution",
            "memory",
            "tool_execution",
        )
        safe_actions = (
            "process",
            "analyze",
            "plan",
            "execute",
            "get_session_turns",
            "get_exact",
            "open_app",
            "close_app",
            "create_file",
            "write_file",
            "read_file",
            "delete_file",
            "search_web",
            "ask_clarification",
        )
        if norm_cap in safe_caps or action in safe_actions:
            return PolicyDecision(
                outcome=PolicyOutcome.ALLOW,
                matched_rule_id="FALLBACK_SAFE_DEFAULT_ALLOW",
                scope=PolicyScope.DEFAULT_FALLBACK,
                explanation=(
                    f"Default safe policy applied for capability '{capability_name}' "
                    f"and action '{action}'."
                ),
                timestamp=now,
            )

        if action in ("delete_file", "run_command"):
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_CONFIRMATION,
                matched_rule_id="FALLBACK_UNRECOGNIZED_ACTION_CONFIRM",
                scope=PolicyScope.DEFAULT_FALLBACK,
                explanation=(
                    f"Unrecognized action '{action}' requires explicit human "
                    "confirmation."
                ),
                timestamp=now,
            )

        return PolicyDecision(
            outcome=PolicyOutcome.ALLOW,
            matched_rule_id="FALLBACK_SAFE_DEFAULT_ALLOW",
            scope=PolicyScope.DEFAULT_FALLBACK,
            explanation=(
                f"Default safe policy applied for capability '{capability_name}' "
                f"and action '{action}'."
            ),
            timestamp=now,
        )

    def _parse_record_to_rule(self, record: Any) -> PolicyRule | None:
        """Parses a MemoryRecord or dictionary into a PolicyRule object."""
        try:
            val = getattr(record, "value", record)
            if isinstance(val, dict):
                data = val
            elif hasattr(record, "export_to_dict"):
                data = record.export_to_dict().get("value", {})
            else:
                return None

            return PolicyRule(
                rule_id=data["rule_id"],
                scope=PolicyScope(data.get("scope", "user_policy")),
                target_capability=data.get("target_capability", WILDCARD_SYMBOL),
                target_action=data.get("target_action", WILDCARD_SYMBOL),
                parameter_name=data.get("parameter_name"),
                operator=RuleOperator(data.get("operator", "equals")),
                expected_value=data.get("expected_value", ""),
                outcome=PolicyOutcome(data.get("outcome", "allow")),
                explanation=data.get("explanation", "User policy rule"),
            )
        except Exception:
            return None
