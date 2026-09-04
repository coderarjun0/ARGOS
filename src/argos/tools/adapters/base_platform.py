"""BasePlatformAdapter ABC defining the platform OS execution protocol.

This module provides the platform abstraction boundary isolating OS mechanics
from domain and tool logic.
"""

from abc import ABC, abstractmethod
from typing import Any


class BasePlatformAdapter(ABC):
    """Abstract interface defining platform-specific system operations."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Returns the canonical platform identifier string (e.g. 'win32')."""

    @abstractmethod
    def launch_known_application(self, application_name: str) -> dict[str, Any]:
        """Launches an approved, whitelisted host application.

        Args:
            application_name: The normalized application key (e.g. 'calculator').

        Returns:
            Dictionary containing launch metadata (e.g. pid, application).

        Raises:
            PlatformExecutionError: If launch fails or application is unmapped.
        """
