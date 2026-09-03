"""Persistent Semantic Memory SQLite store for ARGOS (ADS-006 Milestone 3).

Provides durable, local, file-backed SQLite storage for structured user facts and
configurations. Implements atomic transaction semantics, schema versioning,
deterministic exact-match retrieval, explicit-consent authorization enforcement,
and read-only user inspection/export.
"""

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from argos.memory.constants import (
    CATEGORY_PATTERN,
    DEFAULT_DB_PATH,
    DEFAULT_TIMEOUT_SECONDS,
    KEY_PATTERN,
    MAX_CATEGORY_LENGTH,
    MAX_KEY_LENGTH,
    MAX_VALUE_BYTES,
    SCHEMA_VERSION,
)
from argos.memory.exceptions import (
    MemoryAuthorizationError,
    MemoryNotFoundError,
    MemoryStorageError,
    MemoryValidationError,
)
from argos.memory.models import (
    AuthorizationRecord,
    AuthorizationType,
    MemoryRecord,
    MemoryScope,
)

_CATEGORY_REGEX = re.compile(CATEGORY_PATTERN)
_KEY_REGEX = re.compile(KEY_PATTERN)


def validate_category(category: str) -> str:
    """Validates and returns a category string.

    Raises:
        MemoryValidationError: If category is invalid or exceeds max length.
    """
    if not isinstance(category, str):
        raise MemoryValidationError(
            f"Category must be a string, got {type(category).__name__}."
        )
    if not category or category != category.strip():
        raise MemoryValidationError(
            "Category must be a non-empty string without whitespace."
        )
    if len(category) > MAX_CATEGORY_LENGTH:
        raise MemoryValidationError(
            f"Category length ({len(category)}) exceeds limit of {MAX_CATEGORY_LENGTH}."
        )
    if not _CATEGORY_REGEX.match(category):
        raise MemoryValidationError(
            f"Invalid category '{category}'. Must match pattern '{CATEGORY_PATTERN}'."
        )
    return category


def validate_key(key: str) -> str:
    """Validates and returns a memory key string.

    Raises:
        MemoryValidationError: If key is invalid or exceeds max length.
    """
    if not isinstance(key, str):
        raise MemoryValidationError(
            f"Memory key must be a string, got {type(key).__name__}."
        )
    if not key or key != key.strip():
        raise MemoryValidationError(
            "Memory key must be a non-empty string without whitespace."
        )
    if len(key) > MAX_KEY_LENGTH:
        raise MemoryValidationError(
            f"Memory key length ({len(key)}) exceeds limit of {MAX_KEY_LENGTH}."
        )
    if not _KEY_REGEX.match(key):
        raise MemoryValidationError(
            f"Invalid memory key '{key}'. Must match pattern '{KEY_PATTERN}'."
        )
    return key


def serialize_value(value: Any) -> str:
    """Serializes a Python value to JSON text and validates payload constraints.

    Raises:
        MemoryValidationError: If value is not JSON-serializable or exceeds size limit.
    """
    try:
        json_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError) as err:
        raise MemoryValidationError(
            f"Memory value is not valid JSON-serializable data: {err}"
        ) from err

    encoded_bytes = json_str.encode("utf-8")
    if len(encoded_bytes) > MAX_VALUE_BYTES:
        raise MemoryValidationError(
            f"Serialized value size ({len(encoded_bytes)} bytes) "
            f"exceeds limit of {MAX_VALUE_BYTES} bytes."
        )

    return json_str


def validate_authorization_for_mutation(auth: AuthorizationRecord) -> None:
    """Validates authorization provenance for persistent memory mutation.

    In V1, EXPLICIT_USER_CONSENT is the ONLY permitted authorization type.

    Raises:
        MemoryAuthorizationError: If authorization is not EXPLICIT_USER_CONSENT.
    """
    if not isinstance(auth, AuthorizationRecord):
        raise MemoryAuthorizationError(
            f"Expected AuthorizationRecord instance, got {type(auth).__name__}."
        )

    if not auth.granted:
        raise MemoryAuthorizationError(
            "Persistent memory mutation denied: authorization.granted is False."
        )

    if auth.auth_type != AuthorizationType.EXPLICIT_USER_CONSENT:
        msg = (
            "Persistent mutation requires EXPLICIT_USER_CONSENT, "
            f"got '{auth.auth_type}'."
        )
        raise MemoryAuthorizationError(msg)


