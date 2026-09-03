"""In-memory Session Memory store for ARGOS (ADS-006 Milestone 2).

Provides deterministic, FIFO-bounded, turn-based conversational continuity across
multi-turn interactions within an active session. Data is strictly in-memory and
ephemeral, resetting upon session clearance or process termination.
"""

import re
from collections import deque

from argos.memory.constants import (
    DEFAULT_MAX_SESSION_TURNS,
    DEFAULT_SESSION_ID,
)
from argos.memory.exceptions import MemoryValidationError
from argos.memory.models import SessionTurn

# Allowed session ID pattern: alphanumeric, hyphen, underscore
_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_session_id(session_id: str) -> str:
    """Validates and returns a session ID string.

    Args:
        session_id: The session identifier to validate.

    Returns:
        The validated session ID string.

    Raises:
        MemoryValidationError: If session_id is not a string, is empty,
            contains leading/trailing whitespace, or contains invalid characters.
    """
    if not isinstance(session_id, str):
        raise MemoryValidationError(
            f"Session ID must be a string, got {type(session_id).__name__}."
        )

    if not session_id or session_id != session_id.strip():
        raise MemoryValidationError(
            "Session ID must be a non-empty string without whitespace."
        )

    if not _SESSION_ID_PATTERN.match(session_id):
        raise MemoryValidationError(
            f"Invalid Session ID '{session_id}'. Must contain only alphanumeric, "
            "hyphen, and underscore characters."
        )

    return session_id


class SessionStore:
    """In-memory bounded FIFO turn tracker for multi-turn session dialogue."""

    def __init__(self, max_turns: int = DEFAULT_MAX_SESSION_TURNS) -> None:
        """Initializes a new SessionStore instance.

        Args:
            max_turns: Maximum turns to retain per session before FIFO eviction.

        Raises:
            MemoryValidationError: If max_turns is not a positive integer.
        """
        if (
            not isinstance(max_turns, int)
            or isinstance(max_turns, bool)
            or max_turns <= 0
        ):
            raise MemoryValidationError(
                f"max_turns must be a positive integer, got {max_turns}."
            )

        self._max_turns = max_turns
        self._sessions: dict[str, deque[SessionTurn]] = {}

    @property
    def max_turns(self) -> int:
        """Returns the maximum turns capacity per session."""
        return self._max_turns

    def record_turn(self, turn: SessionTurn) -> SessionTurn:
        """Appends a conversation turn to the designated session.

        Enforces deterministic FIFO eviction when turn count exceeds capacity.

        Args:
            turn: The SessionTurn object to record.

        Returns:
            The recorded SessionTurn object.

        Raises:
            MemoryValidationError: If turn is not a SessionTurn or has invalid ID.
        """
        if not isinstance(turn, SessionTurn):
            raise MemoryValidationError(
                f"Expected SessionTurn instance, got {type(turn).__name__}."
            )

        session_id = validate_session_id(turn.session_id)

        if session_id not in self._sessions:
            self._sessions[session_id] = deque(maxlen=self._max_turns)

        self._sessions[session_id].append(turn)
        return turn

    def get_session_turns(
        self,
        session_id: str = DEFAULT_SESSION_ID,
        limit: int = 10,
    ) -> list[SessionTurn]:
        """Retrieves the most recent N turns for a session in chronological order.

        Does not mutate the stored session state.

        Args:
            session_id: The target session identifier.
            limit: Maximum number of recent turns to return.

        Returns:
            List of most recent SessionTurn objects in chronological order.

        Raises:
            MemoryValidationError: If session_id is invalid or limit is invalid.
        """
        valid_id = validate_session_id(session_id)

        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise MemoryValidationError(
                f"Limit must be a positive integer, got {limit}."
            )

        if valid_id not in self._sessions:
            return []

        turns = list(self._sessions[valid_id])
        if len(turns) <= limit:
            return turns
        return turns[-limit:]

    def get_turn_count(self, session_id: str = DEFAULT_SESSION_ID) -> int:
        """Returns the current number of stored turns for a session.

        Args:
            session_id: The target session identifier.

        Returns:
            Integer count of stored turns.

        Raises:
            MemoryValidationError: If session_id is invalid.
        """
        valid_id = validate_session_id(session_id)
        if valid_id not in self._sessions:
            return 0
        return len(self._sessions[valid_id])

    def clear_session(self, session_id: str = DEFAULT_SESSION_ID) -> bool:
        """Clears all turns for a specific session.

        Args:
            session_id: The target session identifier to clear.

        Returns:
            True if session existed and was cleared, False if non-existent.

        Raises:
            MemoryValidationError: If session_id is invalid.
        """
        valid_id = validate_session_id(session_id)

        if valid_id in self._sessions:
            del self._sessions[valid_id]
            return True

        return False
