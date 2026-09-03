"""Unit tests for the ARGOS Memory subsystem (ADS-006 Milestones 1–6).

Tests domain entities, DTO slots, enumerations, constants, exception hierarchy,
session ID validation, SessionStore FIFO turn tracking, PersistentStore / SQLite,
ConsentManager authorization validation, MemoryEngine, and MemoryCapability.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import argos.memory as memory_pkg
from argos.memory.consent_manager import ConsentManager
from argos.memory.constants import (
    CATEGORY_PATTERN,
    DEFAULT_DB_PATH,
    DEFAULT_MAX_SESSION_TURNS,
    DEFAULT_SESSION_ID,
    DEFAULT_TIMEOUT_SECONDS,
    KEY_PATTERN,
    MAX_CATEGORY_LENGTH,
    MAX_KEY_LENGTH,
    MAX_VALUE_BYTES,
    SCHEMA_VERSION,
)
from argos.memory.exceptions import (
    MemoryAuthorizationError,
    MemoryError,
    MemoryNotFoundError,
    MemoryStorageError,
    MemoryValidationError,
)
from argos.memory.memory_capability import CAPABILITY_MEMORY, MemoryCapability
from argos.memory.memory_engine import MemoryEngine
from argos.memory.models import (
    AuthorizationRecord,
    AuthorizationType,
    MemoryRecord,
    MemoryScope,
    MemorySearchResult,
    SessionTurn,
)
from argos.memory.session_store import SessionStore, validate_session_id
from argos.memory.sqlite_store import (
    PersistentStore,
    SQLiteStore,
    serialize_value,
    validate_authorization_for_mutation,
    validate_category,
    validate_key,
)

# =====================================================================
# Constants and Capacity Limits Tests
# =====================================================================


def test_session_constants() -> None:
    """Verifies default capacity limits and identifiers for session memory."""
    assert DEFAULT_MAX_SESSION_TURNS == 50
    assert DEFAULT_SESSION_ID == "default"


def test_semantic_limits() -> None:
    """Verifies key lengths, category lengths, and payload size ceilings."""
    assert MAX_KEY_LENGTH == 128
    assert MAX_CATEGORY_LENGTH == 64
    assert MAX_VALUE_BYTES == 65536


def test_regex_patterns() -> None:
    """Verifies key and category regex validation patterns."""
    assert KEY_PATTERN == r"^[a-zA-Z0-9_.-]+$"
    assert CATEGORY_PATTERN == r"^[a-zA-Z0-9_.-]+$"


def test_storage_defaults() -> None:
    """Verifies default database file path, timeout, and schema version."""
    assert DEFAULT_TIMEOUT_SECONDS == 5.0
    assert SCHEMA_VERSION == 1
    assert isinstance(DEFAULT_DB_PATH, Path)
    assert DEFAULT_DB_PATH.name == "memory.db"


# =====================================================================
# Exception Hierarchy Tests
# =====================================================================


def test_base_exception() -> None:
    """Verifies that MemoryError is an Exception with string representation."""
    err = MemoryError("base error")
    assert isinstance(err, Exception)
    assert str(err) == "base error"


def test_subclass_inheritance() -> None:
    """Verifies that domain memory exceptions inherit from MemoryError."""
    validation_err = MemoryValidationError("invalid key")
    storage_err = MemoryStorageError("disk error")
    auth_err = MemoryAuthorizationError("consent missing")
    not_found_err = MemoryNotFoundError("record missing")

    assert isinstance(validation_err, MemoryError)
    assert isinstance(storage_err, MemoryError)
    assert isinstance(auth_err, MemoryError)
    assert isinstance(not_found_err, MemoryError)


def test_decoupling_from_brain_exceptions() -> None:
    """Confirms that Memory exceptions do not inherit from BrainError."""
    from argos.brain.exceptions import BrainError

    assert not issubclass(MemoryError, BrainError)
    assert not issubclass(MemoryValidationError, BrainError)
    assert not issubclass(MemoryStorageError, BrainError)
    assert not issubclass(MemoryAuthorizationError, BrainError)
    assert not issubclass(MemoryNotFoundError, BrainError)


# =====================================================================
# Models and DTOs Tests
# =====================================================================


def test_memory_scope_enum() -> None:
    """Verifies members and string representations of MemoryScope."""
    assert MemoryScope.SESSION == "session"
    assert MemoryScope.PERSISTENT == "persistent"
    assert len(MemoryScope) == 2


def test_authorization_type_enum() -> None:
    """Verifies members and string representations of AuthorizationType."""
    assert AuthorizationType.EXPLICIT_USER_CONSENT == "explicit_user_consent"
    assert AuthorizationType.PRE_AUTHORIZED_POLICY == "pre_authorized_policy"
    assert AuthorizationType.SYSTEM_DEFAULT == "system_default"
    assert len(AuthorizationType) == 3


def test_authorization_record_creation_and_slots() -> None:
    """Verifies AuthorizationRecord instantiation and slots restriction."""
    now = datetime.now(UTC)
    record = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at=now,
        details="User approved via prompt",
    )
    assert record.granted is True
    assert record.auth_type == AuthorizationType.EXPLICIT_USER_CONSENT
    assert record.granted_at == now
    assert record.details == "User approved via prompt"

    with pytest.raises(AttributeError):
        record.arbitrary_field = "invalid"  # type: ignore[attr-defined]


def test_authorization_record_default_details() -> None:
    """Verifies that details defaults to None in AuthorizationRecord."""
    now = datetime.now(UTC)
    record = AuthorizationRecord(
        granted=False,
        auth_type=AuthorizationType.SYSTEM_DEFAULT,
        granted_at=now,
    )
    assert record.details is None


def test_memory_record_creation_and_slots() -> None:
    """Verifies MemoryRecord creation, fields, and slots enforcement."""
    now = datetime.now(UTC)
    auth = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at=now,
    )
    record = MemoryRecord(
        memory_id="mem-001",
        scope=MemoryScope.PERSISTENT,
        category="preference",
        key="editor.default",
        value="vscode",
        source="user_explicit",
        created_at=now,
        updated_at=now,
        authorization=auth,
    )
    assert record.memory_id == "mem-001"
    assert record.scope == MemoryScope.PERSISTENT
    assert record.category == "preference"
    assert record.key == "editor.default"
    assert record.value == "vscode"
    assert record.source == "user_explicit"
    assert record.created_at == now
    assert record.updated_at == now
    assert record.authorization == auth

    with pytest.raises(AttributeError):
        record.new_attr = "invalid"  # type: ignore[attr-defined]


def test_session_turn_creation_and_slots() -> None:
    """Verifies SessionTurn creation, fields, and slots enforcement."""
    now = datetime.now(UTC)
    turn = SessionTurn(
        turn_id=1,
        session_id="default",
        user_input="set editor to code",
        normalized_text="set editor to code",
        intent_name="system_config",
        plan_summary="Configure default editor",
        execution_status="SUCCESS",
        timestamp=now,
        metadata={"source": "cli"},
    )
    assert turn.turn_id == 1
    assert turn.session_id == "default"
    assert turn.user_input == "set editor to code"
    assert turn.normalized_text == "set editor to code"
    assert turn.intent_name == "system_config"
    assert turn.plan_summary == "Configure default editor"
    assert turn.execution_status == "SUCCESS"
    assert turn.timestamp == now
    assert turn.metadata == {"source": "cli"}

    with pytest.raises(AttributeError):
        turn.extra = 123  # type: ignore[attr-defined]


def test_session_turn_default_metadata() -> None:
    """Verifies that metadata defaults to an empty dict in SessionTurn."""
    now = datetime.now(UTC)
    turn = SessionTurn(
        turn_id=2,
        session_id="session-xyz",
        user_input="hello",
        normalized_text="hello",
        intent_name=None,
        plan_summary=None,
        execution_status=None,
        timestamp=now,
    )
    assert turn.metadata == {}


def test_memory_search_result_creation_and_slots() -> None:
    """Verifies MemorySearchResult fields, defaults, and slots restriction."""
    result = MemorySearchResult(query="editor")
    assert result.query == "editor"
    assert result.records == []
    assert result.total_count == 0

    with pytest.raises(AttributeError):
        result.extra = "disallowed"  # type: ignore[attr-defined]


# =====================================================================
# Session ID Validation Tests
# =====================================================================


def test_validate_session_id_valid() -> None:
    """Verifies acceptance of valid session ID formats."""
    assert validate_session_id("default") == "default"
    assert validate_session_id("session-123") == "session-123"
    assert validate_session_id("user_session_abc") == "user_session_abc"
    assert validate_session_id("A-B_1") == "A-B_1"


def test_validate_session_id_invalid_type() -> None:
    """Verifies rejection of non-string session ID values."""
    with pytest.raises(MemoryValidationError, match="must be a string"):
        validate_session_id(123)  # type: ignore[arg-type]

    with pytest.raises(MemoryValidationError, match="must be a string"):
        validate_session_id(None)  # type: ignore[arg-type]


def test_validate_session_id_empty_or_whitespace() -> None:
    """Verifies rejection of empty strings and leading/trailing whitespace."""
    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_session_id("")

    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_session_id(" default")

    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_session_id("default ")

    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_session_id("   ")


def test_validate_session_id_disallowed_characters() -> None:
    """Verifies rejection of session IDs containing disallowed characters."""
    invalid_ids = ["session@1", "session 1", "session!", "session/1", "session.key"]
    for inv_id in invalid_ids:
        with pytest.raises(MemoryValidationError, match="Invalid Session ID"):
            validate_session_id(inv_id)


# =====================================================================
# SessionStore Unit Tests (Milestone 2)
# =====================================================================


def _make_turn(
    turn_id: int,
    session_id: str = "default",
    text: str = "test",
) -> SessionTurn:
    """Helper to construct SessionTurn instances for testing."""
    return SessionTurn(
        turn_id=turn_id,
        session_id=session_id,
        user_input=text,
        normalized_text=text.lower(),
        intent_name="test_intent",
        plan_summary="test_plan",
        execution_status="SUCCESS",
        timestamp=datetime.now(UTC),
    )


def test_session_store_creation() -> None:
    """Verifies default and custom capacity initialization for SessionStore."""
    store_default = SessionStore()
    assert store_default.max_turns == 50

    store_custom = SessionStore(max_turns=10)
    assert store_custom.max_turns == 10


def test_session_store_invalid_max_turns() -> None:
    """Verifies rejection of non-positive integer values for max_turns."""
    invalid_values = [0, -5, "50", False, None]
    for val in invalid_values:
        with pytest.raises(MemoryValidationError, match="positive integer"):
            SessionStore(max_turns=val)  # type: ignore[arg-type]


def test_record_turn_and_retrieval() -> None:
    """Verifies recording turns and retrieving them from SessionStore."""
    store = SessionStore()
    turn1 = _make_turn(1, "default", "first turn")
    recorded = store.record_turn(turn1)
    assert recorded == turn1

    turns = store.get_session_turns("default")
    assert len(turns) == 1
    assert turns[0] == turn1
    assert store.get_turn_count("default") == 1


def test_record_turn_invalid_object() -> None:
    """Verifies that record_turn rejects non-SessionTurn instances."""
    store = SessionStore()
    with pytest.raises(MemoryValidationError, match="Expected SessionTurn instance"):
        store.record_turn({"turn_id": 1})  # type: ignore[arg-type]


def test_record_turn_invalid_session_id() -> None:
    """Verifies that record_turn rejects turns with invalid session IDs."""
    store = SessionStore()
    invalid_turn = _make_turn(1, "invalid session id!")
    with pytest.raises(MemoryValidationError, match="Invalid Session ID"):
        store.record_turn(invalid_turn)


def test_recent_n_retrieval_and_ordering() -> None:
    """Verifies that get_session_turns returns recent N turns chronologically."""
    store = SessionStore()
    for i in range(1, 6):
        store.record_turn(_make_turn(i, "default", f"turn-{i}"))

    recent_3 = store.get_session_turns("default", limit=3)
    assert len(recent_3) == 3
    assert [t.turn_id for t in recent_3] == [3, 4, 5]

    all_turns = store.get_session_turns("default", limit=10)
    assert len(all_turns) == 5
    assert [t.turn_id for t in all_turns] == [1, 2, 3, 4, 5]


def test_get_session_turns_invalid_params() -> None:
    """Verifies validation of session_id and limit in get_session_turns."""
    store = SessionStore()

    with pytest.raises(MemoryValidationError, match="Invalid Session ID"):
        store.get_session_turns("invalid ID!")

    invalid_limits = [0, -1, "10", True, None]
    for lim in invalid_limits:
        msg = "Limit must be a positive integer"
        with pytest.raises(MemoryValidationError, match=msg):
            store.get_session_turns("default", limit=lim)  # type: ignore[arg-type]


def test_get_session_turns_does_not_mutate_state() -> None:
    """Verifies that reading from SessionStore does not alter internal state."""
    store = SessionStore()
    store.record_turn(_make_turn(1))
    store.record_turn(_make_turn(2))

    res1 = store.get_session_turns("default", limit=2)
    res2 = store.get_session_turns("default", limit=2)
    assert res1 == res2
    assert store.get_turn_count("default") == 2


def test_fifo_eviction_at_capacity_limit() -> None:
    """Verifies deterministic FIFO eviction when turn count exceeds 50."""
    store = SessionStore(max_turns=50)
    for i in range(1, 52):
        store.record_turn(_make_turn(i, "default", f"turn-{i}"))

    assert store.get_turn_count("default") == 50
    turns = store.get_session_turns("default", limit=50)

    assert turns[0].turn_id == 2
    assert turns[-1].turn_id == 51
    assert [t.turn_id for t in turns] == list(range(2, 52))


def test_fifo_eviction_custom_capacity() -> None:
    """Verifies deterministic FIFO eviction for custom max_turns capacity."""
    store = SessionStore(max_turns=3)
    for i in range(1, 6):
        store.record_turn(_make_turn(i, "default", f"turn-{i}"))

    assert store.get_turn_count("default") == 3
    turns = store.get_session_turns("default", limit=10)
    assert [t.turn_id for t in turns] == [3, 4, 5]


def test_session_isolation() -> None:
    """Verifies that different session IDs maintain isolated turn histories."""
    store = SessionStore()
    store.record_turn(_make_turn(10, "session-a", "msg a"))
    store.record_turn(_make_turn(20, "session-b", "msg b"))

    turns_a = store.get_session_turns("session-a")
    turns_b = store.get_session_turns("session-b")

    assert len(turns_a) == 1
    assert turns_a[0].turn_id == 10
    assert len(turns_b) == 1
    assert turns_b[0].turn_id == 20

    assert store.clear_session("session-a") is True
    assert store.get_turn_count("session-a") == 0
    assert store.get_turn_count("session-b") == 1


def test_clear_session_semantics() -> None:
    """Verifies clearing existing and non-existing/empty sessions."""
    store = SessionStore()
    store.record_turn(_make_turn(1, "session-1"))

    assert store.clear_session("session-1") is True
    assert store.get_turn_count("session-1") == 0
    assert store.clear_session("session-1") is False
    assert store.clear_session("unknown-session") is False


def test_empty_session_retrieval() -> None:
    """Verifies retrieval behavior for empty or non-existent sessions."""
    store = SessionStore()
    assert store.get_session_turns("nonexistent") == []
    assert store.get_turn_count("nonexistent") == 0


def test_validate_session_id_in_get_turn_count_and_clear_session() -> None:
    """Verifies session ID validation in get_turn_count and clear_session."""
    store = SessionStore()
    with pytest.raises(MemoryValidationError, match="Invalid Session ID"):
        store.get_turn_count("bad id!")

    with pytest.raises(MemoryValidationError, match="Invalid Session ID"):
        store.clear_session("bad id!")


# =====================================================================
# SQLiteStore / PersistentStore Helpers & Store Tests (Milestone 3)
# =====================================================================


def _make_auth(
    granted: bool = True,
    auth_type: AuthorizationType = AuthorizationType.EXPLICIT_USER_CONSENT,
) -> AuthorizationRecord:
    """Helper to construct AuthorizationRecord instances for testing."""
    return AuthorizationRecord(
        granted=granted,
        auth_type=auth_type,
        granted_at=datetime.now(UTC),
        details="User approved in test",
    )


def test_validate_category_valid_and_invalid() -> None:
    """Verifies category string validation rules and limits."""
    assert validate_category("preference") == "preference"
    assert validate_category("user_fact.sub") == "user_fact.sub"

    with pytest.raises(MemoryValidationError, match="must be a string"):
        validate_category(123)  # type: ignore[arg-type]

    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_category("")

    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_category(" preference")

    msg = "exceeds limit"
    with pytest.raises(MemoryValidationError, match=msg):
        validate_category("a" * (MAX_CATEGORY_LENGTH + 1))

    with pytest.raises(MemoryValidationError, match="Must match pattern"):
        validate_category("cat@name")


def test_validate_key_valid_and_invalid() -> None:
    """Verifies memory key string validation rules and limits."""
    assert validate_key("editor.default") == "editor.default"
    assert validate_key("key-123_test") == "key-123_test"

    with pytest.raises(MemoryValidationError, match="must be a string"):
        validate_key(None)  # type: ignore[arg-type]

    with pytest.raises(MemoryValidationError, match="non-empty string"):
        validate_key("   ")

    msg = "exceeds limit"
    with pytest.raises(MemoryValidationError, match=msg):
        validate_key("k" * (MAX_KEY_LENGTH + 1))

    with pytest.raises(MemoryValidationError, match="Must match pattern"):
        validate_key("key name!")


def test_serialize_value_types_and_size() -> None:
    """Verifies JSON serialization rules, supported types, and payload size bounds."""
    assert serialize_value({"a": 1, "b": "str"}) == '{"a": 1, "b": "str"}'
    assert serialize_value(["item", 123, True, None]) == '["item", 123, true, null]'
    assert serialize_value("plain_text") == '"plain_text"'
    assert serialize_value(100) == "100"
    assert serialize_value(3.14) == "3.14"

    with pytest.raises(MemoryValidationError, match="not valid JSON-serializable"):
        serialize_value(lambda x: x)

    large_val = "x" * (MAX_VALUE_BYTES + 1)
    with pytest.raises(MemoryValidationError, match="exceeds limit"):
        serialize_value(large_val)


def test_validate_authorization_for_mutation() -> None:
    """Verifies authorization enforcement rules for persistent mutations in V1."""
    valid_auth = _make_auth(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
    )
    validate_authorization_for_mutation(valid_auth)

    denied_auth = _make_auth(granted=False)
    with pytest.raises(MemoryAuthorizationError, match="granted is False"):
        validate_authorization_for_mutation(denied_auth)

    policy_auth = _make_auth(
        granted=True,
        auth_type=AuthorizationType.PRE_AUTHORIZED_POLICY,
    )
    msg = "requires EXPLICIT_USER_CONSENT"
    with pytest.raises(MemoryAuthorizationError, match=msg):
        validate_authorization_for_mutation(policy_auth)

    default_auth = _make_auth(
        granted=True,
        auth_type=AuthorizationType.SYSTEM_DEFAULT,
    )
    with pytest.raises(MemoryAuthorizationError, match=msg):
        validate_authorization_for_mutation(default_auth)

    with pytest.raises(MemoryAuthorizationError, match="Expected AuthorizationRecord"):
        validate_authorization_for_mutation("granted")  # type: ignore[arg-type]


def test_sqlite_store_creation_and_isolation(tmp_path: Path) -> None:
    """Verifies SQLiteStore creation in memory and on local disk with isolated files."""
    store_mem = SQLiteStore(":memory:")
    assert store_mem.db_path == ":memory:"
    store_mem.close()

    db_file = tmp_path / "sub_dir" / "test_memory.db"
    store_file = SQLiteStore(db_file)
    assert store_file.db_path == str(db_file)
    assert db_file.exists()
    store_file.close()


def test_sqlite_store_default_db_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies SQLiteStore initialization when db_path is None."""
    default_file = tmp_path / "default_argos" / "memory.db"
    monkeypatch.setattr(
        "argos.memory.sqlite_store.DEFAULT_DB_PATH",
        default_file,
    )
    with SQLiteStore() as store:
        assert store.db_path == str(default_file)
        assert default_file.exists()


