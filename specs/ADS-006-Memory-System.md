# ADS-006 — Memory System

**Document:** Architecture Design Specification (ADS)  
**Subsystem:** Memory Subsystem (`argos.memory`)  
**Version:** 1.1  
**Status:** Approved (Frozen)  
**Date:** 2 July 2026  
**Author:** Arjun Saini & Antigravity  
**Governing Documents:** [`constitution.md`](file:///f:/ARGOS/constitution.md) (Article IV), [`architecture.md`](file:///f:/ARGOS/ARCHITECTURE.md) (Section 7), [`decisions.md`](file:///f:/ARGOS/decisions.md) (EDR-003, EDR-024), [`mvp.md`](file:///f:/ARGOS/mvp.md) (Section 3)  

---

## 1. Purpose

The **Memory System** (`argos.memory`) provides multi-turn conversational context and durable semantic persistence for the ARGOS Cognitive Operating System.

Prior to ADS-006, ARGOS operated in an amnesic state: `WorkingMemory` inside `argos.brain` reset at the start of every user request, preventing the system from remembering prior conversation turns, recalling persistent user preferences, or tracking multi-request goals. 

ADS-006 implements the **Dual-Store Memory Architecture** frozen in **EDR-024**, establishing:
1. **Session Memory:** Fast, in-memory, turn-based conversational continuity.
2. **Persistent Semantic Memory:** Transactionally sound, local SQLite storage for user preferences and declarative facts.
3. **Memory Consent Gateway:** Strict enforcement of the Constitutional mandate (*"Remember with permission"*).

---

## 2. Scope

### In-Scope (Version 1)
* In-memory, bounded FIFO turn tracking for multi-turn session dialogue (`SessionMemory`).
* Durable, local, file-backed SQLite storage for structured user facts and configurations (`PersistentStore`).
* Constitutional memory consent and authorization provenance validation (`ConsentManager`).
* Public facade (`MemoryEngine`) orchestrating retrieval, persistence, inspection, and export.
* Standard `CognitiveCapability` adapter (`MemoryCapability`) integrating memory into `BrainCore`'s reasoning loop.
* 100% statement coverage, robust transactional rollback testing, and zero third-party dependencies.

### Out-of-Scope (Explicit V1 Deferrals per EDR-024)
* Vector embeddings, vector databases, and neural similarity search.
* Unsupervised or autonomous memory formation.
* Automated memory forgetting, heuristic eviction, relevance ranking, or probabilistic decay.
* Episodic memory graph networks (deep longitudinal event histories).
* Procedural memory (learned automation routines and skills).
* Cloud synchronization, multi-tenant databases, or remote endpoints.

---

## 3. Architectural Position

The Memory Subsystem operates as a subordinate **Cognitive Capability** registered with `BrainCore`'s `CapabilityManager`:

```
                           User Request
                                │
                                ▼
                       ┌─────────────────┐
                       │    BrainCore    │ ◄── (Owns Lifecycle & Loop)
                       └────────┬────────┘
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
           WorkingMemory   GoalManager   DecisionEngine
           (Transient)     (Active)      (Reasoning)
                 │              │              │
                 └──────────────┼──────────────┘
                                ▼
                       CapabilityManager (Registry)
                                │
        ┌────────────┬──────────┼────────────┬────────────┐
        ▼            ▼          ▼            ▼            ▼
      Input        Intent     Planning   Execution     Memory
    (ADS-001)    (ADS-002)   (ADS-003)   (ADS-004)   (ADS-006)
                                                          │
                                         ┌────────────────┴────────────────┐
                                         ▼                                 ▼
                                  SessionStore                     PersistentStore
                               (In-Memory FIFO)                   (Local SQLite DB)
```

During the cognitive loop:
* **`REASON` Stage:** `BrainCore` invokes memory retrieval capabilities to inject relevant session context and user preferences into `WorkingMemory`.
* **`REFLECT` Stage:** `BrainCore` evaluates session outcomes. If new preferences or durable facts are established, `BrainCore` coordinates memory persistence with explicit user consent before committing.

> [!NOTE]
> **Cognitive Phases vs. Cognitive States:** Terms such as `REASON`, `ACT`, `OBSERVE`, and `REFLECT` in this specification describe conceptual cognitive phases. They are not additional `CognitiveState` enum values. `BrainCore` maps these conceptual phases onto the formal ADS-005 states, primarily `REASONING`, `EXECUTING`, and `EVALUATING`.

---

## 4. Memory Taxonomy

In strict accordance with EDR-024, memory in ARGOS is categorized into three distinct tiers:

| Memory Tier | Ownership | Lifecycle | Storage Mechanism | Consent Requirement | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Working Memory** | `argos.brain` | Single request / cycle | In-memory `@dataclass(slots=True)` | Implicit (System runtime) | Intra-cycle scratchpad for active DTOs, parse trees, and plans. Resets every request. |
| **Session Memory** | `argos.memory` | Multi-turn active session | In-memory FIFO queue | Implicit within session | Retains recent conversation turns, prior intents, and active entities for dialogue continuity. |
| **Persistent Semantic Memory** | `argos.memory` | Durable across reboots | Local SQLite database file | **Explicit User Consent** | Stores long-term user preferences, system configurations, and approved declarative facts. |

---

## 5. Responsibilities

* **Deterministic Retrieval:** Provide exact-match lookup of semantic memories by key, category, and key prefix.
* **Turn-Based Session Tracking:** Record chronological conversation turns, preserving turn ordering, user inputs, intents, and execution statuses.
* **Transactional Persistence:** Atomically insert, update, and delete durable facts in a local SQLite database with transactional integrity and controlled failure behavior.
* **Authorization Provenance Enforcement:** Enforce that every persistent write, update, or deletion carries valid authorization metadata.
* **User Inspection & Transparency:** Expose inspection methods allowing users to review all stored memories in human-readable formats.
* **Data Portability:** Provide structured JSON export of all stored memories.
* **Subsystem Isolation:** Encapsulate all database connections, SQLite implementation details, and SQL queries away from external consumers.

---

## 6. Non-Responsibilities

* **Non-Cognitive:** `argos.memory` does NOT reason, infer user intent, plan actions, or decide what should be remembered.
* **No Semantic Relevance Determination:** `BrainCore` and its reasoning components determine when memory retrieval is useful and which deterministic query should be issued. The Memory subsystem executes the requested retrieval operation without probabilistic relevance ranking, semantic inference, or autonomous selection.
* **No General Policy Enforcement:** `argos.memory` validates memory-specific authorization; it does NOT serve as the generalized ARGOS Policy Engine.
* **No Execution:** `argos.memory` never executes OS actions, files, or network commands.
* **No Semantic Guessing:** It does not use probabilistic vector math to guess loosely related facts.
* **No Unsupervised Scraping:** It never writes to persistent storage without explicit authorization.

---

## 7. Package Boundary

The subsystem is implemented under `src/argos/memory/`:

```text
src/argos/memory/
├── __init__.py               # Public API boundary exports
├── constants.py              # System constants, defaults, and limits
├── exceptions.py             # MemoryError hierarchy
├── models.py                 # Dataclasses and enums (slots=True)
├── session_store.py          # In-memory FIFO turn tracker
├── sqlite_store.py           # SQLite persistence implementation
├── consent_manager.py        # Authorization and provenance validator
└── memory_engine.py          # Public facade orchestrator
```

All internal storage queries, SQLite connections, and helper classes are strictly private and not exported at the package root.

---

## 8. Public API

External consumers (including `argos.brain`) interact exclusively with the symbols exported from `argos.memory`:

### Public Facade
* `MemoryEngine`: Primary public interface orchestrating session and persistent memory.

### Public Enums & Models
* `MemoryScope`: StrEnum (`SESSION`, `PERSISTENT`).
* `AuthorizationType`: StrEnum (`EXPLICIT_USER_CONSENT`, `PRE_AUTHORIZED_POLICY`, `SYSTEM_DEFAULT`).
* `AuthorizationRecord`: Dataclass capturing consent provenance.
* `MemoryRecord`: Dataclass capturing durable semantic memory entries.
* `SessionTurn`: Dataclass capturing multi-turn conversation steps.
* `MemorySearchResult`: Dataclass capturing query outcomes.

### Public Exceptions
* `MemoryError`: Base exception for all memory errors.
* `MemoryValidationError`: Raised on invalid keys, scopes, or payloads.
* `MemoryStorageError`: Raised on SQLite disk/I/O or database access failures.
* `MemoryAuthorizationError`: Raised when persistent writes lack valid consent.
* `MemoryNotFoundError`: Raised when attempting to update or delete a non-existent key.

---

## 9. Core DTOs / Entities

All DTOs are declared with `@dataclass(slots=True)` for strict typing and performance.

### 9.1 Enums
```python
class MemoryScope(StrEnum):
    SESSION = "session"
    PERSISTENT = "persistent"

class AuthorizationType(StrEnum):
    EXPLICIT_USER_CONSENT = "explicit_user_consent"
    PRE_AUTHORIZED_POLICY = "pre_authorized_policy"
    SYSTEM_DEFAULT = "system_default"
```

> [!IMPORTANT]
> **V1 Authorization Rules:**
> * `EXPLICIT_USER_CONSENT` is the **ONLY** authorization type permitted to authorize persistent mutations (writes, updates, deletions) in Version 1.
> * `PRE_AUTHORIZED_POLICY` is reserved for future integration with the dedicated Policy Engine (`argos.policy`) and **MUST NOT** authorize persistent mutation in V1.
> * `SYSTEM_DEFAULT` **MUST NOT** authorize persistent mutation in V1.
> * There is no implicit or default authorization for persistent writes, updates, or deletions. Memory enforces valid authorization records, but does not define or evaluate generalized system policies.

### 9.2 AuthorizationRecord
```python
@dataclass(slots=True)
class AuthorizationRecord:
    granted: bool
    auth_type: AuthorizationType
    granted_at: datetime
    details: str | None = None
```

### 9.3 MemoryRecord
```python
@dataclass(slots=True)
class MemoryRecord:
    memory_id: str
    scope: MemoryScope
    category: str
    key: str
    value: Any
    source: str
    created_at: datetime
    updated_at: datetime
    authorization: AuthorizationRecord
```

### 9.4 SessionTurn
```python
@dataclass(slots=True)
class SessionTurn:
    turn_id: int
    session_id: str
    user_input: str
    normalized_text: str
    intent_name: str | None
    plan_summary: str | None
    execution_status: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## 10. Session Memory Design

* **Storage:** In-memory queue managed by `SessionStore`.
* **Ordering:** Strictly chronological (ascending by `timestamp` and auto-incrementing `turn_id`).
* **Eviction Policy:** Deterministic **FIFO (First-In, First-Out)** bounded by `DEFAULT_MAX_SESSION_TURNS = 50`.
  * When turn count exceeds 50, the oldest turn is discarded.
* **Multi-Turn Context Resolution:** Provides queries to retrieve the last $N$ turns for pronoun resolution and conversational context.
* **Session Lifecycle:** Sessions persist in memory until explicitly cleared (`clear_session(session_id)`) or process shutdown.

---

## 11. Persistent Semantic Memory Design

* **Storage:** Local SQLite database file managed by `SQLiteStore`.
* **Scope:** Long-term key-value storage partitioned by categorical domains (`preference`, `system`, `user_fact`).
* **Uniqueness:** Uniquely indexed on `(category, memory_key)`.
* **Durability:** Survives application shutdowns and system reboots.
* **No Verbatim Prompts:** Raw prompt strings are never stored verbatim in persistent semantic memory; only structured, verified facts (e.g. `key="editor.default", value="code"`).

---

## 12. SQLite Storage Architecture

To ensure SQLite remains an implementation detail:
1. `MemoryEngine` interacts with storage exclusively through an abstract interface or private manager (`SQLiteStore`).
2. No SQL queries, `sqlite3.Connection` objects, or table structures leak through public method signatures.
3. If SQLite is replaced with another engine in the future, only `SQLiteStore` is modified; `MemoryEngine` and `BrainCore` remain untouched.
4. Uses Python's standard library `sqlite3` with default thread-safety behavior and timeout safeguards. Because Version 1 operates in a single-user, sequential execution model, cross-thread connection sharing is not required.

---

## 13. Database Schema

The database consists of two tables: `schema_migrations` and `semantic_memories`.

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

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

CREATE INDEX IF NOT EXISTS idx_memories_cat_key 
ON semantic_memories (category, memory_key);

CREATE INDEX IF NOT EXISTS idx_memories_updated 
ON semantic_memories (updated_at);
```

---

## 14. Serialization Rules

* `value_json`: Values are serialized to valid JSON text using `json.dumps(value, sort_keys=True)`.
* Supported types: `str`, `int`, `float`, `bool`, `list`, `dict`.
* Unsupported types (e.g. arbitrary objects, binary buffers) raise `MemoryValidationError`.
* Deserialization: Stored values are deserialized via `json.loads()` when returned in `MemoryRecord`.
* Timestamps: Serialized as ISO 8601 UTC strings (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`).

---

## 15. Session Identification

* **Default Session ID:** Defined in `constants.py` as `DEFAULT_SESSION_ID = "default"`.
* **API Invariant:** All session methods accept `session_id: str = DEFAULT_SESSION_ID`.
* **Validation:** Session IDs must be non-empty, trimmed strings containing only alphanumeric, hyphen, and underscore characters. Invalid IDs raise `MemoryValidationError`.

---

## 16. Memory Retrieval Semantics

Retrieval is strictly deterministic. Exact match only:
1. `get_exact(category: str, key: str) -> MemoryRecord | None`: Returns the matching record or `None`.
2. `list_by_category(category: str) -> list[MemoryRecord]`: Returns all records in a category ordered by `key`.
3. `search_by_prefix(category: str, prefix: str) -> list[MemoryRecord]`: Returns all records where `key` starts with `prefix`.
4. `get_session_turns(session_id: str = DEFAULT_SESSION_ID, limit: int = 10) -> list[SessionTurn]`: Returns the most recent $N$ turns in chronological order.
* **Cognition vs. Memory Boundary:** `BrainCore` and its reasoning components determine when memory retrieval is useful and which deterministic query should be issued. The Memory subsystem executes the requested retrieval operation without probabilistic relevance ranking, semantic inference, or autonomous selection.
* **Retrieval Degradation vs. Storage Corruption:**
  * **Transient Retrieval Unavailability:** If storage experiences transient lock contention, temporary busy timeouts, or non-critical read unavailability during retrieval, `MemoryEngine` gracefully degrades: it logs a warning at `DEBUG` level and returns empty results (or `None`), allowing `BrainCore` to continue reasoning using raw input without cognitive state disruption.
  * **Confirmed Storage Corruption:** Confirmed database corruption (e.g. malformed disk image, unparseable database header) or unrecoverable storage failures are **never** silently converted into empty context. Any confirmed corruption encountered during retrieval must remain observable and raise `MemoryStorageError`, which is wrapped as `ProcessingError` at the capability boundary.

---

## 17. Memory Write Semantics

* **Session Write (`record_turn`):** Appends a turn to in-memory `SessionStore`. Automatic; requires no user confirmation.
* **Persistent Write (`store_persistent`):**
  1. Validates category, key, and JSON serializability.
  2. Verifies that `authorization.granted is True`. If `False`, raises `MemoryAuthorizationError`.
  3. Executes atomic SQL `INSERT INTO semantic_memories ...`.
  4. If `(category, memory_key)` already exists, raises `MemoryValidationError` (use `update_persistent` instead).
  5. Returns the compiled `MemoryRecord`.

---

## 18. Memory Update Semantics

* **Method:** `update_persistent(category: str, key: str, new_value: Any, authorization: AuthorizationRecord) -> MemoryRecord`.
* **Pre-conditions:** Record must exist (otherwise raises `MemoryNotFoundError`).
* **Authorization:** `authorization.granted` must be `True` (otherwise raises `MemoryAuthorizationError`).
* **Transaction:** Updates `value_json`, `updated_at`, and authorization fields atomically. Never leaves partially updated records.

---

## 19. Memory Deletion Semantics

* **Method:** `delete_persistent(category: str, key: str, authorization: AuthorizationRecord) -> bool`.
* **Pre-conditions:** Record must exist (otherwise raises `MemoryNotFoundError`).
* **Authorization:** Requires `authorization.granted is True`.
* **Execution:** Atomically executes `DELETE FROM semantic_memories WHERE category = ? AND memory_key = ?`.
* **Observable:** Returns `True` upon confirmed deletion.

---

## 20. Memory Inspection

In adherence to Constitution Article IV (*"manageable and reviewable by the user"*):
* `inspect_all() -> list[dict[str, Any]]`: A local, read-only transparency mechanism returning the actual stored values, categories, keys, and authorization provenance across persistent memory. Inspection is strictly read-only and never alters database state.

---

## 21. Memory Export

* `export_to_dict() -> dict[str, Any]`: Exports persistent semantic memory only in Version 1. Generates a structured dictionary containing export metadata, timestamps, and all stored persistent memory records. Session Memory is intentionally ephemeral and is excluded from persistent memory export. Export operations are strictly read-only and never mutate memory.

---

## 22. Consent / Authorization Model

Memory operations are governed by the following consent requirements:

| Operation | Target Store | Requires User Consent? | Cognitive State |
| :--- | :--- | :---: | :--- |
| Read / Query | Session & Persistent | **NO** | Automatic in `REASON` |
| Record Turn | Session Memory | **NO** | Automatic in `REFLECT` |
| Create Fact | Persistent Semantic | **YES** | `WAITING_FOR_USER` |
| Update Fact | Persistent Semantic | **YES** | `WAITING_FOR_USER` |
| Delete Fact | Persistent Semantic | **YES** | `WAITING_FOR_USER` |
| Clear Session | Session Memory | **NO** | Explicit API call |
| Inspect / Export | Persistent Semantic | **NO** | Safe read-only API |

When a persistent mutation is proposed during cognition, `BrainCore` transitions to `WAITING_FOR_USER`, presenting the proposed key and value for user confirmation. In Version 1, `EXPLICIT_USER_CONSENT` is the only authorization type permitted to approve persistent writes, updates, or deletions.

---

## 23. Authorization Provenance

Every persistent memory record permanently stores an `AuthorizationRecord`:
* `auth_type`: How authorization was granted (`EXPLICIT_USER_CONSENT` for all V1 mutations; `PRE_AUTHORIZED_POLICY` and `SYSTEM_DEFAULT` are reserved for future policy integration).
* `granted_at`: Exact UTC timestamp when confirmation was provided.
* `details`: Optional audit string (e.g. `"Confirmed by user at turn 4"`).

---

## 24. Failure Semantics

Failure handling is granular and non-equivalent, with unambiguous precedence:

1. **Transient Retrieval Unavailability:** Graceful degradation. If the database experiences transient lock contention or temporary unavailability during an optional read, retrieval logs a warning at `DEBUG` and returns empty context (`None` or empty list). Cognition continues using raw input alone.
2. **Storage Corruption / Unrecoverable Storage Failure:** Must remain strictly observable. Confirmed database corruption (e.g., malformed SQLite header, unparseable disk image, I/O hardware faults) is **never** silently swallowed or converted into empty context. It immediately raises `MemoryStorageError`, which `MemoryCapability` converts/wraps into `ProcessingError` at the capability boundary.
3. **Persistent Write Failure:** Must NEVER report false success. If an atomic commit fails, `MemoryStorageError` is raised, working memory records the failure in decision history, and an explicit failure outcome is reported.
4. **Persistent Update Failure:** Atomic rollback. Failed updates must never leave partially updated or corrupted records. Transactions cleanly roll back, maintaining database consistency.
5. **Persistent Deletion Failure:** Observable. Accurately reports that deletion could not be completed rather than falsely confirming removal.
6. **Consent Denial:** Not a system error. User denial of consent is a valid human choice. The commit is cleanly aborted, the refusal is recorded in working memory decision logs, and cognition completes with a consistent terminal status (`COMPLETED`).

---

## 25. Error Hierarchy

```text
argos.memory
└── MemoryError (base exception for argos.memory)
       ├── MemoryValidationError
       ├── MemoryStorageError
       ├── MemoryAuthorizationError
       └── MemoryNotFoundError
```

Memory exceptions are completely independent of `argos.brain` exceptions. At the `CognitiveCapability` boundary, `MemoryCapability` converts and wraps unexpected memory failures into the existing Brain-level `ProcessingError` contract where appropriate, preserving subsystem independence and dependency inversion.

---

## 26. Brain Integration

`BrainCore` coordinates memory using the standard cognitive loop:

1. **`PERCEIVE` & `INTERPRET`:** User request is parsed and intent classified.
2. **`REASON`:** `BrainCore` invokes `CAPABILITY_MEMORY` to retrieve recent session turns and relevant user preferences. Context is placed into `WorkingMemory.context`.
3. **`DECIDE` & `PLAN`:** `Planner` generates a plan informed by recalled preferences.
4. **`ACT` & `OBSERVE`:** `ExecutionEngine` executes the plan.
5. **`REFLECT`:** `BrainCore` inspects outcomes. If the user explicitly instructed ARGOS to remember a preference:
   * If consent is not yet granted, `BrainCore` pauses at `WAITING_FOR_USER`.
   * Upon consent, `BrainCore` commits the record via `CAPABILITY_MEMORY`.

---

## 27. CognitiveCapability Integration

`argos.memory` provides `MemoryCapability`, an adapter conforming to `CognitiveCapability`:
```python
class MemoryCapability(CognitiveCapability):
    def __init__(self, memory_engine: MemoryEngine) -> None:
        self._engine = memory_engine

    @property
    def name(self) -> str:
        return "memory"

    def execute(self, action: str, *args: Any, **kwargs: Any) -> Any:
        ...
```
`BrainCore` registers this capability without importing SQLite or database classes.

---

## 28. Dependency Injection

`MemoryEngine` accepts custom store backends via constructor injection:
```python
def __init__(
    self,
    session_store: SessionStore | None = None,
    persistent_store: PersistentStore | None = None,
    consent_manager: ConsentManager | None = None,
    db_path: str | Path | None = None,
) -> None:
    ...
```
This enables injecting an in-memory SQLite store (`":memory:"`) for unit testing with zero disk side-effects.

---

## 29. Privacy Requirements (Constitution Article IV)

* **Local Storage Only:** SQLite databases must reside exclusively in local user application directories (default: `~/.argos/memory.db`).
* **No Telemetry / Cloud Sync:** Zero network transmission of memory data.
* **No Raw Prompt Dumps:** Semantic memory stores structured facts, not conversational logs.
* **Full Deletion Support:** Users can inspect, export, and explicitly delete individual stored records at any time.

---

## 30. Logging Requirements

* **INFO Level:** Lifecycle events only (e.g. `"Session memory initialized"`, `"Persistent memory committed: category=preference"`).
* **Zero Payload Leaks:** Stored memory values, sensitive preferences, or personal details must **NEVER** appear in logs at `INFO` level.
* **DEBUG Level:** Permitted to record query diagnostics and timing without leaking credentials.

---

## 31. Retention Rules

* **Session Memory:** Retained in RAM for the life of the active session. Evicted via FIFO past capacity limit.
* **Persistent Memory:** Retained indefinitely until explicitly updated or deleted by the user.

---

## 32. Capacity Limits

Defined in `constants.py`:
* `DEFAULT_MAX_SESSION_TURNS = 50`: Maximum turns in session history.
* `MAX_KEY_LENGTH = 128`: Maximum character length for memory keys.
* `MAX_CATEGORY_LENGTH = 64`: Maximum character length for category names.
* `MAX_VALUE_BYTES = 65536` (64 KB): Maximum JSON payload size per memory record.

---

## 33. Transaction Semantics

* Every persistent write, update, and deletion is wrapped in an explicit SQLite transaction (`BEGIN IMMEDIATE` ... `COMMIT`).
* On any exception, `ROLLBACK` is executed immediately.
* Database connections use Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) or standard rollback journals for atomic durability.

---

## 34. Concurrency Expectations

* Version 1 is designed for single-user, sequential CLI requests.
* SQLite connections use standard library defaults without cross-thread connection sharing.
* Connection timeouts (default: 5.0 seconds) prevent lock contention.
* Multi-process or distributed concurrent writes are deferred to future versions.

---

## 35. Initialization & Database Lifecycle

* Database initialization occurs automatically upon first instantiation of `SQLiteStore`.
* Tables and indexes are created idempotently (`CREATE TABLE IF NOT EXISTS`).
* If parent directories do not exist, they are created automatically.
* Resources are cleanly closed via `close()` or context manager protocols.

---

## 36. Schema Versioning & Migration Strategy

* Initial schema version is `1`.
* Tracked via table `schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT)`.
* Future schema changes will execute sequential migration functions registered in a migration runner.

---

## 37. Testing Strategy

* **In-Memory Isolation:** All automated unit tests utilize SQLite in-memory databases (`db_path=":memory:"`), guaranteeing zero filesystem artifacts.
* **Transactional Rollback Verification:** Tests verify that failed writes leave the database completely unaltered.
* **Consent Enforcement Tests:** Verify that attempting writes without consent raises `MemoryAuthorizationError`.
* **FIFO Eviction Tests:** Verify that Session Memory evicts turn 1 when turn 51 is added.
* **Boundary Encapsulation Tests:** Verify that only public symbols are accessible from `argos.memory`.
* **Brain Integration Tests:** Test full loop execution with `MemoryCapability` registered in `BrainCore`.

---

## 38. Coverage Requirements

* **100% Statement Coverage** across all modules in `src/argos/memory/`.
* Zero statement misses.
* Complete branch and error-handling coverage.

---

## 39. Security & Safety Considerations

* **SQL Injection Prevention:** 100% parameterized queries (`?` placeholders); string formatting/concatenation into SQL queries is strictly prohibited.
* **Input Validation:** Category and key names must match regex pattern `^[a-zA-Z0-9_.-]+$`.
* **Resource Limits:** Maximum payload size enforced to prevent denial-of-service memory exhaustion.

---

## 40. Future Extension Points

* **Vector Search Provider:** A future `VectorStore` can sit alongside `PersistentStore` without breaking `MemoryEngine`.
* **Policy Engine Hooks:** When `argos.policy` is built, it can supply pre-authorized policies to `ConsentManager`.
* **Episodic Event Logger:** An episodic event store can attach to `SessionStore` when longitudinal reflection is introduced.

---

## 41. Explicit V1 Deferrals

* Vector embeddings and semantic similarity matching.
* Cloud database synchronization.
* Unsupervised automated memory extraction.
* Heuristic forgetting and automated pruning algorithms.
* Procedural skill automation storage.

---

## 42. Acceptance Criteria

1. `argos.memory` package passes all linting (`py -m ruff check .`) with 0 errors.
2. Comprehensive unit test suite in `tests/test_memory.py` achieves **100% statement coverage** with 0 misses.
3. Session memory correctly stores and retrieves up to 50 turns with deterministic FIFO eviction.
4. Persistent memory atomically stores, updates, retrieves, and deletes records using SQLite with transactional integrity and controlled failure behavior.
5. Persistent writes without valid authorization raise `MemoryAuthorizationError`.
6. Public API leaks zero SQL syntax, connection objects, or table structures.
7. Existing test suites for ADS-001 through ADS-005 continue to pass with 100% statement coverage.
