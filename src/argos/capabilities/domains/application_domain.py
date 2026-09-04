"""Application Execution Domain implementation."""

from argos.capabilities.base_domain import CapabilityDomain
from argos.planning.action import Action


class ApplicationDomain(CapabilityDomain):
    """Capability Domain for host application management capabilities."""

    @property
    def domain_id(self) -> str:
        """Returns unique domain identifier."""
        return "domain.application"

    @property
    def name(self) -> str:
        """Returns domain display name."""
        return "Application Execution Domain"

    @property
    def description(self) -> str:
        """Returns domain description."""
        return "Manages host OS application launch and process lifecycle capabilities."

    @property
    def supported_actions(self) -> tuple[Action, ...]:
        """Returns supported Action enums for this domain."""
        return (Action.OPEN_APP, Action.CLOSE_APP)