def test_sqlite_store_mkdir_failure(tmp_path: Path) -> None:
    """Verifies directory creation failure raises MemoryStorageError."""
    file_as_dir = tmp_path / "file_blocking_dir"
    file_as_dir.write_text("blocking file")

    msg = "Failed to create directory"
    with pytest.raises(MemoryStorageError, match=msg):
        SQLiteStore(file_as_dir / "db.db")


def test_sqlite_store_init_db_error_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies schema initialization failure raises MemoryStorageError."""

    def mock_connect(*args: Any, **kwargs: Any) -> Any:
        class DummyConn:
            def __enter__(self) -> "DummyConn":
                raise sqlite3.Error("Mocked connect init failure")

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

            def execute(self, *args: Any, **kwargs: Any) -> Any:
                pass

        return DummyConn()

    monkeypatch.setattr(sqlite3, "connect", mock_connect)
    msg = "Database schema initialization failed"
    with pytest.raises(MemoryStorageError, match=msg):
        SQLiteStore(":memory:")


def test_sqlite_store_invalid_parameters() -> None:
    """Verifies validation of timeout and db_path parameters."""
    msg_timeout = "Timeout must be a positive number"
    with pytest.raises(MemoryValidationError, match=msg_timeout):
        SQLiteStore(":memory:", timeout=0)

    with pytest.raises(MemoryValidationError, match=msg_timeout):
        SQLiteStore(":memory:", timeout=-1.0)

    msg_path = "db_path must be a string, Path, or None"
    with pytest.raises(MemoryValidationError, match=msg_path):
        SQLiteStore(12345)  # type: ignore[arg-type]


def test_schema_initialization_and_version(tmp_path: Path) -> None:
    """Verifies idempotent schema creation and schema_migrations table versioning."""
    db_file = tmp_path / "schema_test.db"

    with SQLiteStore(db_file) as store:
        assert store.db_path == str(db_file)

    with SQLiteStore(db_file) as store:
        cursor = store._conn.execute("SELECT version FROM schema_migrations;")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["version"] == SCHEMA_VERSION


def test_store_persistent_record_and_get_exact() -> None:
    """Verifies storing a persistent record and exact retrieval."""
    auth = _make_auth(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
    )
    with SQLiteStore(":memory:") as store:
        rec = store.store_persistent(
            category="preference",
            key="editor.default",
            value="vscode",
            authorization=auth,
            source="user_explicit",
        )
        assert rec.memory_id == "preference:editor.default"
        assert rec.category == "preference"
        assert rec.key == "editor.default"
        assert rec.value == "vscode"
        assert rec.scope == MemoryScope.PERSISTENT

        retrieved = store.get_exact("preference", "editor.default")
        assert retrieved is not None
        assert retrieved.memory_id == rec.memory_id
        assert retrieved.value == "vscode"
        assert retrieved.authorization.granted is True
        assert retrieved.authorization.auth_type == (
            AuthorizationType.EXPLICIT_USER_CONSENT
        )


def test_store_persistent_invalid_source() -> None:
    """Verifies rejection of empty or non-string source metadata."""
    auth = _make_auth()
    msg = "Source must be a non-empty string"
    with SQLiteStore(":memory:") as store:
        with pytest.raises(MemoryValidationError, match=msg):
            store.store_persistent("pref", "k1", "v", auth, source="")


def test_store_persistent_duplicate_detection() -> None:
    """Verifies inserting a duplicate key raises MemoryValidationError."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        store.store_persistent("pref", "editor", "code", auth)
        with pytest.raises(MemoryValidationError, match="already exists"):
            store.store_persistent("pref", "editor", "vim", auth)


