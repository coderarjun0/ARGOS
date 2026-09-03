"""Deterministic Policy Evaluator for the ARGOS Policy Engine Subsystem."""

import re
from typing import Any

from argos.policy.constants import WILDCARD_SYMBOL
from argos.policy.models import PolicyOutcome, PolicyRule, PolicyScope

# Scope Hierarchy Order (Highest to Lowest)
SCOPE_HIERARCHY: list[PolicyScope] = [
    PolicyScope.CONSTITUTION,
    PolicyScope.SYSTEM_IMMUTABLE,
    PolicyScope.USER_POLICY,
    PolicyScope.SYSTEM_SECURITY,
    PolicyScope.CONTEXTUAL,
    PolicyScope.DEFAULT_FALLBACK,
]

# Severity Outcome Ranks (Highest to Lowest)
SEVERITY_RANKS: dict[PolicyOutcome, int] = {
    PolicyOutcome.DENY: 4,
    PolicyOutcome.REQUIRE_AUTHORIZATION: 3,
    PolicyOutcome.REQUIRE_CONFIRMATION: 2,
    PolicyOutcome.ALLOW: 1,
}


def normalize_capability_name(cap: str) -> str:
    """Normalizes capability names and aliases."""
    if not cap or not isinstance(cap, str):
        return ""
    low = cap.lower().strip()
    if low in ("input", "input_processing"):
        return "input_processing"
    if low in ("intent", "intent_analysis"):
        return "intent_analysis"
    if low in ("execution", "tool_execution"):
        return "execution"
    return low


def evaluate_rule_condition(
    rule: PolicyRule,
    capability_name: str,
    action: str,
    parameters: dict[str, Any],
) -> bool:
    """Evaluates whether a single PolicyRule matches context.

    Args:
        rule: PolicyRule to evaluate.
        capability_name: Target capability name string.
        action: Target action string.
        parameters: Dictionary of evaluation parameters.

    Returns:
        True if rule matches context, False otherwise.
    """
    # 1. Target Capability Matching (with alias normalization)
    rule_cap = normalize_capability_name(rule.target_capability)
    ctx_cap = normalize_capability_name(capability_name)
    if rule.target_capability != WILDCARD_SYMBOL and rule_cap != ctx_cap:
        return False

    # 2. Target Action Matching
    if (
        rule.target_action != WILDCARD_SYMBOL
        and rule.target_action.lower() != action.lower()
    ):
        return False

    # 3. Parameter Condition Matching
    if rule.parameter_name is None:
        return True

    val = parameters.get(rule.parameter_name)
    if val is None:
        val = (
            parameters.get("target")
            or parameters.get("file_path")
            or parameters.get("command")
            or parameters.get("path")
        )

    if val is None:
        return False

    str_val = str(val)
    expected = rule.expected_value
    op_str = (
        rule.operator.value
        if hasattr(rule.operator, "value")
        else str(rule.operator)
    )

    try:
        match op_str:
            case "equals":
                return str_val.lower() == expected.lower()
            case "not_equals":
                return str_val.lower() != expected.lower()
            case "contains":
                return expected.lower() in str_val.lower()
            case "not_contains":
                return expected.lower() not in str_val.lower()
            case "prefix_match":
                return str_val.lower().startswith(expected.lower())
            case "suffix_match":
                return str_val.lower().endswith(expected.lower())
            case "regex_match":
                return re.search(expected, str_val, re.IGNORECASE) is not None
            case "in_list":
                items = [x.strip().lower() for x in expected.split(",") if x.strip()]
                return str_val.lower() in items
            case "not_in_list":
                items = [x.strip().lower() for x in expected.split(",") if x.strip()]
                return str_val.lower() not in items
            case _:
                return False
    except Exception:
        # Regex or string evaluation error -> fail match safely
        return False


def get_rule_specificity(rule: PolicyRule) -> int:
    """Calculates the specificity rank integer for a PolicyRule."""
    has_specific_cap = rule.target_capability != WILDCARD_SYMBOL
    has_specific_act = rule.target_action != WILDCARD_SYMBOL
    has_param = rule.parameter_name is not None

    if has_specific_cap and has_specific_act and has_param:
        return 3
    if has_specific_cap and has_specific_act:
        return 2
    if has_specific_cap:
        return 1
    return 0


def resolve_canonical_decision(
    matching_rules: list[PolicyRule],
) -> PolicyRule | None:
    """Applies the canonical 4-step conflict resolution algorithm.

    Algorithm:
    1. Scope Precedence: Keep only rules matching the highest active PolicyScope.
    2. Deny-Override: If any rule at highest scope is DENY, select DENY.
    3. Specificity Ranking: Keep rules tied at highest Specificity Rank (0..3).
    4. Severity Rank Selection & Tie-Break: Select rule with highest severity rank.
       Tie-break lexicographically by rule_id.

    Args:
        matching_rules: List of PolicyRules that matched context.

    Returns:
        The winning PolicyRule or None if matching_rules is empty.
    """
    if not matching_rules:
        return None

    # Step 1: Highest Scope Layer Selection
    highest_scope: PolicyScope | None = None
    for scope in SCOPE_HIERARCHY:
        scope_matches = [r for r in matching_rules if r.scope == scope]
        if scope_matches:
            highest_scope = scope
            matching_rules = scope_matches
            break

    if not matching_rules or highest_scope is None:
        return None

    # Step 2: Deny-Override Inspection
    deny_matches = [r for r in matching_rules if r.outcome == PolicyOutcome.DENY]
    if deny_matches:
        # Sort deny matches lexicographically by rule_id for determinism
        deny_matches.sort(key=lambda r: r.rule_id)
        return deny_matches[0]

    # Step 3: Specificity Ranking
    max_specificity = max(get_rule_specificity(r) for r in matching_rules)
    matching_rules = [
        r for r in matching_rules if get_rule_specificity(r) == max_specificity
    ]

    # Step 4: Severity Rank Selection & Lexicographical Tie-Break
    # Sort key: (-severity_rank, rule_id)
    matching_rules.sort(key=lambda r: (-SEVERITY_RANKS.get(r.outcome, 0), r.rule_id))
    return matching_rules[0]
