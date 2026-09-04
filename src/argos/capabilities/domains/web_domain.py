"""Web & Network Domain implementation."""

from argos.capabilities.base_domain import CapabilityDomain
from argos.planning.action import Action


class WebDomain(CapabilityDomain):
    """Capability Domain for web search and network query capabilities."""

    @property
    def domain_id(self) -> str:
        """Returns unique domain identifier."""
        return "domain.web"

    @property
    def name(self) -> str:
        """Returns domain display name."""
        return "Web & Network Domain"

    @property
    def description(self) -> str:
        """Returns domain description."""
        return "Manages web search and remote information discovery capabilities."

    @property
    def supported_actions(self) -> tuple[Action, ...]:
        """Returns supported Action enums for this domain."""
        return (Action.SEARCH_WEB,)