def test_get_exact_nonexistent() -> None:
    """Verifies that get_exact returns None for non-existent records."""
    with SQLiteStore(":memory:") as store:
        assert store.get_exact("pref", "nonexistent") is None


def test_list_by_category_and_search_by_prefix() -> None:
    """Verifies category listing and prefix search with deterministic key order."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        store.store_persistent("pref", "editor.font", "Fira Code", auth)
        store.store_persistent("pref", "editor.theme", "Dark+", auth)
        store.store_persistent("pref", "terminal.shell", "powershell", auth)
        store.store_persistent("system", "os", "windows", auth)

        prefs = store.list_by_category("pref")
        assert len(prefs) == 3
        expected_keys = ["editor.font", "editor.theme", "terminal.shell"]
        assert [r.key for r in prefs] == expected_keys

        editor_prefs = store.search_by_prefix("pref", "editor.")
        assert len(editor_prefs) == 2
        assert [r.key for r in editor_prefs] == ["editor.font", "editor.theme"]

        empty_prefix = store.search_by_prefix("pref", "nonexistent")
        assert empty_prefix == []


def test_search_by_prefix_invalid_prefix() -> None:
    """Verifies rejection of non-string prefix parameter."""
    with SQLiteStore(":memory:") as store:
        with pytest.raises(MemoryValidationError, match="Prefix must be a string"):
            store.search_by_prefix("pref", 123)  # type: ignore[arg-type]


def test_update_persistent_record() -> None:
    """Verifies updating an existing persistent record atomically."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        rec1 = store.store_persistent("pref", "theme", "light", auth)

        updated_auth = AuthorizationRecord(
            granted=True,
            auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
            granted_at=datetime.now(UTC),
            details="User updated theme preference",
        )
        rec2 = store.update_persistent("pref", "theme", "dark", updated_auth)

        assert rec2.memory_id == rec1.memory_id
        assert rec2.value == "dark"
        assert rec2.updated_at >= rec1.updated_at
        assert rec2.authorization.details == "User updated theme preference"

        retrieved = store.get_exact("pref", "theme")
        assert retrieved is not None
        assert retrieved.value == "dark"


