"""Windows Win32PlatformAdapter implementation.

This module owns Windows-specific application resolution and process launching
via argument-list subprocess invocation without shell expansion.
"""

import subprocess
from typing import Any

from argos.tools.adapters.base_platform import BasePlatformAdapter
from argos.tools.exceptions import PlatformExecutionError


class Win32PlatformAdapter(BasePlatformAdapter):
    """Platform adapter implementing real Windows application execution."""

    # Trusted immutable application mapping
    APPROVED_APPLICATIONS: dict[str, str] = {
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "notepad": "notepad.exe",
    }

    @property
    def platform_name(self) -> str:
        """Returns platform identifier."""
        return "win32"

    def launch_known_application(self, application_name: str) -> dict[str, Any]:
        """Launches a whitelisted Windows GUI application as a detached process.

        Args:
            application_name: Normalized application key (e.g. 'calculator').

        Returns:
            Dictionary containing PID and launch confirmation metadata.

        Raises:
            PlatformExecutionError: If application is unmapped or launch fails.
        """
        app_key = application_name.strip().lower()
        if app_key not in self.APPROVED_APPLICATIONS:
            raise PlatformExecutionError(
                f"Application '{application_name}' is not in the Win32 approved list."
            )

        binary = self.APPROVED_APPLICATIONS[app_key]

        try:
            # Launch process with shell=False using explicit binary list
            proc = subprocess.Popen([binary], shell=False)
            return {
                "pid": proc.pid,
                "application": app_key,
                "binary": binary,
                "status": "launched",
                "detached": True,
            }
        except Exception as err:
            raise PlatformExecutionError(
                f"Failed to launch Windows process '{binary}': {err}"
            ) from err
