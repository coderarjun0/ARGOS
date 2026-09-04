"""File System Operations Domain implementation."""

from argos.capabilities.base_domain import CapabilityDomain
from argos.planning.action import Action


class FileSystemDomain(CapabilityDomain):
    """Capability Domain for file system management capabilities."""

    @property
    def domain_id(self) -> str:
        """Returns unique domain identifier."""
        return "domain.filesystem"

    @property
    def name(self) -> str:
        """Returns domain display name."""
        return "File System Operations Domain"

    @property
    def description(self) -> str:
        """Returns domain description."""
        return (
            "Manages sandboxed local file system read, write, creation, "
            "and directory listing actions."
        )

    @property
    def supported_actions(self) -> tuple[Action, ...]:
        """Returns supported Action enums for this domain."""
        return (
            Action.READ_FILE,
            Action.WRITE_FILE,
            Action.CREATE_FILE,
            Action.LIST_DIR,
        )