def test_update_persistent_nonexistent() -> None:
    """Verifies that updating a non-existent record raises MemoryNotFoundError."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        msg = "Cannot update non-existent record"
        with pytest.raises(MemoryNotFoundError, match=msg):
            store.update_persistent("pref", "missing", "val", auth)


def test_delete_persistent_record() -> None:
    """Verifies deleting an existing persistent record atomically."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        store.store_persistent("pref", "temp_key", "temp_val", auth)
        assert store.get_exact("pref", "temp_key") is not None

        res = store.delete_persistent("pref", "temp_key", auth)
        assert res is True
        assert store.get_exact("pref", "temp_key") is None


def test_delete_persistent_nonexistent() -> None:
    """Verifies that deleting a non-existent record raises MemoryNotFoundError."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        msg = "Cannot delete non-existent record"
        with pytest.raises(MemoryNotFoundError, match=msg):
            store.delete_persistent("pref", "missing", auth)


def test_inspect_all_and_export_to_dict() -> None:
    """Verifies read-only inspection and dict export of persistent memories."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        store.store_persistent("pref", "key_a", "val_a", auth)
        store.store_persistent("fact", "key_b", "val_b", auth)

        inspection = store.inspect_all()
        assert len(inspection) == 2
        assert inspection[0]["key"] == "key_b"
        assert inspection[1]["key"] == "key_a"

        export_data = store.export_to_dict()
        assert "export_metadata" in export_data
        assert export_data["export_metadata"]["version"] == SCHEMA_VERSION
        assert export_data["export_metadata"]["total_records"] == 2
        assert len(export_data["records"]) == 2


