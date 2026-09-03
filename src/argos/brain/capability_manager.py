"""Capability management layer for the ARGOS Brain Core subsystem.

Registers and coordinates cognitive capabilities (Input, Intent, Planning,
Execution, Memory, Policy) and wraps subsystem exceptions at capability boundaries.
Integrates Layer 1 Policy Gateway (Capability Pre-Dispatch Enforcement).
"""

from abc import ABC, abstractmethod
from typing import Any

from argos.brain.constants import (
    CAPABILITY_EXECUTION,
    CAPABILITY_INPUT,
    CAPABILITY_INTENT,
    CAPABILITY_PLANNING,
)
from argos.brain.exceptions import (
    CapabilityNotFoundError,
    ProcessingError,
    ValidationError,
)
from argos.execution.exceptions import ExecutionError
from argos.execution.execution_result import ExecutionResult
from argos.input.exceptions import InputProcessingError
from argos.input.input_request import InputRequest
from argos.input.parsed_request import ParsedRequest
from argos.input.processor import InputProcessor
from argos.intent.analyzer import IntentAnalyzer
from argos.intent.exceptions import IntentAnalysisError
from argos.intent.intent_result import IntentResult
from argos.planning.exceptions import PlanningError
from argos.planning.plan import Plan
from argos.planning.planner import Planner
from argos.policy.constants import CAPABILITY_POLICY
from argos.policy.exceptions import PolicyEngineError, PolicyEvaluationError
from argos.policy.models import PolicyOutcome
from argos.policy.policy_engine import PolicyEngine


