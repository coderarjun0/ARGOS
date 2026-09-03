"""Memory Engine facade for ARGOS (ADS-006 Milestone 5).

Orchestrates transient Session Memory, durable Persistent Semantic Memory (SQLite),
and explicit user consent authorization boundaries. Acts as the primary facade
for memory interactions without violating Clean Architecture or privacy requirements.
"""

import sqlite3
from pathlib import Path
from typing import Any

from argos.memory.consent_manager import ConsentManager
from argos.memory.constants import DEFAULT_SESSION_ID
from argos.memory.exceptions import (
    MemoryError,
    MemoryStorageError,
)
from argos.memory.models import (
    AuthorizationRecord,
    MemoryRecord,
    SessionTurn,
)
from argos.memory.session_store import SessionStore
from argos.memory.sqlite_store import PersistentStore, SQLiteStore


class MemoryEngine:
    """Primary public facade orchestrating session and persistent memory operations."""

    def __init__(
        self,
        session_store: SessionStore | None = None,
        persistent_store: PersistentStore | None = None,
        consent_manager: ConsentManager | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        """Initializes MemoryEngine with explicit dependency injection.

        Args:
            session_store: Session memory store instance.
            persistent_store: Persistent memory store instance.
            consent_manager: Consent manager instance.
            db_path: Target database path for persistent store if None.

        Raises:
            MemoryStorageError: If database initialization fails.
            MemoryValidationError: If parameters are invalid.
        """
        self._session_store = (
            session_store if session_store is not None else SessionStore()
        )
        self._consent_manager = (
            consent_manager if consent_manager is not None else ConsentManager()
        )
        if persistent_store is not None:
            self._persistent_store = persistent_store
        else:
            self._persistent_store = SQLiteStore(db_path=db_path)

    @property
    def session_store(self) -> SessionStore:
        """Returns the configured SessionStore instance."""
        return self._session_store

    @property
    def persistent_store(self) -> PersistentStore:
        """Returns the configured PersistentStore instance."""
        return self._persistent_store

    @property
    def consent_manager(self) -> ConsentManager:
        """Returns the configured ConsentManager instance."""
        return self._consent_manager

    # =========================================================================
    # Session Memory Operations
    # =========================================================================

    def record_turn(self, turn: SessionTurn) -> SessionTurn:
        """Records a conversational turn in transient Session Memory.

        Args:
            turn: The SessionTurn object to record.

        Returns:
            The recorded SessionTurn instance.

        Raises:
            MemoryValidationError: If turn or session_id is invalid.
        """
        return self._session_store.record_turn(turn)

    def get_session_turns(
        self,
        session_id: str = DEFAULT_SESSION_ID,
        limit: int = 10,
    ) -> list[SessionTurn]:
        """Retrieves recent turns from Session Memory in chronological order.

        Args:
            session_id: Session identifier string.
            limit: Maximum number of recent turns to return.

        Returns:
            List of matching SessionTurn objects.

        Raises:
            MemoryValidationError: If session_id or limit is invalid.
        """
        return self._session_store.get_session_turns(
            session_id=session_id, limit=limit
        )

    def get_turn_count(self, session_id: str = DEFAULT_SESSION_ID) -> int:
        """Returns the total number of turns stored for a session.

        Args:
            session_id: Session identifier string.

        Returns:
            Integer turn count.

        Raises:
            MemoryValidationError: If session_id is invalid.
        """
        return self._session_store.get_turn_count(session_id=session_id)

    def clear_session(self, session_id: str = DEFAULT_SESSION_ID) -> bool:
        """Clears transient turn history for a specified session.

        Args:
            session_id: Session identifier string.

        Returns:
            True if an active session was cleared, False otherwise.

        Raises:
            MemoryValidationError: If session_id is invalid.
        """
        return self._session_store.clear_session(session_id=session_id)

    # =========================================================================
    # Persistent Semantic Memory Reads
    # =========================================================================

    def get_exact(self, category: str, key: str) -> MemoryRecord | None:
        """Retrieves a persistent memory record by exact category and key.

        Args:
            category: Domain category name.
            key: Memory key identifier.

        Returns:
            Matching MemoryRecord or None.

        Raises:
            MemoryValidationError: If category or key format is invalid.
            MemoryStorageError: If database retrieval encounters failure.
        """
        try:
            return self._persistent_store.get_exact(category, key)
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to retrieve memory record '{category}:{key}': {err}"
            ) from err

    def list_by_category(self, category: str) -> list[MemoryRecord]:
        """Lists all persistent memory records in a category ordered by key.

        Args:
            category: Domain category name.

        Returns:
            List of matching MemoryRecord objects.

        Raises:
            MemoryValidationError: If category format is invalid.
            MemoryStorageError: If database access fails.
        """
        try:
            return self._persistent_store.list_by_category(category)
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to list records for category '{category}': {err}"
            ) from err

    def search_by_prefix(self, category: str, prefix: str) -> list[MemoryRecord]:
        """Searches persistent memory records in a category matching key prefix.

        Args:
            category: Domain category name.
            prefix: Key prefix string.

        Returns:
            List of matching MemoryRecord objects.

        Raises:
            MemoryValidationError: If category or prefix is invalid.
            MemoryStorageError: If database access fails.
        """
        try:
            return self._persistent_store.search_by_prefix(category, prefix)
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to search records for category '{category}': {err}"
            ) from err

    def inspect_all(self) -> list[dict[str, Any]]:
        """Provides a local, read-only inspection view of persistent memory records.

        Returns:
            List of dicts exposing stored values and authorization provenance.

        Raises:
            MemoryStorageError: If database query fails.
        """
        try:
            return self._persistent_store.inspect_all()
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to inspect persistent memories: {err}"
            ) from err

    def export_to_dict(self) -> dict[str, Any]:
        """Generates a structured export dictionary of persistent semantic memory.

        Excludes Session Memory. Read-only operation.

        Returns:
            Dictionary containing export metadata and all persistent records.

        Raises:
            MemoryStorageError: If export fails.
        """
        try:
            return self._persistent_store.export_to_dict()
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to export persistent memory: {err}"
            ) from err

    # =========================================================================
    # Persistent Semantic Memory Mutations (Consent Required)
    # =========================================================================

    def store_persistent(
        self,
        category: str,
        key: str,
        value: Any,
        authorization: AuthorizationRecord,
        source: str = "user_explicit",
    ) -> MemoryRecord:
        """Persists a semantic memory record with explicit user consent validation.

        Args:
            category: Domain category identifier.
            key: Memory key identifier.
            value: JSON-serializable value payload.
            authorization: User authorization record.
            source: Memory source provenance metadata string.

        Returns:
            The compiled MemoryRecord object.

        Raises:
            MemoryAuthorizationError: If authorization is denied or unapproved.
            MemoryValidationError: If inputs are invalid or key exists.
            MemoryStorageError: If database insertion fails.
        """
        self._consent_manager.validate_authorization(authorization)
        try:
            return self._persistent_store.store_persistent(
                category=category,
                key=key,
                value=value,
                authorization=authorization,
                source=source,
            )
        except (MemoryError, sqlite3.Error) as err:
            if isinstance(err, MemoryError):
                raise
            raise MemoryStorageError(
                f"Failed to store persistent memory '{category}:{key}': {err}"
            ) from err

    def update_persistent(
        self,
        category: str,
        key: str,
        new_value: Any,
        authorization: AuthorizationRecord,
    ) -> MemoryRecord:
        """Updates an existing persistent memory record with explicit consent.

        Args:
            category: Domain category identifier.
            key: Memory key identifier.
            new_value: New JSON-serializable value payload.
            authorization: User authorization record.

        Returns:
            The updated MemoryRecord object.

        Raises:
            MemoryAuthorizationError: If authorization is denied or unapproved.
            MemoryNotFoundError: If key does not exist.
            MemoryValidationError: If inputs are invalid.
            MemoryStorageError: If database update fails.
        """
        self._consent_manager.validate_authorization(authorization)
        try:
            return self._persistent_store.update_persistent(
                category=category,
                key=key,
                new_value=new_value,
                authorization=authorization,
            )
        except (MemoryError, sqlite3.Error) as err:
            if isinstance(err, MemoryError):
                raise
            raise MemoryStorageError(
                f"Failed to update persistent memory '{category}:{key}': {err}"
            ) from err

    def delete_persistent(
        self,
        category: str,
        key: str,
        authorization: AuthorizationRecord,
    ) -> bool:
        """Deletes an existing persistent memory record with explicit consent.

        Args:
            category: Domain category identifier.
            key: Memory key identifier.
            authorization: User authorization record.

        Returns:
            True upon confirmed deletion.

        Raises:
            MemoryAuthorizationError: If authorization is denied or unapproved.
            MemoryNotFoundError: If key does not exist.
            MemoryValidationError: If inputs are invalid.
            MemoryStorageError: If database deletion fails.
        """
        self._consent_manager.validate_authorization(authorization)
        try:
            return self._persistent_store.delete_persistent(
                category=category,
                key=key,
                authorization=authorization,
            )
        except (MemoryError, sqlite3.Error) as err:
            if isinstance(err, MemoryError):
                raise
            raise MemoryStorageError(
                f"Failed to delete persistent memory '{category}:{key}': {err}"
            ) from err

    # =========================================================================
    # Consent Helper Delegation
    # =========================================================================

    def grant_explicit_consent(
        self, details: str | None = None
    ) -> AuthorizationRecord:
        """Creates an AuthorizationRecord representing explicit user consent.

        Args:
            details: Optional audit provenance message.

        Returns:
            AuthorizationRecord with granted=True and auth_type=EXPLICIT_USER_CONSENT.

        Raises:
            MemoryAuthorizationError: If details is not a string or None.
        """
        return self._consent_manager.grant_explicit_consent(details=details)

    def deny_consent(self, details: str | None = None) -> AuthorizationRecord:
        """Creates an AuthorizationRecord representing explicit user consent denial.

        Args:
            details: Optional denial audit message.

        Returns:
            AuthorizationRecord with granted=False and auth_type=EXPLICIT_USER_CONSENT.

        Raises:
            MemoryAuthorizationError: If details is not a string or None.
        """
        return self._consent_manager.deny_consent(details=details)

    def validate_authorization(self, authorization: AuthorizationRecord) -> None:
        """Validates that an AuthorizationRecord permits persistent mutation in V1.

        Args:
            authorization: The AuthorizationRecord to validate.

        Raises:
            MemoryAuthorizationError: If authorization is invalid or denied.
        """
        self._consent_manager.validate_authorization(authorization)

    def is_authorized(self, authorization: AuthorizationRecord) -> bool:
        """Checks whether an AuthorizationRecord permits persistent mutation in V1.

        Args:
            authorization: The AuthorizationRecord to evaluate.

        Returns:
            True if authorized, False otherwise.
        """
        return self._consent_manager.is_authorized(authorization)

    # =========================================================================
    # Context Manager and Lifecycle
    # =========================================================================

    def close(self) -> None:
        """Cleanly closes underlying persistent storage resources."""
        if hasattr(self._persistent_store, "close"):
            try:
                self._persistent_store.close()
            except Exception:
                pass

    def __enter__(self) -> "MemoryEngine":
        """Context manager entry returning self instance."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit closing underlying storage connection."""
        self.close()
