"""ToolRegistry implementation.

This module provides the registry for discovering BaseTool instances.
"""

from argos.tools.base_tool import BaseTool
from argos.tools.exceptions import ToolNotFoundError, ToolRegistrationError


class ToolRegistry:
    """Registry managing registered BaseTool instances."""

    def __init__(self) -> None:
        """Initializes an empty ToolRegistry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a BaseTool instance in the registry.

        Args:
            tool: BaseTool instance to register.

        Raises:
            ToolRegistrationError: If tool_id is already registered.
        """
        tool_id = tool.manifest.tool_id
        if tool_id in self._tools:
            raise ToolRegistrationError(
                f"Tool with ID '{tool_id}' is already registered."
            )
        self._tools[tool_id] = tool

    def get_tool(self, tool_id: str) -> BaseTool:
        """Resolves a registered BaseTool by tool_id.

        Args:
            tool_id: Unique tool string identifier.

        Returns:
            The registered BaseTool instance.

        Raises:
            ToolNotFoundError: If no tool is registered for tool_id.
        """
        if tool_id not in self._tools:
            raise ToolNotFoundError(
                f"No tool registered with ID: '{tool_id}'."
            )
        return self._tools[tool_id]

    def get_tools_for_action(self, action: str) -> list[BaseTool]:
        """Resolves all tools supporting a given action name.

        Args:
            action: Action name string (e.g. 'open_app').

        Returns:
            List of BaseTool instances handling the action.
        """
        return [
            tool
            for tool in self._tools.values()
            if action in tool.manifest.supported_actions
        ]

    def list_tools(self) -> list[BaseTool]:
        """Returns a list of all registered BaseTool instances.

        Returns:
            List of BaseTool objects.
        """
        return list(self._tools.values())