def test_persistence_across_reopen(tmp_path: Path) -> None:
    """Verifies data persistence when database connection is closed and reopened."""
    db_file = tmp_path / "persistent_reopen.db"
    auth = _make_auth()

    with SQLiteStore(db_file) as store1:
        store1.store_persistent("user_fact", "city", "Tokyo", auth)

    with SQLiteStore(db_file) as store2:
        rec = store2.get_exact("user_fact", "city")
        assert rec is not None
        assert rec.value == "Tokyo"


def test_storage_error_wrapping_on_corrupt_db(tmp_path: Path) -> None:
    """Verifies wrapping of database errors into MemoryStorageError upon corruption."""
    corrupt_file = tmp_path / "corrupt.db"
    corrupt_file.write_bytes(b"This is not a valid SQLite database header string.")

    msg = "Failed to connect|Database schema|Corrupted"
    with pytest.raises(MemoryStorageError, match=msg):
        SQLiteStore(corrupt_file)


def test_corrupt_row_parsing_in_row_to_record() -> None:
    """Verifies that corrupted JSON row values raise MemoryStorageError."""
    with SQLiteStore(":memory:") as store:
        now_str = datetime.now(UTC).isoformat()
        store._conn.execute(
            """
            INSERT INTO semantic_memories (
                memory_id, category, memory_key, value_json, source,
                created_at, updated_at, auth_granted, auth_type,
                auth_timestamp, auth_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "pref:bad",
                "pref",
                "bad",
                "NOT_VALID_JSON",
                "source",
                now_str,
                now_str,
                1,
                "explicit_user_consent",
                now_str,
                None,
            ),
        )
        with pytest.raises(MemoryStorageError, match="Corrupted record row"):
            store.get_exact("pref", "bad")


def test_closed_connection_error_handling() -> None:
    """Verifies that operations on a closed DB connection raise MemoryStorageError."""
    auth = _make_auth()
    store = SQLiteStore(":memory:")

    # Force close connection
    store.close()

    with pytest.raises(MemoryStorageError, match="Failed to insert"):
        store.store_persistent("pref", "k2", "v2", auth)

    with pytest.raises(MemoryStorageError, match="Failed to query DB"):
        store.get_exact("pref", "k1")

    with pytest.raises(MemoryStorageError, match="Failed to list records"):
        store.list_by_category("pref")

    with pytest.raises(MemoryStorageError, match="Failed to search records"):
        store.search_by_prefix("pref", "k")

    with pytest.raises(MemoryStorageError, match="Failed to query DB"):
        store.update_persistent("pref", "k1", "v2", auth)

    with pytest.raises(MemoryStorageError, match="Failed to query DB"):
        store.delete_persistent("pref", "k1", auth)

    with pytest.raises(MemoryStorageError, match="Failed to inspect"):
        store.inspect_all()


def test_update_and_delete_storage_error_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies wrapping of sqlite3 errors during update and delete operations."""
    auth = _make_auth()
    with SQLiteStore(":memory:") as store:
        existing_rec = store.store_persistent("pref", "k1", "v1", auth)

        class DummyFailingConn:
            def execute(self, *args: Any, **kwargs: Any) -> Any:
                raise sqlite3.OperationalError("Mocked database write error")

            def __enter__(self) -> "DummyFailingConn":
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        monkeypatch.setattr(store, "get_exact", lambda c, k: existing_rec)
        store._conn = DummyFailingConn()  # type: ignore[assignment]

        with pytest.raises(MemoryStorageError, match="Failed to update"):
            store.update_persistent("pref", "k1", "v2", auth)

        with pytest.raises(MemoryStorageError, match="Failed to delete"):
            store.delete_persistent("pref", "k1", auth)


def test_persistent_store_alias() -> None:
    """Verifies that PersistentStore is an alias for SQLiteStore."""
    assert PersistentStore is SQLiteStore


# =====================================================================
# ConsentManager Unit Tests (Milestone 4)
# =====================================================================


def test_grant_explicit_consent() -> None:
    """Verifies creating explicit user consent authorization records."""
    mgr = ConsentManager()
    record = mgr.grant_explicit_consent(details="Confirmed by user at turn 1")

    assert record.granted is True
    assert record.auth_type == AuthorizationType.EXPLICIT_USER_CONSENT
    assert isinstance(record.granted_at, datetime)
    assert record.granted_at.tzinfo == UTC
    assert record.details == "Confirmed by user at turn 1"

    default_rec = mgr.grant_explicit_consent()
    assert default_rec.granted is True
    assert default_rec.details is None


def test_grant_explicit_consent_invalid_details() -> None:
    """Verifies rejection of non-string details parameter in grant_explicit_consent."""
    mgr = ConsentManager()
    with pytest.raises(MemoryAuthorizationError, match="details must be a string"):
        mgr.grant_explicit_consent(details=12345)  # type: ignore[arg-type]


def test_deny_consent() -> None:
    """Verifies creating explicit consent denial authorization records."""
    mgr = ConsentManager()
    record = mgr.deny_consent(details="User declined persistent store")

    assert record.granted is False
    assert record.auth_type == AuthorizationType.EXPLICIT_USER_CONSENT
    assert isinstance(record.granted_at, datetime)
    assert record.granted_at.tzinfo == UTC
    assert record.details == "User declined persistent store"


def test_deny_consent_invalid_details() -> None:
    """Verifies rejection of non-string details parameter in deny_consent."""
    mgr = ConsentManager()
    with pytest.raises(MemoryAuthorizationError, match="details must be a string"):
        mgr.deny_consent(details={"key": "val"})  # type: ignore[arg-type]


def test_validate_authorization_granted_explicit() -> None:
    """Verifies validation and acceptance of granted explicit user consent."""
    mgr = ConsentManager()
    auth = mgr.grant_explicit_consent(details="User confirmed")

    mgr.validate_authorization(auth)
    assert mgr.is_authorized(auth) is True


def test_validate_authorization_denied_explicit() -> None:
    """Verifies rejection of denied consent records."""
    mgr = ConsentManager()
    auth = mgr.deny_consent(details="User refused")

    msg = "authorization.granted is False"
    with pytest.raises(MemoryAuthorizationError, match=msg):
        mgr.validate_authorization(auth)

    assert mgr.is_authorized(auth) is False


def test_validate_authorization_policy_and_system_default_rejection() -> None:
    """Verifies rejection of PRE_AUTHORIZED_POLICY and SYSTEM_DEFAULT in V1."""
    mgr = ConsentManager()
    now = datetime.now(UTC)

    policy_auth = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.PRE_AUTHORIZED_POLICY,
        granted_at=now,
    )
    msg = "requires EXPLICIT_USER_CONSENT"
    with pytest.raises(MemoryAuthorizationError, match=msg):
        mgr.validate_authorization(policy_auth)
    assert mgr.is_authorized(policy_auth) is False

    system_auth = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.SYSTEM_DEFAULT,
        granted_at=now,
    )
    with pytest.raises(MemoryAuthorizationError, match=msg):
        mgr.validate_authorization(system_auth)
    assert mgr.is_authorized(system_auth) is False


