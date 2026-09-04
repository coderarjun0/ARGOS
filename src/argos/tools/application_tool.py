"""ApplicationLauncherTool implementation.

This module provides the domain tool for launching approved host applications
via injected platform OS adapters.
"""

from typing import Any

from argos.tools.adapters.base_platform import BasePlatformAdapter
from argos.tools.base_tool import BaseTool, SideEffectClass, ToolManifest, ToolResult
from argos.tools.exceptions import InvalidParameterError, PlatformExecutionError


class ApplicationLauncherTool(BaseTool):
    """Real system tool for launching approved host applications."""

    APPROVED_APPLICATIONS: tuple[str, ...] = ("calculator", "calc", "notepad")

    def __init__(self, platform_adapter: BasePlatformAdapter) -> None:
        """Initializes ApplicationLauncherTool with a platform adapter.

        Args:
            platform_adapter: Concrete BasePlatformAdapter for OS process dispatch.
        """
        self._platform = platform_adapter
        self._manifest = ToolManifest(
            tool_id="tool.app.launcher",
            version="1.0.0",
            description="Launches approved host applications.",
            supported_actions=("open_app",),
            side_effect=SideEffectClass.MUTATING_REVERSIBLE,
            is_reversible=True,
            default_timeout_seconds=5.0,
        )

    @property
    def manifest(self) -> ToolManifest:
        """Returns the tool manifest."""
        return self._manifest

    @property
    def platform_adapter(self) -> BasePlatformAdapter:
        """Public access to underlying platform adapter."""
        return self._platform

    def validate_parameters(self, parameters: dict[str, Any]) -> None:
        """Validates application launcher parameters.

        Args:
            parameters: Parameter dict containing 'application'.

        Raises:
            InvalidParameterError: If 'application' is missing, non-string, or unmapped.
        """
        app = parameters.get("application")
        if not app or not isinstance(app, str) or not app.strip():
            raise InvalidParameterError(
                "Missing or invalid required parameter 'application' "
                "(must be a non-empty string)."
            )

        app_normalized = app.strip().lower()
        if app_normalized not in self.APPROVED_APPLICATIONS:
            raise InvalidParameterError(
                f"Application '{app}' is not in the approved application whitelist: "
                f"{self.APPROVED_APPLICATIONS}"
            )

    def run(self, parameters: dict[str, Any]) -> ToolResult:
        """Executes application launch via platform adapter.

        Args:
            parameters: Validated parameter dictionary.

        Returns:
            A ToolResult containing PID and launch confirmation message.

        Raises:
            PlatformExecutionError: On OS execution failure.
        """
        app_name = str(parameters["application"]).strip().lower()
        try:
            launch_info = self._platform.launch_known_application(app_name)
            pid = launch_info.get("pid")
            pid_str = f" (PID: {pid})" if pid else ""
            msg = f"Application '{app_name}' launched successfully{pid_str}."

            return ToolResult(
                success=True,
                message=msg,
                metadata=launch_info,
            )
        except PlatformExecutionError:
            raise
        except Exception as err:
            raise PlatformExecutionError(
                f"Unexpected platform failure launching application '{app_name}': {err}"
            ) from err
