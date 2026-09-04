"""System Information & Telemetry Domain implementation."""

from argos.capabilities.base_domain import CapabilityDomain
from argos.planning.action import Action


class SystemInfoDomain(CapabilityDomain):
    """Capability Domain for system telemetry and metric query capabilities."""

    @property
    def domain_id(self) -> str:
        """Returns unique domain identifier."""
        return "domain.system_info"

    @property
    def name(self) -> str:
        """Returns domain display name."""
        return "System Information & Telemetry Domain"

    @property
    def description(self) -> str:
        """Returns domain description."""
        return (
            "Manages system environment inspection and platform telemetry queries."
        )

    @property
    def supported_actions(self) -> tuple[Action, ...]:
        """Returns supported Action enums for this domain."""
        return (Action.QUERY_SYS_INFO,)