def test_validate_authorization_malformed_inputs() -> None:
    """Verifies validation and error handling for malformed authorization objects."""
    mgr = ConsentManager()
    now = datetime.now(UTC)

    msg_type = "Expected AuthorizationRecord instance"
    with pytest.raises(MemoryAuthorizationError, match=msg_type):
        mgr.validate_authorization("invalid_type")  # type: ignore[arg-type]
    assert mgr.is_authorized("invalid_type") is False  # type: ignore[arg-type]

    auth_bad_granted = AuthorizationRecord(
        granted="True",  # type: ignore[arg-type]
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at=now,
    )
    msg_granted = "authorization.granted is False"
    with pytest.raises(MemoryAuthorizationError, match=msg_granted):
        mgr.validate_authorization(auth_bad_granted)
    assert mgr.is_authorized(auth_bad_granted) is False

    auth_bad_time = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at="2026-07-03T12:00:00Z",  # type: ignore[arg-type]
    )
    msg_time = "granted_at must be a datetime"
    with pytest.raises(MemoryAuthorizationError, match=msg_time):
        mgr.validate_authorization(auth_bad_time)
    assert mgr.is_authorized(auth_bad_time) is False

    auth_bad_details = AuthorizationRecord(
        granted=True,
        auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
        granted_at=now,
        details=9999,  # type: ignore[arg-type]
    )
    msg_details = "details must be a string or None"
    with pytest.raises(MemoryAuthorizationError, match=msg_details):
        mgr.validate_authorization(auth_bad_details)
    assert mgr.is_authorized(auth_bad_details) is False


def test_consent_manager_no_storage_or_brain_dependencies() -> None:
    """Verifies that ConsentManager has no database connection or storage attributes."""
    mgr = ConsentManager()
    assert not hasattr(mgr, "_conn")
    assert not hasattr(mgr, "db_path")
    assert not hasattr(mgr, "brain")


# =====================================================================
# MemoryEngine Unit Tests (Milestone 5)
# =====================================================================


def test_memory_engine_default_instantiation() -> None:
    """Verifies default initialization of MemoryEngine with transient store."""
    with MemoryEngine(db_path=":memory:") as engine:
        assert isinstance(engine.session_store, SessionStore)
        assert isinstance(engine.persistent_store, SQLiteStore)
        assert isinstance(engine.consent_manager, ConsentManager)


def test_memory_engine_dependency_injection() -> None:
    """Verifies custom dependency injection in MemoryEngine."""
    custom_session = SessionStore(max_turns=5)
    custom_persistent = SQLiteStore(":memory:")
    custom_consent = ConsentManager()

    with MemoryEngine(
        session_store=custom_session,
        persistent_store=custom_persistent,
        consent_manager=custom_consent,
    ) as engine:
        assert engine.session_store is custom_session
        assert engine.persistent_store is custom_persistent
        assert engine.consent_manager is custom_consent


def test_memory_engine_session_operations() -> None:
    """Verifies session turn recording and retrieval via MemoryEngine."""
    with MemoryEngine(db_path=":memory:") as engine:
        turn1 = _make_turn(1, "s1", "turn 1")
        turn2 = _make_turn(2, "s1", "turn 2")

        engine.record_turn(turn1)
        engine.record_turn(turn2)

        assert engine.get_turn_count("s1") == 2
        turns = engine.get_session_turns("s1", limit=10)
        assert len(turns) == 2
        assert turns[0] == turn1
        assert turns[1] == turn2

        # Session isolation check
        assert engine.get_turn_count("s2") == 0
        assert engine.clear_session("s1") is True
        assert engine.get_turn_count("s1") == 0


