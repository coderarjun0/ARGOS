"""BaseTool ABC and ToolManifest dataclass definitions.

This module defines the contract interface implemented by all real system tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SideEffectClass(StrEnum):
    """Enumeration of tool side-effect severity classes."""

    READ_ONLY = "read_only"
    MUTATING_REVERSIBLE = "mutating_reversible"
    MUTATING_IRREVERSIBLE = "mutating_irreversible"


class RiskClass(StrEnum):
    """Enumeration of operational risk classifications for tool manifests."""

    READ_ONLY = "read_only"
    LOCAL_MUTATION_REVERSIBLE = "local_mutation_reversible"
    LOCAL_MUTATION_IRREVERSIBLE = "local_mutation_irreversible"
    NETWORK_READ = "network_read"
    EXTERNAL_MUTATION = "external_mutation"
    DESTRUCTIVE_PRIVILEGED = "destructive_privileged"


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Specification contract for a tool parameter."""

    name: str
    param_type: type
    required: bool = True
    default: Any = None
    allowed_values: tuple[Any, ...] | None = None


@dataclass(frozen=True, slots=True)
class ToolManifest:
    """Declarative manifest describing a real system tool's properties.

    Attributes:
        tool_id: Unique string identifier for the tool.
        version: Semantic version string of the tool specification.
        description: Human-readable explanation of tool functionality.
        supported_actions: Canonical Action names handled by the tool.
        side_effect: Side-effect classification rating.
        is_reversible: True if a compensating inverse action exists.
        default_timeout_seconds: Hard execution timeout boundary.
        risk_class: Operational risk classification rating.
        parameter_specs: Tuple of parameter specification contracts.
    """

    tool_id: str
    version: str
    description: str
    supported_actions: tuple[str, ...]
    side_effect: SideEffectClass = SideEffectClass.READ_ONLY
    is_reversible: bool = False
    default_timeout_seconds: float = 5.0
    risk_class: RiskClass = RiskClass.READ_ONLY
    parameter_specs: tuple[ParameterSpec, ...] = ()



@dataclass(slots=True)
class ToolResult:
    """Container holding outcome metrics and output from tool execution.

    Attributes:
        success: True if execution completed successfully, False otherwise.
        message: Diagnostic output string or launch confirmation.
        metadata: Execution contextual key-value pairs (e.g. PID, exit code).
    """

    success: bool
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract interface defining the execution protocol for real system tools."""

    @property
    @abstractmethod
    def manifest(self) -> ToolManifest:
        """Returns the declarative ToolManifest describing this tool."""

    @abstractmethod
    def validate_parameters(self, parameters: dict[str, Any]) -> None:
        """Validates parameter keys and types prior to execution.

        Args:
            parameters: Key-value parameters passed to tool invocation.

        Raises:
            InvalidParameterError: If any parameter is invalid or missing.
        """

    @abstractmethod
    def run(self, parameters: dict[str, Any]) -> ToolResult:
        """Executes the tool with validated parameters.

        Args:
            parameters: Key-value parameters for tool execution.

        Returns:
            A ToolResult containing execution outcome and metadata.

        Raises:
            ToolError: On tool execution failure.
        """
