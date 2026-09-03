"""Public API boundary for the ARGOS Memory subsystem (ADS-006).

External consumers interact with symbols exported from this module.
Internal storage implementations and SQLite details remain private.
"""

from argos.memory.consent_manager import ConsentManager
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
from argos.memory.session_store import (
    SessionStore,
    validate_session_id,
)
from argos.memory.sqlite_store import (
    PersistentStore,
    SQLiteStore,
)

__all__ = [
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
]