class CognitiveCapability(ABC):
    """Abstract interface defining a cognitive capability usable by the Brain."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the unique identifier for this capability."""
        ...

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Executes the capability with the provided parameters.

        Raises:
            Exception: Subsystem-specific exceptions on failure.
        """
        ...


from argos.memory.exceptions import MemoryError  # noqa: E402


class InputCapability(CognitiveCapability):
    """Adapter wrapping the ADS-001 InputProcessor subsystem."""

    def __init__(self, processor: InputProcessor | None = None) -> None:
        """Initializes with an optional injected InputProcessor."""
        self._processor = processor or InputProcessor()

    @property
    def name(self) -> str:
        """Unique identifier of the input capability."""
        return CAPABILITY_INPUT

    def execute(self, request: InputRequest) -> ParsedRequest:
        """Executes input parsing on an InputRequest."""
        return self._processor.process(request)


class IntentCapability(CognitiveCapability):
    """Adapter wrapping the ADS-002 IntentAnalyzer subsystem."""

    def __init__(self, analyzer: IntentAnalyzer | None = None) -> None:
        """Initializes with an optional injected IntentAnalyzer."""
        self._analyzer = analyzer or IntentAnalyzer()

    @property
    def name(self) -> str:
        """Unique identifier of the intent capability."""
        return CAPABILITY_INTENT

    def execute(self, request: ParsedRequest) -> IntentResult:
        """Executes semantic intent classification on a ParsedRequest."""
        return self._analyzer.analyze(request)


class PlanningCapability(CognitiveCapability):
    """Adapter wrapping the ADS-003 Planner subsystem."""

    def __init__(self, planner: Planner | None = None) -> None:
        """Initializes with an optional injected Planner."""
        self._planner = planner or Planner()

    @property
    def name(self) -> str:
        """Unique identifier of the planning capability."""
        return CAPABILITY_PLANNING

    def execute(self, intent_result: IntentResult) -> Plan:
        """Generates an action recipe Plan from an IntentResult."""
        return self._planner.plan(intent_result)


class ExecutionCapability(CognitiveCapability):
    """Adapter wrapping the ADS-004 ExecutionEngine subsystem."""

    def __init__(self, engine: Any | None = None) -> None:
        """Initializes with an optional injected ExecutionEngine."""
        if engine is None:
            from argos.execution.execution_engine import ExecutionEngine
            self._engine = ExecutionEngine()
        else:
            self._engine = engine

    @property
    def name(self) -> str:
        """Unique identifier of the execution capability."""
        return CAPABILITY_EXECUTION

    def execute(self, plan: Plan, authorization: Any | None = None) -> ExecutionResult:
        """Executes the action steps defined in a Plan."""
        return self._engine.execute(plan, authorization=authorization)


class CapabilityManager:
    """Registry managing available cognitive capabilities.

    Handles capability discovery, invocation, Layer 1 policy evaluation,
    and boundary exception translation.
    """

    def __init__(
        self,
        capabilities: list[CognitiveCapability] | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        """Initializes CapabilityManager with capabilities and optional policy engine.

        Args:
            capabilities: Optional list of CognitiveCapability instances to register.
            policy_engine: Optional injected PolicyEngine instance.
        """
        self._capabilities: dict[str, CognitiveCapability] = {}
        self._policy_engine = policy_engine or PolicyEngine()
        if capabilities:
            for cap in capabilities:
                self.register(cap)

    @property
    def policy_engine(self) -> PolicyEngine:
        """Public access to underlying PolicyEngine instance."""
        return self._policy_engine

    def register(self, capability: CognitiveCapability) -> None:
        """Registers a new cognitive capability.

        Args:
            capability: A CognitiveCapability instance.

        Raises:
            ValidationError: If capability is invalid or already registered.
        """
        if not isinstance(capability, CognitiveCapability):
            raise ValidationError(
                "Registered capability must implement CognitiveCapability."
            )
        name = capability.name
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Capability name must be a non-empty string.")
        if name in self._capabilities:
            raise ValidationError(f"Capability '{name}' is already registered.")

        self._capabilities[name] = capability

    def _normalize_name(self, name: str) -> str:
        if name in self._capabilities:
            return name
        low = name.lower().strip()
        if (
            low in ("input", "input_processing")
            and CAPABILITY_INPUT in self._capabilities
        ):
            return CAPABILITY_INPUT
        if (
            low in ("intent", "intent_analysis")
            and CAPABILITY_INTENT in self._capabilities
        ):
            return CAPABILITY_INTENT
        return name

    def get(self, name: str) -> CognitiveCapability:
        """Retrieves a registered capability by name.

        Args:
            name: Identifier of the capability.

        Returns:
            The registered CognitiveCapability instance.

        Raises:
            CapabilityNotFoundError: If the capability is not registered.
        """
        norm_name = self._normalize_name(name)
        if norm_name not in self._capabilities:
            raise CapabilityNotFoundError(f"Capability '{name}' is not registered.")
        return self._capabilities[norm_name]

    def has(self, name: str) -> bool:
        """Checks if a capability is registered.

        Args:
            name: Capability identifier.

        Returns:
            True if capability exists, False otherwise.
        """
        norm_name = self._normalize_name(name)
        return norm_name in self._capabilities

    def list_capabilities(self) -> list[str]:
        """Returns names of all currently registered capabilities.

        Returns:
            List of registered capability names.
        """
        return list(self._capabilities.keys())

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Executes capability through Layer 1 Policy Gateway.

        Args:
            name: Capability identifier.
            *args: Positional arguments to pass to capability.
            **kwargs: Keyword arguments to pass to capability.

        Returns:
            Result returned by the capability.

        Raises:
            CapabilityNotFoundError: If capability is not found.
            ValidationError: If input validation fails.
            PolicyEvaluationError: If policy authorization is unfulfilled.
            ProcessingError: If subsystem execution or policy DENY occurs.
        """
        capability = self.get(name)

        # Infer action identifier
        action = "execute"
        if kwargs.get("action"):
            action = str(kwargs["action"])
        elif args and isinstance(args[0], str):
            action = args[0]

        auth = kwargs.get("authorization")

        # 1. Layer 1 Policy Gateway Pre-Dispatch Enforcement (except for policy)
        if name != CAPABILITY_POLICY:
            decision = self._policy_engine.evaluate_capability(
                name, action, kwargs
            )
            if decision.outcome == PolicyOutcome.DENY:
                raise ProcessingError(
                    f"Capability '{name}' failed with policy DENY: "
                    f"{decision.explanation}"
                )
            elif decision.outcome in (
                PolicyOutcome.REQUIRE_CONFIRMATION,
                PolicyOutcome.REQUIRE_AUTHORIZATION,
            ):
                if not auth or getattr(auth, "granted", False) is not True:
                    raise PolicyEvaluationError(
                        f"Capability '{name}' requires user authorization: "
                        f"{decision.explanation}"
                    )

        # 2. Dispatch Capability Execution
        call_kwargs = dict(kwargs)
        non_auth_caps = (
            CAPABILITY_INPUT,
            CAPABILITY_INTENT,
            CAPABILITY_PLANNING,
            CAPABILITY_POLICY,
        )
        if name in non_auth_caps:
            call_kwargs.pop("authorization", None)

        try:
            return capability.execute(*args, **call_kwargs)
        except (
            InputProcessingError,
            IntentAnalysisError,
            PlanningError,
            ExecutionError,
            MemoryError,
            PolicyEngineError,
        ) as err:
            raise ProcessingError(
                f"Capability '{name}' failed with subsystem error: {err}"
            ) from err
        except Exception as err:
            raise ProcessingError(
                f"Capability '{name}' encountered an unexpected error: {err}"
            ) from err


def create_default_capability_manager(
    input_processor: InputProcessor | None = None,
    intent_analyzer: IntentAnalyzer | None = None,
    planner: Planner | None = None,
    execution_engine: Any | None = None,
    memory_engine: Any = None,
    policy_engine: PolicyEngine | None = None,
) -> CapabilityManager:
    """Factory creating a CapabilityManager populated with standard subsystem adapters.

    Args:
        input_processor: Optional custom InputProcessor.
        intent_analyzer: Optional custom IntentAnalyzer.
        planner: Optional custom Planner.
        execution_engine: Optional custom ExecutionEngine.
        memory_engine: Optional custom MemoryEngine for MemoryCapability.
        policy_engine: Optional custom PolicyEngine.

    Returns:
        A fully configured CapabilityManager with standard capabilities.
    """
    from argos.execution.execution_engine import ExecutionEngine
    from argos.memory.memory_capability import MemoryCapability
    from argos.policy.policy_capability import PolicyCapability

    p_engine = policy_engine or PolicyEngine(memory_engine=memory_engine)
    e_engine = execution_engine or ExecutionEngine(policy_engine=p_engine)

    return CapabilityManager(
        capabilities=[
            InputCapability(input_processor),
            IntentCapability(intent_analyzer),
            PlanningCapability(planner),
            ExecutionCapability(e_engine),
            MemoryCapability(memory_engine),
            PolicyCapability(p_engine),
        ],
        policy_engine=p_engine,
    )
