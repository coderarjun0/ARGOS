"""Definition of the ActionRouter class.

This module provides a registry-based routing mechanism to map planning Actions
to concrete ActionExecutor implementations.
"""

from argos.execution.action_executor import ActionExecutor
from argos.execution.exceptions import RoutingError
from argos.planning.action import Action


class ActionRouter:
    """Registry router mapping Action enums to registered executors.

    Allows runtime registration to enable plugin extensibility.
    """

    def __init__(self) -> None:
        """Initializes the ActionRouter with an empty registry."""
        self._registry: dict[Action, ActionExecutor] = {}

    def register(self, action: Action, executor: ActionExecutor) -> None:
        """Registers an executor implementation to handle a specific action.

        Args:
            action: The Action StrEnum target.
            executor: The ActionExecutor implementation to execute the action.
        """
        self._registry[action] = executor

    def route(self, action: Action) -> ActionExecutor:
        """Resolves the registered executor for a given action.

        Args:
            action: The Action StrEnum target.

        Returns:
            The registered ActionExecutor implementation.

        Raises:
            RoutingError: If no executor is registered for the action type.
        """
        if action not in self._registry:
            raise RoutingError(
                f"No executor is registered to handle action: {action}"
            )
        return self._registry[action]
