"""Discovery DTOs for the ARGOS Capability Ecosystem & Domain Registry."""

from dataclasses import dataclass

from argos.planning.action import Action
from argos.tools.base_tool import ParameterSpec, RiskClass


@dataclass(frozen=True, slots=True)
class ActionSchemaDescriptor:
    """Abstract descriptor exposing an action's parameter schema for discovery."""

    action: Action
    tool_id: str
    risk_class: RiskClass
    parameters: tuple[ParameterSpec, ...]


@dataclass(frozen=True, slots=True)
class DomainDescriptor:
    """Abstract descriptor exposing domain discovery metadata."""

    domain_id: str
    name: str
    description: str
    supported_actions: tuple[Action, ...]


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Abstract descriptor exposing tool discovery metadata."""

    tool_id: str
    version: str
    description: str
    supported_actions: tuple[Action, ...]
    risk_class: RiskClass
