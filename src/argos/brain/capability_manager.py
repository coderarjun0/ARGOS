"""Capability management layer for the ARGOS Brain Core subsystem.

Registers and coordinates cognitive capabilities (Input, Intent, Planning,
Execution, Memory) and wraps subsystem exceptions at capability boundaries.
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
from argos.execution.execution_engine import ExecutionEngine
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

    def __init__(self, engine: ExecutionEngine | None = None) -> None:
        """Initializes with an optional injected ExecutionEngine."""
        self._engine = engine or ExecutionEngine()

    @property
    def name(self) -> str:
        """Unique identifier of the execution capability."""
        return CAPABILITY_EXECUTION

    def execute(self, plan: Plan) -> ExecutionResult:
        """Executes the action steps defined in a Plan."""
        return self._engine.execute(plan)


class CapabilityManager:
    """Registry managing available cognitive capabilities.

    Handles capability discovery, invocation, and boundary exception translation.
    """

    def __init__(
        self,
        capabilities: list[CognitiveCapability] | None = None,
    ) -> None:
        """Initializes the CapabilityManager with optional capabilities.

        Args:
            capabilities: Optional list of CognitiveCapability instances to register.
        """
        self._capabilities: dict[str, CognitiveCapability] = {}
        if capabilities:
            for cap in capabilities:
                self.register(cap)

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

    def get(self, name: str) -> CognitiveCapability:
        """Retrieves a registered capability by name.

        Args:
            name: Identifier of the capability.

        Returns:
            The registered CognitiveCapability instance.

        Raises:
            CapabilityNotFoundError: If the capability is not registered.
        """
        if name not in self._capabilities:
            raise CapabilityNotFoundError(f"Capability '{name}' is not registered.")
        return self._capabilities[name]

    def has(self, name: str) -> bool:
        """Checks if a capability is registered.

        Args:
            name: Capability identifier.

        Returns:
            True if registered, otherwise False.
        """
        return name in self._capabilities

    def list_capabilities(self) -> list[str]:
        """Returns names of all currently registered capabilities.

        Returns:
            List of registered capability names.
        """
        return list(self._capabilities.keys())

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Executes a capability, wrapping subsystem errors in ProcessingError.

        Args:
            name: Capability identifier.
            *args: Positional arguments to pass to capability.
            **kwargs: Keyword arguments to pass to capability.

        Returns:
            Result returned by the capability.

        Raises:
            CapabilityNotFoundError: If capability is not found.
            ValidationError: If input validation fails.
            ProcessingError: If subsystem execution fails.
        """
        capability = self.get(name)
        try:
            return capability.execute(*args, **kwargs)
        except (
            InputProcessingError,
            IntentAnalysisError,
            PlanningError,
            ExecutionError,
            MemoryError,
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
    execution_engine: ExecutionEngine | None = None,
    memory_engine: Any = None,
) -> CapabilityManager:
    """Factory creating a CapabilityManager populated with standard subsystem adapters.

    Args:
        input_processor: Optional custom InputProcessor.
        intent_analyzer: Optional custom IntentAnalyzer.
        planner: Optional custom Planner.
        execution_engine: Optional custom ExecutionEngine.
        memory_engine: Optional custom MemoryEngine for MemoryCapability.

    Returns:
        A fully configured CapabilityManager with standard capabilities.
    """
    from argos.memory.memory_capability import MemoryCapability

    return CapabilityManager(
        capabilities=[
            InputCapability(input_processor),
            IntentCapability(intent_analyzer),
            PlanningCapability(planner),
            ExecutionCapability(execution_engine),
            MemoryCapability(memory_engine),
        ]
    )
