"""Domain models and enumerations for the ARGOS Policy Engine Subsystem."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PolicyOutcome(StrEnum):
    """Public evaluation outcomes produced by PolicyEngine."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REQUIRE_AUTHORIZATION = "require_authorization"


class PolicyScope(StrEnum):
    """Hierarchy and precedence scopes for policy rules."""

    CONSTITUTION = "constitution"
    SYSTEM_IMMUTABLE = "system_immutable"
    SYSTEM_SECURITY = "system_security"
    USER_POLICY = "user_policy"
    CONTEXTUAL = "contextual"
    DEFAULT_FALLBACK = "default_fallback"


class RuleOperator(StrEnum):
    """Supported rule evaluation operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    PREFIX_MATCH = "prefix_match"
    SUFFIX_MATCH = "suffix_match"
    REGEX_MATCH = "regex_match"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"


@dataclass(slots=True)
class PolicyRule:
    """Represents a declarative policy rule definition."""

    rule_id: str
    scope: PolicyScope
    target_capability: str
    target_action: str
    parameter_name: str | None
    operator: RuleOperator
    expected_value: str
    outcome: PolicyOutcome
    explanation: str


@dataclass(slots=True)
class PolicyDecision:
    """Represents the immutable result of a policy evaluation."""

    outcome: PolicyOutcome
    matched_rule_id: str | None
    scope: PolicyScope
    explanation: str
    timestamp: datetime
