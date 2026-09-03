"""Domain transfer objects and enumerations for the ARGOS Memory subsystem (ADS-006).

All DTOs use dataclass(slots=True) for strict typing and memory efficiency.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MemoryScope(StrEnum):
    """Scope demarcation for memory entries."""

    SESSION = "session"
    PERSISTENT = "persistent"


class AuthorizationType(StrEnum):
    """Provenance type for memory authorizations.

    In Version 1 (ADS-006), EXPLICIT_USER_CONSENT is the ONLY authorization type
    permitted to authorize persistent mutations. PRE_AUTHORIZED_POLICY and
    SYSTEM_DEFAULT are reserved for future integration with the Policy Engine.
    """

    EXPLICIT_USER_CONSENT = "explicit_user_consent"
    PRE_AUTHORIZED_POLICY = "pre_authorized_policy"
    SYSTEM_DEFAULT = "system_default"


@dataclass(slots=True)
class AuthorizationRecord:
    """Captures authorization provenance and consent metadata for memory mutations."""

    granted: bool
    auth_type: AuthorizationType
    granted_at: datetime
    details: str | None = None


@dataclass(slots=True)
class MemoryRecord:
    """Represents a durable semantic memory record stored in persistent memory."""

    memory_id: str
    scope: MemoryScope
    category: str
    key: str
    value: Any
    source: str
    created_at: datetime
    updated_at: datetime
    authorization: AuthorizationRecord


@dataclass(slots=True)
class SessionTurn:
    """Represents a single conversational turn within an active multi-turn session."""

    turn_id: int
    session_id: str
    user_input: str
    normalized_text: str
    intent_name: str | None
    plan_summary: str | None
    execution_status: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemorySearchResult:
    """Represents the compiled outcome of a deterministic memory query."""

    query: str
    records: list[MemoryRecord] = field(default_factory=list)
    total_count: int = 0
