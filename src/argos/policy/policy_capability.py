"""Capability adapter for the ARGOS Policy Engine Subsystem."""

from typing import Any

from argos.brain.capability_manager import CognitiveCapability
from argos.policy.constants import CAPABILITY_POLICY
from argos.policy.exceptions import PolicyValidationError
from argos.policy.policy_engine import PolicyEngine


class PolicyCapability(CognitiveCapability):
    """Adapter wrapping the ADS-007 PolicyEngine subsystem as a CognitiveCapability."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        """Initializes with an optional injected PolicyEngine."""
        self._engine = policy_engine or PolicyEngine()

    @property
    def name(self) -> str:
        """Unique identifier of the policy capability."""
        return CAPABILITY_POLICY

    @property
    def engine(self) -> PolicyEngine:
        """Public access to underlying PolicyEngine instance."""
        return self._engine

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Executes a policy governance operation.

        Args:
            *args: Positional arguments (op, etc.).
            **kwargs: Keyword arguments.

        Returns:
            Result returned by PolicyEngine.
        """
        if not args:
            op = kwargs.pop("operation", "evaluate_capability")
        else:
            op = args[0]
            args = args[1:]

        match op:
            case "evaluate_capability":
                cap_name = kwargs.get("capability_name") or (
                    args[0] if args else "unknown"
                )
                cap_action = kwargs.get("action") or (
                    args[1] if len(args) > 1 else "unknown"
                )
                cap_kwargs = kwargs.get("kwargs") or {}
                return self._engine.evaluate_capability(
                    cap_name, cap_action, cap_kwargs
                )
            case "evaluate_action":
                act_name = kwargs.get("action") or (
                    args[0] if args else "unknown"
                )
                act_target = kwargs.get("target") or (
                    args[1] if len(args) > 1 else None
                )
                act_params = kwargs.get("parameters") or {}
                return self._engine.evaluate_action(
                    act_name, act_target, act_params
                )
            case "register_user_rule":
                rule = kwargs.get("rule") or (args[0] if args else None)
                if rule is None:
                    raise PolicyValidationError(
                        "register_user_rule requires a PolicyRule parameter."
                    )
                return self._engine.register_user_rule(rule)
            case "reload_user_rules":
                return self._engine.reload_user_rules()
            case _:
                raise PolicyValidationError(f"Unsupported policy action '{op}'.")
