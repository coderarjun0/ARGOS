"""Abstract Base Class for Capability Domains."""

from abc import ABC, abstractmethod

from argos.capabilities.models import DomainDescriptor
from argos.planning.action import Action


class CapabilityDomain(ABC):
    """Abstract base class defining a tool ecosystem Capability Domain."""

    @property
    @abstractmethod
    def domain_id(self) -> str:
        """Unique domain identifier (e.g. 'domain.application')."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name of the capability domain."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of capability domain scope."""

    @property
    @abstractmethod
    def supported_actions(self) -> tuple[Action, ...]:
        """Tuple of canonical Action enums assigned to this domain."""

    def to_descriptor(self) -> DomainDescriptor:
        """Converts domain metadata to an immutable DomainDescriptor DTO."""
        return DomainDescriptor(
            domain_id=self.domain_id,
            name=self.name,
            description=self.description,
            supported_actions=self.supported_actions,
        )