def test_memory_engine_persistent_reads_no_consent_required() -> None:
    """Verifies persistent read operations execute without requiring consent objects."""
    with MemoryEngine(db_path=":memory:") as engine:
        auth = engine.grant_explicit_consent()
        engine.store_persistent("pref", "k1", "v1", auth)

        # Reads require no consent parameters
        rec = engine.get_exact("pref", "k1")
        assert rec is not None
        assert rec.value == "v1"

        category_list = engine.list_by_category("pref")
        assert len(category_list) == 1

        prefix_list = engine.search_by_prefix("pref", "k")
        assert len(prefix_list) == 1

        inspection = engine.inspect_all()
        assert len(inspection) == 1

        export_data = engine.export_to_dict()
        assert export_data["export_metadata"]["total_records"] == 1


def test_memory_engine_store_persistent_mutations_and_consent() -> None:
    """Verifies persistent creation and consent authorization enforcement."""
    with MemoryEngine(db_path=":memory:") as engine:
        valid_auth = engine.grant_explicit_consent(details="Approved")
        rec = engine.store_persistent(
            category="fact",
            key="user_name",
            value="Alice",
            authorization=valid_auth,
            source="user_explicit",
        )
        assert rec.value == "Alice"

        # Denied authorization rejection
        denied_auth = engine.deny_consent()
        msg_denied = "granted is False"
        with pytest.raises(MemoryAuthorizationError, match=msg_denied):
            engine.store_persistent("fact", "k2", "v2", denied_auth)

        # Policy & system default rejection
        now = datetime.now(UTC)
        policy_auth = AuthorizationRecord(
            granted=True,
            auth_type=AuthorizationType.PRE_AUTHORIZED_POLICY,
            granted_at=now,
        )
        msg_policy = "requires EXPLICIT_USER_CONSENT"
        with pytest.raises(MemoryAuthorizationError, match=msg_policy):
            engine.store_persistent("fact", "k3", "v3", policy_auth)

        # Duplicate key rejection
        with pytest.raises(MemoryValidationError, match="already exists"):
            engine.store_persistent("fact", "user_name", "Bob", valid_auth)


def test_memory_engine_update_persistent_and_consent() -> None:
    """Verifies persistent update operation and authorization enforcement."""
    with MemoryEngine(db_path=":memory:") as engine:
        valid_auth = engine.grant_explicit_consent()
        engine.store_persistent("pref", "theme", "light", valid_auth)

        # Valid update
        updated_rec = engine.update_persistent("pref", "theme", "dark", valid_auth)
        assert updated_rec.value == "dark"

        # Denied update rejection
        denied_auth = engine.deny_consent()
        with pytest.raises(MemoryAuthorizationError, match="granted is False"):
            engine.update_persistent("pref", "theme", "auto", denied_auth)

        # Non-existent key update
        with pytest.raises(MemoryNotFoundError, match="Cannot update non-existent"):
            engine.update_persistent("pref", "missing", "val", valid_auth)


def test_memory_engine_delete_persistent_and_consent() -> None:
    """Verifies persistent deletion operation and authorization enforcement."""
    with MemoryEngine(db_path=":memory:") as engine:
        valid_auth = engine.grant_explicit_consent()
        engine.store_persistent("pref", "temp_key", "val", valid_auth)

        # Denied delete rejection
        denied_auth = engine.deny_consent()
        with pytest.raises(MemoryAuthorizationError, match="granted is False"):
            engine.delete_persistent("pref", "temp_key", denied_auth)

        # Valid deletion
        res = engine.delete_persistent("pref", "temp_key", valid_auth)
        assert res is True
        assert engine.get_exact("pref", "temp_key") is None

        # Non-existent key deletion
        with pytest.raises(MemoryNotFoundError, match="Cannot delete non-existent"):
            engine.delete_persistent("pref", "temp_key", valid_auth)


def test_memory_engine_consent_helpers_delegation() -> None:
    """Verifies convenience consent helper delegation through MemoryEngine facade."""
    with MemoryEngine(db_path=":memory:") as engine:
        granted = engine.grant_explicit_consent(details="Audit note")
        assert granted.granted is True
        assert engine.is_authorized(granted) is True

        denied = engine.deny_consent()
        assert denied.granted is False
        assert engine.is_authorized(denied) is False

        engine.validate_authorization(granted)  # Does not raise
        with pytest.raises(MemoryAuthorizationError):
            engine.validate_authorization(denied)


