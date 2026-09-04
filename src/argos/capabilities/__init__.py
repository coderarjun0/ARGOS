"""ARGOS Capability Ecosystem & Domain Registry package.

Exposes domain metadata and tool schema discovery descriptors for the cognitive planner.
"""

from argos.capabilities.base_domain import CapabilityDomain
from argos.capabilities.capability_registry import CapabilityRegistry
from argos.capabilities.domains import (
    ApplicationDomain,
    FileSystemDomain,
    SystemInfoDomain,
    WebDomain,
)
from argos.capabilities.exceptions import (
    ActionNotFoundError,
    AmbiguousActionError,
    CapabilityDomainError,
    CapabilityRegistryError,
    DuplicateDomainError,
    DuplicateToolIndexError,
    RegistryFrozenError,
)
from argos.capabilities.models import (
    ActionSchemaDescriptor,
    DomainDescriptor,
    ToolDescriptor,
)

__all__ = [
    "ActionNotFoundError",
    "ActionSchemaDescriptor",
    "AmbiguousActionError",
    "ApplicationDomain",
    "CapabilityDomain",
    "CapabilityDomainError",
    "CapabilityRegistry",
    "CapabilityRegistryError",
    "DomainDescriptor",
    "DuplicateDomainError",
    "DuplicateToolIndexError",
    "FileSystemDomain",
    "RegistryFrozenError",
    "SystemInfoDomain",
    "ToolDescriptor",
    "WebDomain",
]
