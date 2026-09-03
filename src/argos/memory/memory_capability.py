"""Cognitive capability adapter wrapping MemoryEngine (ADS-006 Milestone 6).

Integrates memory functionality into the ARGOS Brain Core capability structure.
"""

from typing import Any

from argos.brain.capability_manager import CognitiveCapability
from argos.memory.exceptions import MemoryValidationError
from argos.memory.memory_engine import MemoryEngine

CAPABILITY_MEMORY: str = "memory"


class MemoryCapability(CognitiveCapability):
    """Adapter integrating MemoryEngine as a CognitiveCapability for BrainCore."""

    def __init__(self, memory_engine: MemoryEngine | None = None) -> None:
        """Initializes MemoryCapability with an optional injected MemoryEngine.

        Args:
            memory_engine: Custom MemoryEngine instance. Defaults to new MemoryEngine().
        """
        self._engine = memory_engine if memory_engine is not None else MemoryEngine()

    @property
    def name(self) -> str:
        """Unique identifier of the memory capability."""
        return CAPABILITY_MEMORY

    @property
    def engine(self) -> MemoryEngine:
        """Returns the wrapped MemoryEngine instance."""
        return self._engine

    def execute(self, action: str, *args: Any, **kwargs: Any) -> Any:
        """Executes a memory action by dispatching to MemoryEngine.

        Args:
            action: The memory action identifier string.
            *args: Positional arguments to forward to MemoryEngine.
            **kwargs: Keyword arguments to forward to MemoryEngine.

        Returns:
            Result returned by the corresponding MemoryEngine method.

        Raises:
            MemoryValidationError: If action is unknown or parameters are invalid.
            MemoryAuthorizationError: If authorization is denied or unapproved.
            MemoryNotFoundError: If target persistent record is missing.
            MemoryStorageError: If persistent storage backend fails.
        """
        if not isinstance(action, str) or not action.strip():
            msg = "Action must be a non-empty string."
            raise MemoryValidationError(msg)

        supported_actions = {
            # Session
            "record_turn",
            "get_session_turns",
            "get_turn_count",
            "clear_session",
            # Persistent Read
            "get_exact",
            "list_by_category",
            "search_by_prefix",
            "inspect_all",
            "export_to_dict",
            # Persistent Mutation
            "store_persistent",
            "update_persistent",
            "delete_persistent",
            # Consent Helpers
            "grant_explicit_consent",
            "deny_consent",
            "validate_authorization",
            "is_authorized",
        }

        if action not in supported_actions:
            msg = f"Unsupported memory capability action: '{action}'."
            raise MemoryValidationError(msg)

        method = getattr(self._engine, action, None)
        if method is None or not callable(method):
            msg = f"Memory engine method missing for action: '{action}'."
            raise MemoryValidationError(msg)

        return method(*args, **kwargs)