def test_memory_engine_error_boundary_wrapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that persistent store errors wrap into MemoryStorageError."""

    class FailingStore:
        def get_exact(self, category: str, key: str) -> Any:
            raise sqlite3.OperationalError("Read DB error")

        def list_by_category(self, category: str) -> Any:
            raise sqlite3.OperationalError("List DB error")

        def search_by_prefix(self, category: str, prefix: str) -> Any:
            raise sqlite3.OperationalError("Search DB error")

        def inspect_all(self) -> Any:
            raise sqlite3.OperationalError("Inspect DB error")

        def export_to_dict(self) -> Any:
            raise sqlite3.OperationalError("Export DB error")

        def store_persistent(self, *args: Any, **kwargs: Any) -> Any:
            raise sqlite3.OperationalError("Store DB error")

        def update_persistent(self, *args: Any, **kwargs: Any) -> Any:
            raise sqlite3.OperationalError("Update DB error")

        def delete_persistent(self, *args: Any, **kwargs: Any) -> Any:
            raise sqlite3.OperationalError("Delete DB error")

    failing_store = FailingStore()
    with MemoryEngine(persistent_store=failing_store) as engine:  # type: ignore[arg-type]
        valid_auth = engine.grant_explicit_consent()

        with pytest.raises(MemoryStorageError, match="Failed to retrieve"):
            engine.get_exact("cat", "k")

        with pytest.raises(MemoryStorageError, match="Failed to list"):
            engine.list_by_category("cat")

        with pytest.raises(MemoryStorageError, match="Failed to search"):
            engine.search_by_prefix("cat", "k")

        with pytest.raises(MemoryStorageError, match="Failed to inspect"):
            engine.inspect_all()

        with pytest.raises(MemoryStorageError, match="Failed to export"):
            engine.export_to_dict()

        with pytest.raises(MemoryStorageError, match="Failed to store"):
            engine.store_persistent("cat", "k", "v", valid_auth)

        with pytest.raises(MemoryStorageError, match="Failed to update"):
            engine.update_persistent("cat", "k", "v", valid_auth)

        with pytest.raises(MemoryStorageError, match="Failed to delete"):
            engine.delete_persistent("cat", "k", valid_auth)


def test_memory_engine_no_brain_or_ads_001_005_dependencies() -> None:
    """Verifies that MemoryEngine has no Brain or execution dependencies."""
    with MemoryEngine(db_path=":memory:") as engine:
        assert not hasattr(engine, "brain")
        assert not hasattr(engine, "planning")
        assert not hasattr(engine, "execution")


def test_memory_engine_close_exception_handling() -> None:
    """Verifies that engine.close() suppresses exceptions raised during store close."""

    class StoreWithFailingClose:
        def close(self) -> None:
            raise RuntimeError("Close error")

    engine = MemoryEngine(persistent_store=StoreWithFailingClose())  # type: ignore[arg-type]
    engine.close()  # Does not raise


# =====================================================================
# MemoryCapability Unit Tests (Milestone 6)
# =====================================================================


def test_memory_capability_properties_and_di() -> None:
    """Verifies MemoryCapability capability name, engine property, and custom DI."""
    engine_custom = MemoryEngine(db_path=":memory:")
    cap_custom = MemoryCapability(memory_engine=engine_custom)

    assert cap_custom.name == CAPABILITY_MEMORY
    assert cap_custom.name == "memory"
    assert cap_custom.engine is engine_custom

    cap_default = MemoryCapability()
    assert isinstance(cap_default.engine, MemoryEngine)


def test_memory_capability_session_dispatch() -> None:
    """Verifies MemoryCapability session operation dispatch to MemoryEngine."""
    engine = MemoryEngine(db_path=":memory:")
    cap = MemoryCapability(memory_engine=engine)
    turn = _make_turn(1, "sess-1", "hello")

    rec_turn = cap.execute("record_turn", turn)
    assert rec_turn == turn

    turns = cap.execute("get_session_turns", "sess-1", limit=5)
    assert len(turns) == 1
    assert turns[0] == turn

    count = cap.execute("get_turn_count", "sess-1")
    assert count == 1

    cleared = cap.execute("clear_session", "sess-1")
    assert cleared is True
    assert cap.execute("get_turn_count", "sess-1") == 0


def test_memory_capability_persistent_read_dispatch() -> None:
    """Verifies MemoryCapability persistent read operation dispatch."""
    engine = MemoryEngine(db_path=":memory:")
    cap = MemoryCapability(memory_engine=engine)
    auth = cap.execute("grant_explicit_consent", "Test consent")

    cap.execute("store_persistent", "pref", "k1", "v1", auth)

    exact = cap.execute("get_exact", "pref", "k1")
    assert exact is not None
    assert exact.value == "v1"

    cat_list = cap.execute("list_by_category", "pref")
    assert len(cat_list) == 1

    prefix_list = cap.execute("search_by_prefix", "pref", "k")
    assert len(prefix_list) == 1

    inspection = cap.execute("inspect_all")
    assert len(inspection) == 1

    export_dict = cap.execute("export_to_dict")
    assert export_dict["export_metadata"]["total_records"] == 1


def test_memory_capability_persistent_mutation_dispatch() -> None:
    """Verifies MemoryCapability persistent mutation dispatch and update/delete."""
    engine = MemoryEngine(db_path=":memory:")
    cap = MemoryCapability(memory_engine=engine)
    auth = cap.execute("grant_explicit_consent")

    cap.execute("store_persistent", "pref", "k1", "v1", auth)

    updated = cap.execute("update_persistent", "pref", "k1", "v2", auth)
    assert updated.value == "v2"

    deleted = cap.execute("delete_persistent", "pref", "k1", auth)
    assert deleted is True
    assert cap.execute("get_exact", "pref", "k1") is None


def test_memory_capability_consent_helpers_dispatch() -> None:
    """Verifies MemoryCapability consent helper method dispatches."""
    cap = MemoryCapability()

    granted = cap.execute("grant_explicit_consent", "Audit")
    assert granted.granted is True
    assert cap.execute("is_authorized", granted) is True

    denied = cap.execute("deny_consent")
    assert denied.granted is False
    assert cap.execute("is_authorized", denied) is False

    cap.execute("validate_authorization", granted)  # Does not raise
    with pytest.raises(MemoryAuthorizationError):
        cap.execute("validate_authorization", denied)


def test_memory_capability_invalid_and_unsupported_actions() -> None:
    """Verifies MemoryCapability validation of invalid action parameters."""
    cap = MemoryCapability()

    msg_unsupported = "Unsupported memory capability action"
    with pytest.raises(MemoryValidationError, match=msg_unsupported):
        cap.execute("unsupported_method")

    msg_empty = "Action must be a non-empty string"
    with pytest.raises(MemoryValidationError, match=msg_empty):
        cap.execute("")

    with pytest.raises(MemoryValidationError, match=msg_empty):
        cap.execute(123)  # type: ignore[arg-type]


def test_memory_capability_missing_method_on_custom_engine() -> None:
    """Verifies error handling if custom engine is missing a supported action method."""
    class IncompleteEngine:
        pass

    cap = MemoryCapability(memory_engine=IncompleteEngine())  # type: ignore[arg-type]
    msg = "Memory engine method missing for action"
    with pytest.raises(MemoryValidationError, match=msg):
        cap.execute("get_turn_count", "s1")


# =====================================================================
# Public Boundary Tests
# =====================================================================


def test_public_api_exports() -> None:
    """Verifies exact public API exports in argos.memory.__all__."""
    expected_exports = {
        "MemoryScope",
        "AuthorizationType",
        "AuthorizationRecord",
        "MemoryRecord",
        "SessionTurn",
        "MemorySearchResult",
        "SessionStore",
        "validate_session_id",
        "SQLiteStore",
        "PersistentStore",
        "ConsentManager",
        "MemoryEngine",
        "CAPABILITY_MEMORY",
        "MemoryCapability",
        "MemoryError",
        "MemoryValidationError",
        "MemoryStorageError",
        "MemoryAuthorizationError",
        "MemoryNotFoundError",
    }
    actual_exports = set(memory_pkg.__all__)
    assert expected_exports == actual_exports

    for symbol in expected_exports:
        assert hasattr(memory_pkg, symbol)
