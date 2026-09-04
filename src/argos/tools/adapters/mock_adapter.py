"""MockPlatformAdapter implementation for testing.

This module provides a simulated platform adapter for fast, deterministic,
side-effect-free testing without launching real OS processes.
"""

from typing import Any

from argos.tools.adapters.base_platform import BasePlatformAdapter
from argos.tools.exceptions import PlatformExecutionError


class MockPlatformAdapter(BasePlatformAdapter):
    """Test fixture platform adapter simulating OS application launches."""

    def __init__(
        self,
        should_fail: bool = False,
        simulated_pid: int = 9999,
        supported_apps: tuple[str, ...] = ("calculator", "calc", "notepad"),
    ) -> None:
        """Initializes MockPlatformAdapter.

        Args:
            should_fail: If True, launch raises PlatformExecutionError.
            simulated_pid: PID integer returned in launch metadata.
            supported_apps: Tuple of approved app name strings.
        """
        self.should_fail = should_fail
        self.simulated_pid = simulated_pid
        self.supported_apps = supported_apps
        self.launched_history: list[str] = []

    @property
    def platform_name(self) -> str:
        """Returns mock platform identifier."""
        return "mock"

    def launch_known_application(self, application_name: str) -> dict[str, Any]:
        """Simulates launching a known application.

        Args:
            application_name: The application identifier string.

        Returns:
            Dictionary containing mock launch metadata.

        Raises:
            PlatformExecutionError: If configured to fail or application is unmapped.
        """
        app_key = application_name.strip().lower()

        if self.should_fail:
            raise PlatformExecutionError(
                f"Simulated platform failure for '{application_name}'."
            )

        if app_key not in self.supported_apps:
            raise PlatformExecutionError(
                f"Application '{application_name}' is not in the mock approved list."
            )

        self.launched_history.append(app_key)
        return {
            "pid": self.simulated_pid,
            "application": app_key,
            "binary": f"{app_key}.exe",
            "status": "launched",
            "detached": True,
            "simulated": True,
        }
