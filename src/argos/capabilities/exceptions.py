"""Exception hierarchy for the ARGOS Capability Ecosystem & Domain Registry."""


class CapabilityRegistryError(Exception):
    """Base exception for all Capability Registry errors."""


class CapabilityDomainError(CapabilityRegistryError):
    """Base exception for Capability Domain errors."""


class ActionNotFoundError(CapabilityRegistryError):
    """Raised when no registered tool supports the requested Action."""


class AmbiguousActionError(CapabilityRegistryError):
    """Raised when multiple tools support the same Action."""


class RegistryFrozenError(CapabilityRegistryError):
    """Raised when attempting to mutate CapabilityRegistry post-freeze."""


class DuplicateDomainError(CapabilityRegistryError):
    """Raised when attempting to register a domain with an existing domain_id."""


class DuplicateToolIndexError(CapabilityRegistryError):
    """Raised when attempting to index a tool with an existing tool_id."""