class SQLiteStore:
    """Local SQLite persistent storage implementation for semantic memory."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes SQLiteStore and runs database initialization/migration.

        Args:
            db_path: Path to SQLite database file or ':memory:' for transient store.
            timeout: Connection busy timeout in seconds.

        Raises:
            MemoryValidationError: If parameters are invalid.
            MemoryStorageError: If database connection or schema migration fails.
        """
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or timeout <= 0
        ):
            raise MemoryValidationError(
                f"Timeout must be a positive number, got {timeout}."
            )

        if db_path is None:
            target_path = DEFAULT_DB_PATH
        elif isinstance(db_path, (str, Path)):
            target_path = db_path
        else:
            msg = (
                "db_path must be a string, Path, or None; "
                f"got {type(db_path).__name__}."
            )
            raise MemoryValidationError(msg)

        self._db_path_str = str(target_path)
        self._is_in_memory = self._db_path_str == ":memory:"

        if not self._is_in_memory and isinstance(target_path, Path):
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as err:
                raise MemoryStorageError(
                    f"Failed to create directory for '{target_path}': {err}"
                ) from err

        try:
            self._conn = sqlite3.connect(
                self._db_path_str,
                timeout=float(timeout),
                check_same_thread=True,
            )
            self._conn.row_factory = sqlite3.Row
            if not self._is_in_memory:
                self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to connect to SQLite DB at '{self._db_path_str}': {err}"
            ) from err

        self._init_db()

    @property
    def db_path(self) -> str:
        """Returns the configured database path string."""
        return self._db_path_str

    def _init_db(self) -> None:
        """Creates tables, indexes, and schema migration tracking idempotently."""
        try:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    );
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS semantic_memories (
                        memory_id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        memory_key TEXT NOT NULL,
                        value_json TEXT NOT NULL,
                        source TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        auth_granted INTEGER NOT NULL,
                        auth_type TEXT NOT NULL,
                        auth_timestamp TEXT NOT NULL,
                        auth_details TEXT,
                        CONSTRAINT uq_category_key UNIQUE (category, memory_key)
                    );
                    """
                )
                self._conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memories_cat_key
                    ON semantic_memories (category, memory_key);
                    """
                )
                self._conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memories_updated
                    ON semantic_memories (updated_at);
                    """
                )

                cursor = self._conn.execute(
                    "SELECT version FROM schema_migrations WHERE version = ?;",
                    (SCHEMA_VERSION,),
                )
                if not cursor.fetchone():
                    now_str = datetime.now(UTC).isoformat()
                    sql_mig = (
                        "INSERT INTO schema_migrations "
                        "(version, applied_at) VALUES (?, ?);"
                    )
                    self._conn.execute(sql_mig, (SCHEMA_VERSION, now_str))
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Database schema initialization failed: {err}"
            ) from err

    def store_persistent(
        self,
        category: str,
        key: str,
        value: Any,
        authorization: AuthorizationRecord,
        source: str = "user_explicit",
    ) -> MemoryRecord:
        """Persists a new structured semantic memory entry with explicit user consent.

        Args:
            category: Categorical domain identifier.
            key: Memory key identifier.
            value: JSON-serializable value payload.
            authorization: Consent authorization record.
            source: Memory origin metadata string.

        Returns:
            The compiled MemoryRecord object.

        Raises:
            MemoryValidationError: If parameters are invalid or duplicate key exists.
            MemoryAuthorizationError: If authorization is not EXPLICIT_USER_CONSENT.
            MemoryStorageError: If database insertion fails.
        """
        valid_cat = validate_category(category)
        valid_key = validate_key(key)
        value_json = serialize_value(value)
        validate_authorization_for_mutation(authorization)

        if not isinstance(source, str) or not source.strip():
            raise MemoryValidationError("Source must be a non-empty string.")

        memory_id = f"{valid_cat}:{valid_key}"
        now = datetime.now(UTC)
        now_str = now.isoformat()
        auth_ts_str = authorization.granted_at.isoformat()

        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO semantic_memories (
                        memory_id, category, memory_key, value_json, source,
                        created_at, updated_at, auth_granted, auth_type,
                        auth_timestamp, auth_details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        memory_id,
                        valid_cat,
                        valid_key,
                        value_json,
                        source,
                        now_str,
                        now_str,
                        1 if authorization.granted else 0,
                        authorization.auth_type.value,
                        auth_ts_str,
                        authorization.details,
                    ),
                )
        except sqlite3.IntegrityError as err:
            raise MemoryValidationError(
                f"Memory record already exists for '{valid_cat}:{valid_key}': {err}"
            ) from err
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to insert persistent memory record: {err}"
            ) from err

        return MemoryRecord(
            memory_id=memory_id,
            scope=MemoryScope.PERSISTENT,
            category=valid_cat,
            key=valid_key,
            value=value,
            source=source,
            created_at=now,
            updated_at=now,
            authorization=authorization,
        )

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        """Converts a database row to a MemoryRecord object."""
        try:
            val = json.loads(row["value_json"])
            auth = AuthorizationRecord(
                granted=bool(row["auth_granted"]),
                auth_type=AuthorizationType(row["auth_type"]),
                granted_at=datetime.fromisoformat(row["auth_timestamp"]),
                details=row["auth_details"],
            )
            return MemoryRecord(
                memory_id=row["memory_id"],
                scope=MemoryScope.PERSISTENT,
                category=row["category"],
                key=row["memory_key"],
                value=val,
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                authorization=auth,
            )
        except Exception as err:
            raise MemoryStorageError(
                f"Corrupted record row in database: {err}"
            ) from err

    def get_exact(self, category: str, key: str) -> MemoryRecord | None:
        """Retrieves a single persistent memory record by exact category and key.

        Args:
            category: Target category name.
            key: Target memory key.

        Returns:
            Matching MemoryRecord or None.

        Raises:
            MemoryValidationError: If category or key format is invalid.
            MemoryStorageError: If database access or record parsing fails.
        """
        valid_cat = validate_category(category)
        valid_key = validate_key(key)

        try:
            cursor = self._conn.execute(
                """
                SELECT * FROM semantic_memories
                WHERE category = ? AND memory_key = ?;
                """,
                (valid_cat, valid_key),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to query DB for '{valid_cat}:{valid_key}': {err}"
            ) from err

    def list_by_category(self, category: str) -> list[MemoryRecord]:
        """Lists all persistent memory records in a category ordered by key.

        Args:
            category: Target category name.

        Returns:
            List of matching MemoryRecord objects.

        Raises:
            MemoryValidationError: If category format is invalid.
            MemoryStorageError: If database access fails.
        """
        valid_cat = validate_category(category)

        try:
            cursor = self._conn.execute(
                """
                SELECT * FROM semantic_memories
                WHERE category = ?
                ORDER BY memory_key ASC;
                """,
                (valid_cat,),
            )
            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to list records for category '{valid_cat}': {err}"
            ) from err

    def search_by_prefix(self, category: str, prefix: str) -> list[MemoryRecord]:
        """Searches persistent memory records in a category matching key prefix.

        Args:
            category: Target category name.
            prefix: Key prefix string.

        Returns:
            List of matching MemoryRecord objects ordered by key.

        Raises:
            MemoryValidationError: If category or prefix is invalid.
            MemoryStorageError: If database access fails.
        """
        valid_cat = validate_category(category)
        if not isinstance(prefix, str):
            raise MemoryValidationError(
                f"Prefix must be a string, got {type(prefix).__name__}."
            )

        try:
            cursor = self._conn.execute(
                """
                SELECT * FROM semantic_memories
                WHERE category = ? AND memory_key LIKE ?
                ORDER BY memory_key ASC;
                """,
                (valid_cat, f"{prefix}%"),
            )
            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]
        except sqlite3.Error as err:
            msg = f"Failed to search records for prefix '{prefix}': {err}"
            raise MemoryStorageError(msg) from err

    def update_persistent(
        self,
        category: str,
        key: str,
        new_value: Any,
        authorization: AuthorizationRecord,
    ) -> MemoryRecord:
        """Updates an existing persistent memory record with explicit user consent.

        Args:
            category: Categorical domain identifier.
            key: Memory key identifier.
            new_value: New JSON-serializable value payload.
            authorization: Consent authorization record.

        Returns:
            The updated MemoryRecord object.

        Raises:
            MemoryNotFoundError: If no record exists for (category, key).
            MemoryValidationError: If parameters are invalid.
            MemoryAuthorizationError: If authorization is not EXPLICIT_USER_CONSENT.
            MemoryStorageError: If database update fails.
        """
        valid_cat = validate_category(category)
        valid_key = validate_key(key)
        new_value_json = serialize_value(new_value)
        validate_authorization_for_mutation(authorization)

        existing = self.get_exact(valid_cat, valid_key)
        if existing is None:
            raise MemoryNotFoundError(
                f"Cannot update non-existent record '{valid_cat}:{valid_key}'."
            )

        now = datetime.now(UTC)
        now_str = now.isoformat()
        auth_ts_str = authorization.granted_at.isoformat()

        try:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE semantic_memories
                    SET value_json = ?, updated_at = ?, auth_granted = ?,
                        auth_type = ?, auth_timestamp = ?, auth_details = ?
                    WHERE category = ? AND memory_key = ?;
                    """,
                    (
                        new_value_json,
                        now_str,
                        1 if authorization.granted else 0,
                        authorization.auth_type.value,
                        auth_ts_str,
                        authorization.details,
                        valid_cat,
                        valid_key,
                    ),
                )
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to update persistent memory record: {err}"
            ) from err

        return MemoryRecord(
            memory_id=existing.memory_id,
            scope=MemoryScope.PERSISTENT,
            category=valid_cat,
            key=valid_key,
            value=new_value,
            source=existing.source,
            created_at=existing.created_at,
            updated_at=now,
            authorization=authorization,
        )

    def delete_persistent(
        self,
        category: str,
        key: str,
        authorization: AuthorizationRecord,
    ) -> bool:
        """Deletes an existing persistent memory record with explicit user consent.

        Args:
            category: Categorical domain identifier.
            key: Memory key identifier.
            authorization: Consent authorization record.

        Returns:
            True upon confirmed deletion.

        Raises:
            MemoryNotFoundError: If no record exists for (category, key).
            MemoryValidationError: If category or key format is invalid.
            MemoryAuthorizationError: If authorization is not EXPLICIT_USER_CONSENT.
            MemoryStorageError: If database deletion fails.
        """
        valid_cat = validate_category(category)
        valid_key = validate_key(key)
        validate_authorization_for_mutation(authorization)

        existing = self.get_exact(valid_cat, valid_key)
        if existing is None:
            raise MemoryNotFoundError(
                f"Cannot delete non-existent record '{valid_cat}:{valid_key}'."
            )

        try:
            with self._conn:
                self._conn.execute(
                    """
                    DELETE FROM semantic_memories
                    WHERE category = ? AND memory_key = ?;
                    """,
                    (valid_cat, valid_key),
                )
            return True
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to delete persistent memory record: {err}"
            ) from err

    def inspect_all(self) -> list[dict[str, Any]]:
        """Provides a local, read-only inspection view of persistent memory records.

        Returns:
            List of dictionaries exposing stored values and authorization provenance.

        Raises:
            MemoryStorageError: If database query fails.
        """
        try:
            cursor = self._conn.execute(
                """
                SELECT * FROM semantic_memories
                ORDER BY category ASC, memory_key ASC;
                """
            )
            rows = cursor.fetchall()
            results: list[dict[str, Any]] = []
            for row in rows:
                record = self._row_to_record(row)
                results.append(
                    {
                        "memory_id": record.memory_id,
                        "scope": record.scope.value,
                        "category": record.category,
                        "key": record.key,
                        "value": record.value,
                        "source": record.source,
                        "created_at": record.created_at.isoformat(),
                        "updated_at": record.updated_at.isoformat(),
                        "authorization": {
                            "granted": record.authorization.granted,
                            "auth_type": record.authorization.auth_type.value,
                            "granted_at": record.authorization.granted_at.isoformat(),
                            "details": record.authorization.details,
                        },
                    }
                )
            return results
        except sqlite3.Error as err:
            raise MemoryStorageError(
                f"Failed to inspect persistent memory database: {err}"
            ) from err

    def export_to_dict(self) -> dict[str, Any]:
        """Generates a structured export dictionary of persistent semantic memory.

        Excludes Session Memory. Read-only operation.

        Returns:
            Dictionary containing export metadata and all persistent records.
        """
        records_data = self.inspect_all()
        return {
            "export_metadata": {
                "version": SCHEMA_VERSION,
                "exported_at": datetime.now(UTC).isoformat(),
                "total_records": len(records_data),
            },
            "records": records_data,
        }

    def close(self) -> None:
        """Cleanly closes the underlying SQLite database connection."""
        if hasattr(self, "_conn") and self._conn:
            try:
                self._conn.close()
            except Exception:
                pass

    def __enter__(self) -> "SQLiteStore":
        """Context manager entry returning self instance."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit closing database connection."""
        self.close()


# Alias for spec architectural compatibility
PersistentStore = SQLiteStore
