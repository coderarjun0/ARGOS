# Engineering Decision Record

**EDR ID:** EDR-001

**Title:** Adopt a Multi-Model AI Architecture

**Status:** Accepted

**Date:** 25 June 2026

---

# Context

ARGOS is intended to become a long-term Artificial Intelligence Operating System rather than a single-purpose chatbot.

Modern AI models have different strengths. Some excel at reasoning and teaching, others at coding, research, reviewing large codebases, or interacting with development environments.

Building ARGOS around a single AI model would make the project dependent on one provider and reduce flexibility as AI technology evolves.

---

# Problem Statement

Should ARGOS rely on one AI model for every task, or should it coordinate multiple specialized AI systems?

---

# Options Considered

## Option A — Single AI Model

### Advantages

* Simple architecture
* Easy implementation
* Lower integration complexity

### Disadvantages

* Vendor lock-in
* Limited by one model's strengths
* Harder to adapt as technology changes

---

## Option B — Multi-Model Architecture (Chosen)

### Advantages

* Best model for each task
* Easier to replace or upgrade models
* More scalable
* Future-proof architecture
* Encourages modular system design

### Disadvantages

* More complex orchestration
* Requires routing logic
* Higher integration effort

---

# Decision

ARGOS will adopt a **model-agnostic, multi-model architecture**.

The operating system will coordinate specialized AI models based on their strengths rather than depending on a single provider.

The selected development team is:

* **Arjun Saini** — Founder & Chief Architect
* **ChatGPT** — Mentor, System Architect, Documentation, Reasoning
* **GitHub Copilot** — Development Assistant
* **Claude** — Architecture & Code Reviewer
* **Perplexity** — Research Specialist

Additional models and tools may be introduced in future versions if they provide clear value.

---

# Rationale

This decision aligns with the long-term vision of ARGOS as an AI Operating System.

Separating responsibilities allows each model to contribute where it performs best while keeping the architecture modular and adaptable.

This approach also reduces dependence on any single AI provider and makes future upgrades significantly easier.

---

# Consequences

Positive:

* Flexible architecture
* Easier maintenance
* Better specialization
* Long-term scalability
* Reduced vendor lock-in

Negative:

* Increased implementation complexity
* Need for an orchestration layer
* Additional testing across multiple providers

---

# Future Considerations

Future versions of ARGOS should support:

* Dynamic model selection
* Local AI models for privacy-sensitive tasks
* Automatic fallback if a model is unavailable
* User-configurable AI preferences

---

# Review

This decision should be revisited whenever significant advances in AI models or orchestration frameworks occur.

---

**Approved By**

Founder & Chief Architect
**Arjun Saini**

Technical Mentor
**ChatGPT**

# Engineering Decision Records (EDRs)

**Project:** ARGOS (Adaptive Reasoning & General Operating System)

**Document:** DECISIONS.md

**Version:** 0.1

**Status:** Active

**Created:** 25 June 2026

**Last Updated:** 26 June 2026

**Author:** Arjun Saini

**Technical Mentor:** ChatGPT

---

# Purpose

This document records the major architectural and engineering decisions made during the development of ARGOS.

Each decision includes the reasoning behind it, the alternatives considered, and its long-term implications.

The purpose of this document is to preserve engineering intent for future development.

---

# EDR-002

## Universal Reasoning Pipeline

**Date:** 26 June 2026

### Decision

Every user request shall follow a standardized reasoning pipeline before execution.

### Pipeline

Wake Word

↓

Input

↓

Intent

↓

Context

↓

Memory

↓

Planning

↓

Policy Evaluation

↓

Execution

↓

Verification

↓

Reflection

↓

Memory Update

↓

Response

### Rationale

Consistency.

Reliability.

Predictable behavior.

---

# EDR-003

## Layered Memory Architecture

**Date:** 26 June 2026

### Decision

ARGOS shall implement multiple memory types rather than one shared memory.

### Memory Types

* Working Memory
* Session Memory
* Long-Term Memory
* Knowledge Base
* Skills Library
* Archive

### Deferred Decision

Healthy forgetting remains under evaluation and will be revisited after the complete memory architecture is defined.

---

# EDR-004

## Hybrid Agent Architecture

**Date:** 26 June 2026

### Decision

ARGOS shall support both permanent system agents and dynamically created task-specific agents.

### Permanent Agents

Examples:

* Memory Manager
* Scheduler
* Security

### Dynamic Agents

Examples:

* Research
* Coding
* Documentation
* Presentation
* Travel Planning

### Communication Rule

Task-specific agents communicate through the Agent Orchestrator rather than directly with one another.

---

# EDR-005

## Layered Cognitive Architecture

**Date:** 26 June 2026

### Decision

ARGOS separates the system into three logical layers.

### Layer 1

Intelligence

AI models responsible for reasoning.

### Layer 2

Cognition

ARGOS components responsible for planning, policies, orchestration, and memory.

### Layer 3

Action

Execution through tools and operating system integration.

### Rationale

Separating thinking, decision-making, and execution increases maintainability and scalability.

---

# EDR-006

## ARGOS Kernel

**Date:** 26 June 2026

### Decision

ARGOS shall include a Kernel responsible for shared system services.

### Kernel Services

* Event Bus
* Policy Engine
* Model Router
* Task Scheduler
* State Manager
* Capability Registry
* Logging
* Configuration

### Purpose

Provide common infrastructure for all higher-level components.

---

# EDR-007

## Policy-Based Decision Making

**Date:** 26 June 2026

### Decision

Whenever practical and safe, ARGOS shall follow user-defined policies instead of repeatedly asking identical questions.

### Example

If a user has approved the use of a local model for offline document summaries, ARGOS may follow that policy without asking again.

### Exceptions

Safety-critical and irreversible actions continue to require explicit confirmation unless a trusted policy permits otherwise.

---

# EDR-008

## Public Facade Pattern (Implementation EDR-001)

**Date:** 27 June 2026

### Context

To prevent coupling and circular dependencies between subsystem internals and external callers, subsystems must establish clear, high-level interfaces that encapsulate internal implementation logic.

### Decision

Every ARGOS subsystem must expose exactly one public facade class (e.g., `InputProcessor` for input, `IntentAnalyzer` for intent) as the exclusive orchestration and entry point. Helper workers and internal pipeline stages (e.g., normalizers, parsers, classifiers, extractors) must remain encapsulated within the package and hidden from external namespace exports in `__init__.py`.

### Consequences

* **Encapsulation**: Callers only import the facade and DTO container models, insulating them from internal refactoring.
* **Typing Safety**: Simplifies class references at subsystem boundaries.
* **Testing Modularity**: Facade orchestrators can be instantiated with mocked versions of internal dependencies for isolated testing.

---

# EDR-009

## Separation of Confidence Evaluation and Intent Classification (Implementation EDR-002)

**Date:** 28 June 2026

### Context

Originally, the classifier (`RuleEngine`) was slated to perform both category mapping and confidence calculations. This coupled pattern matching with mathematical estimation, violating the Single Responsibility Principle.

### Decision

Create an independent, stateless `ConfidenceEvaluator` component. The `RuleEngine` is responsible solely for determining primary and alternative intents. The `ConfidenceEvaluator` calculates the numeric confidence score (0.0 to 1.0) based on intent validity, ambiguities, and entity counts.

### Consequences

* **Independent Testing**: The mathematical calculations and confidence bounds can be unit tested in isolation using mocked intent and entity values.
* **Flexibility**: The confidence scoring heuristic can be easily tuned, modified, or replaced by ML probability scoring without impacting pattern rules.

---

# EDR-010

## Multiple Extracted Entities Support (Implementation EDR-003)

**Date:** 28 June 2026

### Context

User requests can reference multiple instances of a single parameter category within one command (e.g. *"Open chrome and vscode"* or *"Copy doc1.txt and doc2.txt"*). Storing entities as single strings would prevent batch operations.

### Decision

Define the `entities` field in `IntentResult` as `dict[str, list[str]]` instead of a plain `dict[str, str]`. The `EntityExtractor` must group all parsed targets by category as arrays, deduplicating and sorting matches.

### Consequences

* **Batch Execution**: Downstream executing agents can iterate over array arguments for parallel file or application tasks.
* **Deterministic Telemetry**: Deduplicating and sorting entity lists guarantees that identical raw inputs produce identical, predictable `IntentResult` objects.

---

# EDR-011

## Architecture-First Specification Workflow (Implementation EDR-004)

**Date:** 28 June 2026

### Context

In early stages, code implementations started before design details were frozen, leading to structural refactoring and changes during execution (e.g., changing exception classes mid-way).

### Decision

Establish a mandatory development lifecycle requiring the generation, review, and freezing of an Architecture Design Specification (ADS) *before* writing any subsystem production code.

### Consequences

* **Reduced Refactoring**: Structural changes are debated in the blueprint phase, preventing wasted effort.
* **Stable Contracts**: Subsystem public interfaces, constants, and exceptions are established upfront, enabling parallel work on test suites and other layers.

---

# EDR-012

## Public Planner Facade

**Date:** 2 July 2026

### Context

Similar to previous subsystems, planning orchestration details, thresholds, and internal helpers must not be directly accessed by downstream components to avoid compile-time coupling.

### Decision

Establish the `Planner` class as the sole public facade of the planning subsystem. All execution recipe strategies and validations are orchestrated inside the facade. The package exports only `Planner`, `Plan`, `PlanStep`, `Action`, and base exceptions in `__init__.py`.

### Consequences

* **Boundary Separation**: Downstream layers (like the Brain Core) interact only with the `Planner.plan()` method.
* **Refactoring Independence**: Strategy patterns and validation formulas can be refactored privately without affecting callers.

---

# EDR-013

## Strategy-Based Planning Architecture

**Date:** 2 July 2026

### Context

Different planning techniques (e.g., rule-based heuristic generation, machine learning execution mappings, LLM prompts) should be swap-compatible without changing the main orchestrator flow.

### Decision

Implement planning strategies using a stateless Strategy Pattern backed by an Abstract Base Class (`Strategy(ABC)`). The `Planner` selects the active strategy (such as `DefaultStrategy` or `FallbackStrategy`) and delegates plan steps generation to its abstract method `build_steps()`.

### Consequences

* **Subsystem Extensibility**: Third-party developers can write custom strategies by subclassing `Strategy` and injecting them into the `Planner` constructor.
* **Isolated Testing**: Mocks of the Strategy interface can be injected in tests to isolate the facade's exception handling and validation pipeline.

---

# EDR-014

## Separation of Planning from Execution

**Date:** 2 July 2026

### Context

Execution state (such as progress indicators, step execution statuses, retry counts) is dynamic and OS-dependent. Mixing it with recipe generation violates the Single Responsibility Principle.

### Decision

Decouple execution state completely from the Planning subsystem. `Plan` and `PlanStep` remain pure data transfer objects representing *instructions* rather than progress. Running and tracking actions is delegated to the future Execution subsystem.

### Consequences

* **Subsystem Purity**: The Planner remains stateless and deterministic.
* **Model Lightness**: Dataclass slots prevent dynamic runtime footprint bloat, keeping recipes lightweight and serializable.

---

# EDR-015

## Confidence-Driven Planning Paths

**Date:** 2 July 2026

### Context

Subsystems must fail safely when the parser is unsure of intent, and require user permission for risky actions that fall in low-confidence ranges.

### Decision

Implement three execution paths in `Planner` based on the parsed request confidence:
1. **Normal Path (Confidence >= 0.80)**: Builds steps directly, with `requires_confirmation = False`.
2. **Confirmation Path (0.60 <= Confidence < 0.80)**: Builds steps directly, but flags `requires_confirmation = True` to mandate user consent.
3. **Clarification Path (Confidence < 0.60 or UNKNOWN intent)**: Invokes `FallbackStrategy` to schedule a single `Action.ASK_CLARIFICATION` step.

### Consequences

* **Safe Degradation**: Prevents dangerous execution on ambiguous text commands.
* **Interactivity**: Clean signaling allows downstream executors to cleanly prompt user approval.

---

# EDR-016

## Execution Aggregator Pattern

**Date:** 2 July 2026

### Context

Coordinating the step-by-step execution pipeline and compiling individual step outcomes into a final status DTO are separate responsibilities. Combining them inside the orchestrator engine violates the Single Responsibility Principle.

### Decision

Introduce a stateless `ExecutionAggregator` component. The `ExecutionEngine` is responsible exclusively for plan validation, orchestration, and sequential routing of step runs. The `ExecutionAggregator` receives the list of completed `StepResult` objects and compiles the final aggregated status.

### Consequences

* **Orchestrator Simplicity**: Keeps `ExecutionEngine` clean of result math and outcome logic.
* **Granular Assertions**: Aggregator logic can be unit tested in isolation with mock step success vectors.

---

# EDR-017

## Registry-Based Action Router

**Date:** 2 July 2026

### Context

Hardcoding execution routing tables using `if/elif` or `match` blocks inside the engine facade creates tightly coupled dependencies and prevents dynamic subsystem extensions.

### Decision

Implement the `ActionRouter` utilizing a registry mapping model. Executors must subclass the standard `ActionExecutor` interface and register themselves via `ActionRouter.register(action, executor)`. The router performs resolution using an internal dictionary rather than conditional logic.

### Consequences

* **Clean Routing**: Completely eliminates branching structures inside the engine orchestrator.
* **Plugin Extensibility**: Enables registering custom executors dynamically at runtime.

---

# EDR-018

## Execution Status Enumeration

**Date:** 2 July 2026

### Context

Plan executions can succeed partially, where some steps complete but others fail. Representing outcomes with a binary boolean success flag prevents granular execution reporting.

### Decision

Introduce the `ExecutionStatus` StrEnum containing values: `SUCCESS` (all steps succeeded), `FAILED` (all steps failed), and `PARTIAL_SUCCESS` (mixed step results). `ExecutionResult` exposes a `status` field utilizing this enum.

### Consequences

* **Rich Reporting**: Downstream cognitive layers can identify exactly when a multi-step command fails partially and trigger targeted retries or compensation actions.
* **Predictable outcome DTO**: Simplifies diagnostic checks for downstream planners.

---

# EDR-019

## Mock Execution First Strategy

**Date:** 2 July 2026

### Context

Accessing actual OS commands, filesystems, and networks during the early development stages presents security risks, makes pipeline states unstable, and introduces non-deterministic environment dependencies.

### Decision

Restrict Version 1 of the Execution subsystem to simulated mock runs only. No system calls or filesystem modifications are permitted. Concrete executors return deterministic `StepResult` objects simulating completion details based on parameter checks.

### Consequences

* **Perfect Testability**: Automated unit tests execute instantly in any environment with zero side effects.
* **Platform Security**: Core execution routing logic is finalized and reviewed before introducing dangerous OS permissions.

---

# EDR-020

## Execution Plugin Architecture

**Date:** 2 July 2026

### Context

Adding new capabilities (e.g. running browser automation, database queries, container operations) should not require refactoring the core execution engine code.

### Decision

Establish the subsystem around the `ActionExecutor` interface and the registry-based `ActionRouter`. Developers add capabilities by subclassing `ActionExecutor` and calling `ActionRouter.register()` with the new `Action` type.

### Consequences

* **Open-Closed Principle**: Core execution engine classes are closed to modifications but open to dynamic capability expansions.
* **Plugin Isolation**: Third-party plugins remain completely isolated in their execution modules, minimizing regression risks.

---

# EDR-021

## Cognitive Lifecycle & Single State Model

**Date:** 2 July 2026

### Context

Transforming ARGOS from a linear request-response processing pipeline into an active Cognitive Operating System requires an explicit lifecycle model. Mixing execution state with cognitive reasoning phases causes ambiguity in session telemetry.

### Decision

Model the Brain Core around an explicit Cognitive Loop: `Perceive` -> `Understand` -> `Reason` -> `Decide` -> `Act` -> `Observe` -> `Reflect` -> `Terminate/Repeat`. Internal cognitive phases are explicitly tracked via `CognitiveState` (`IDLE`, `PERCEIVING`, `INTERPRETING`, `REASONING`, `PLANNING`, `EXECUTING`, `EVALUATING`, `WAITING_FOR_USER`, `COMPLETED`, `FAILED`, `TERMINATED`). Public session outcomes are summarized by `BrainStatus`.

### Consequences

* **Unambiguous Cognition**: Downstream telemetry can observe exactly which cognitive stage the Brain occupies at any moment.
* **Separation of Concerns**: High-level cognitive state is cleanly separated from low-level execution step progress.

---

# EDR-022

## Pluggable Cognitive Capabilities

**Date:** 2 July 2026

### Context

Hardcoding lower-level subsystem interactions (input processing, intent parsing, planning, execution) inside the Brain Core tightly couples cognition to mechanical details and violates the Open-Closed Principle.

### Decision

Treat existing and future subsystems as pluggable `CognitiveCapability` instances managed by a `CapabilityManager`. Standard adapters wrap `InputProcessor`, `IntentAnalyzer`, `Planner`, and `ExecutionEngine` without modifying their public contracts. Subsystem exceptions are intercepted and wrapped into `ProcessingError` at the capability boundary.

### Consequences

* **Decoupled Architecture**: Subsystems can be swapped, mocked, or upgraded to neural providers without altering the Brain Core reasoning loop.
* **Boundary Integrity**: Low-level exceptions do not leak across capability boundaries.

---

# EDR-023

## Transient Working Memory & Lightweight Observation Feedback

**Date:** 2 July 2026

### Context

The Brain Core requires short-term context during loop iterations without depending on persistent long-term storage or vector databases. Furthermore, cognition must not terminate immediately upon action execution without observing outcomes.

### Decision

Introduce a transient `WorkingMemory` container owned by the Brain for intra-session state (goals, parameters, intermediate DTOs, decision logs) that resets between requests. Pair it with a lightweight `Observer` that receives capability outputs, updates working memory, and signals discrepancies (e.g. execution failures or partial completions) back to the reasoning loop.

### Consequences

* **Zero Memory Leakage**: Transient context remains lightweight and cleanly scoped to individual sessions.
* **Closed Cognitive Loop**: Observation and reflection allow the Brain to evaluate actual vs. expected results rather than operating blindly.

---

# EDR-024

## Dual-Store Memory Architecture

**Date:** 2 July 2026

**Status:** Approved (Frozen)

### Context

With the completion and freezing of ADS-001 through ADS-005, ARGOS possesses a complete cognitive reasoning loop and transient working memory. However, `WorkingMemory` resets at the beginning of each request. ARGOS is currently amnesic across requests: it has no mechanism to retain multi-turn conversational context, store persistent user preferences, or remember past decisions.

The ARGOS Constitution (Article IV) establishes: *"User information belongs to the user... Long-term memory should be intentional, reviewable, and manageable by the user. An AI system that records everything without consent violates human dignity."*

Furthermore, `ARCHITECTURE.md` (Section 7) and `MVP.md` (Section 3) specify a multi-tiered memory architecture consisting of Working Memory, Session Memory, and Long-Term Memory with Memory Consent.

### Problem

How should memory beyond transient Working Memory be architected, scoped, stored, and integrated into ARGOS while preserving:
1. Deterministic V1 behavior (no non-deterministic vector retrieval or probabilistic hallucinations).
2. Constitutional privacy and human consent ("Remember with permission").
3. Loose coupling and dependency inversion (Brain Core must remain independent of concrete storage mechanisms).
4. Robust transactional integrity, crash resilience, and high reliability without introducing external cloud or third-party dependencies.

### Options Considered

1. **Monolithic Schema-Validated JSON File:**
   Store all session context and long-term memories in a single local JSON file.
   * *Pros:* Human-readable, simple to inspect with standard text editors.
   * *Cons:* Lacks atomic commits; process interruption during writes can lead to file corruption; poor query performance; concurrency conflicts; requires reading and rewriting the entire file for every update.

2. **Vector Database / Embedding Engine (e.g., Chroma, FAISS, Qdrant):**
   Store semantic memories as high-dimensional vector embeddings for similarity search.
   * *Pros:* Fuzzy semantic retrieval.
   * *Cons:* Violates the deterministic V1 mandate; introduces heavy external dependencies; requires an embedding model; non-deterministic retrieval contradicts predictable OS-level behavior.

3. **Dual-Store Architecture (In-Memory Session Cache + Local SQLite Persistent Store with Consent Gateway):**
   Split memory into two decoupled tiers:
   * *Session Store:* Fast in-memory turn-based history for multi-turn conversational continuity within an active session.
   * *Persistent Semantic Store:* Transactionally sound, local SQLite database for durable user preferences, system configurations, and explicit declarative facts.
   * *Consent Gateway:* Dedicated validation component requiring explicit user authorization before committing persistent memories.

### Decision

Adopt **Option 3: Dual-Store Memory Architecture** for ADS-006 and Version 1 of ARGOS.

#### 1. Memory Taxonomy & V1 Boundaries
* **Working Memory (Internal to `argos.brain`):** Transient intra-cycle scratchpad holding active DTOs and loop state. Resets every request. Owned exclusively by Brain Core (ADS-005).
* **Session Memory (Transient Multi-Turn):** In-memory deterministic FIFO turn cache retaining recent conversational interactions, dialogue history, and recent entity bindings within an active session. Discarded when the session terminates.
* **Persistent Semantic Memory (Durable Local Storage):** Durable on-disk factual store for user preferences, environmental configurations, and explicit declarative knowledge that survives restarts.
* **Deferred Memory Types:** Episodic event graphs (detailed longitudinal execution logs), Procedural memory (learned automation skills), and Vector/Embedding memory are **explicitly deferred** to post-V1 milestones.

#### 2. Storage Architecture: SQLite
Persistent semantic memory shall use **SQLite** via the Python standard library `sqlite3` module.
* **Transactional Integrity & Atomic Commits:** Provides ACID guarantees through write-ahead logging or rollback journals. Writes either fully commit or cleanly roll back, ensuring crash resilience and controlled failure behavior without claiming absolute physical immunity from disk corruption.
* **Single Local File:** Stored exclusively in local application data (e.g., `~/.argos/memory.db`).
* **Zero Dependencies:** Pure Python standard library with no external packages.
* **Indexing & Evolution:** Provides indexed exact-match queries (by key, category, and entity) and standard SQL schema migration paths.
* **Privacy:** 100% local, offline, inspectable, and exportable.

#### 3. Session Identification Model
Session memory shall be identified via a **Single Default Session with Optional Explicit `session_id`**.
* Default: `session_id = "default"`.
* API signatures accept `session_id: str = DEFAULT_SESSION_ID`.
* Satisfies V1 single-user CLI needs without blocking future multi-window or multi-session interfaces.

#### 4. Memory Consent vs. General Policy Boundary
In strict adherence to Constitution Article IV ("Remember with permission"):
* **Read Operations:** Non-destructive; executed automatically when relevant context is needed.
* **Session Memory Writes:** Permitted automatically within the active session lifecycle for conversational continuity.
* **Persistent Memory Operations (Writes, Updates, Deletions):** Require explicit memory-specific authorization.
* **Consent vs. Policy Engine Distinction:**
  * Memory Consent is a **constitutional, memory-specific authorization mechanism** governed by Article IV.
  * ADS-006 may validate whether valid authorization exists (e.g., via one-time user consent or established authorization metadata).
  * ADS-006 does **NOT** define or implement the broader ARGOS Policy Engine.
  * The future Policy Engine (`argos.policy`) owns generalized system policies, governance rules, and cross-subsystem rule evaluation. Memory must **not** become a hidden policy engine.
* **Cognitive State Integration:** Memory consent requests shall **reuse the existing `CognitiveState.WAITING_FOR_USER`** and `BrainStatus.WAITING_FOR_USER` states in Brain Core. No competing or redundant cognitive state shall be introduced.

#### 5. Separation of Responsibilities & Ownership
* **Brain Core (`argos.brain`):** Owns cognitive reasoning. Decides *when* memory retrieval is useful (during `Reason` phase); decides *when* information should be proposed for retention (during `Reflect` phase); participates in the cognitive consent flow (driving state transitions like `WAITING_FOR_USER`).
* **Memory Subsystem (`argos.memory`):** Subordinate capability. Responsible for storage, schema validation, index retrieval, enforcing memory-specific authorization constraints, inspection, updates, and deletion.
* **Policy Engine (`argos.policy` — Future):** Owns generalized policies and system governance.
* **Non-Responsibilities:** Memory does NOT reason, plan, execute commands, autonomously decide user intent, or evaluate general system policies.

#### 6. Privacy & Boundary Rules
* **Local-Only:** Persistent databases must never sync to external networks or cloud services in V1.
* **Logging Isolation:** Sensitive user preferences, memory values, and personal facts must NEVER appear in logs at `INFO` level.
* **Raw Text Protection:** Raw user input prompts are not stored verbatim in persistent memory; only structured, approved key-value facts and preferences extracted with consent.
* **Transparency:** Memory provides explicit APIs to inspect, export, and explicitly delete stored records.

#### 7. Brain Integration via Capability Adapter
* `argos.memory` shall be built as an independent, fully self-contained package.
* Integration with `argos.brain` shall occur strictly through the existing `CognitiveCapability(ABC)` abstraction via a `MemoryCapability` adapter registered in `CapabilityManager`.
* `BrainCore` remains decoupled from concrete SQLite or storage details, preserving 100% dependency inversion.

#### 8. Data Model Principles
EDR-024 defines architectural requirements and invariants; concrete DTO schemas, serialization protocols, and database tables are left to ADS-006. Architectural principles:
* **Identity:** Deterministic or UUID string identifier.
* **Scope:** Explicit scope demarcation (`SESSION` vs `PERSISTENT`).
* **Category & Key:** Indexed categorical and key identifiers (e.g., `preference`, `fact`, `system`).
* **Value:** Structured, serializable value payload.
* **Provenance & Timestamps:** UTC creation/update timestamps and origin tracking (`source`).
* **Authorization Provenance:** Metadata must be sufficient to establish authorization provenance (e.g., consent status, authorization source, timestamp) without prematurely locking the representation to a simple boolean if a richer model is architecturally warranted in ADS-006.
* **Table Design:** Concrete SQL tables, column types, and indices belong to ADS-006, not this EDR.

#### 9. Retention & Deletion Policy
* Session Memory enforces a deterministic FIFO capacity ceiling (e.g., maximum 50 turns).
* Persistent Memory retains entries indefinitely until explicitly modified or deleted by the user.
* Heuristic eviction, probabilistic forgetting, automated pruning, and decay algorithms are **explicitly excluded from V1**.

#### 10. Failure Semantics & Graceful Degradation
Memory failures are not treated as equivalent; behavior is categorized by operation:
* **A. Memory Retrieval Failure:** Optional retrieval failure may degrade gracefully. If retrieval experiences transient lock contention or temporary unavailability, `MemoryCapability` logs a warning at `DEBUG` level and returns empty context; `BrainCore` continues reasoning using raw input alone without cognitive state corruption.
* **B. Persistent Memory Write Failure:** Failed persistent writes must **never** be reported as successful. If storage write fails, the error must remain observable, working memory must record the failure in decision logs, and an explicit failure outcome is reported.
* **C. Persistent Memory Update Failure:** Failed updates must **never** silently disappear or leave partially updated state. Transactions must cleanly roll back, maintaining data consistency.
* **D. Persistent Memory Deletion Failure:** Failed deletions must remain observable, accurately reporting that data remains intact rather than falsely confirming removal.
* **E. Storage Corruption / Unrecoverable Failure:** If the database file suffers confirmed corruption or unrecoverable failure, storage failures must **never** be silently converted into empty context; `MemoryStorageError` is raised and wrapped as `ProcessingError` at the capability boundary.
* **F. Consent Denial:** User denial of consent is not a system failure, but a valid human choice. The commit is aborted, the refusal is recorded in working memory decision logs, and cognition completes with a consistent terminal status.

### Rationale

This dual-store architecture cleanly separates ephemeral multi-turn conversational state from durable long-term facts. Utilizing Python's built-in SQLite engine provides transactional integrity, atomic commits, crash resilience, and zero external dependencies while respecting the user's local privacy. Reusing `WAITING_FOR_USER` reinforces the principle that user consent is a first-class cognitive pause rather than an ad-hoc callback.

### Consequences

#### Positive:
* **Constitutional Compliance:** Implements Article IV's "Memory with Permission" mandate before any personal user data is collected.
* **Contextual Continuity:** Enables multi-turn conversations and personalized planning based on recalled preferences.
* **Zero External Dependencies:** Built entirely on Python 3.13+ standard library (`sqlite3`, `dataclasses`).
* **Architectural Preservation:** Preserves existing ADS-001 through ADS-005 contracts without breaking changes.

#### Negative / Constraints:
* **No Fuzzy Matching in V1:** Retrieval is limited to exact keys, categories, and tags; unstructured semantic similarity search is deferred.
* **Storage Overhead:** Introduces disk I/O management, crash recovery, and schema migration responsibilities into the test suite.

### Rejected Alternatives

* **Flat JSON Files:** Rejected due to non-atomic writes, lack of transactional integrity, concurrency race conditions, and vulnerability to file corruption during process interruption.
* **Cloud / Third-Party Vector DBs:** Rejected due to network requirements, vendor lock-in, non-deterministic retrieval, and privacy violations.
* **Unified Single Store:** Rejected because transient conversational dialogue turns and permanent user preferences have fundamentally different lifecycles, scopes, and consent requirements.

### Dependencies

* **Upstream:** Python standard library (`sqlite3`), `argos.brain.capability_manager.CognitiveCapability`.
* **Downstream:** `argos.policy` (future Policy Engine will read rules stored in Semantic Memory).

### Future Revisit Conditions

* Revisit when local neural models or embeddings are introduced, allowing deterministic exact-match retrieval to be augmented with local vector similarity search.
* Revisit when multi-agent collaboration or distributed daemon services require multi-tenant memory synchronization.
* Revisit when healthy forgetting and automated memory compaction algorithms are formally scheduled.

---

# EDR-025

## Deterministic Layered Policy Engine Architecture

**Date:** 3 September 2026

**Status:** Approved (Frozen)

### Context

Following the completion and freezing of ADS-001 through ADS-006 v1.1, ARGOS possesses complete request perception, semantic intent analysis, plan recipe compilation, step execution, cognitive loop orchestration (`BrainCore`), and multi-tier memory storage (`MemoryEngine`).

However, prior to ADS-007, safety checks, confirmation requirements, and security boundaries were hardcoded, fragmented across capability modules, or inferred heuristically inside `Planner` or `DecisionEngine`. As ARGOS prepares to support real OS hardware execution (file operations, terminal commands, web sockets, external application tools) and neural LLM reasoning providers, relying on implicit or fragmented safety checks introduces critical risks of capability bypass, non-deterministic safety failures, or prompt injection exploits.

Article I (Human First), Article V (Safety), and Article XIV (User Policies) of the ARGOS Constitution require that irreversible or high-impact actions mandate explicit confirmation, and that user-defined policies govern repetitive operations without compromising immutable safety.

### Decision

Adopt a **Deterministic Layered Policy Engine Architecture** for ADS-007 and Version 1 of ARGOS.

#### 1. Architecture Triad & Separation of Concerns
* **DecisionEngine (`argos.brain`):** Reasoning evaluator answering *"What capability/step should cognition execute next?"*
* **PolicyEngine (`argos.policy`):** Governance evaluator answering *"Is the proposed capability/action allowed under applicable system and user policies, and under what conditions?"*
* **Capability / Executor (`argos.execution`):** Mechanical execution component answering *"How is the operation performed?"*

#### 2. Layered Enforcement Gateways (Infallible Governance)
* **Layer 1 (Primary Gateway):** `CapabilityManager` evaluates `PolicyEngine.evaluate_capability(name, action, kwargs)` before dispatching to any `CognitiveCapability`. Every registered capability passes through Layer 1.
* **Layer 2 (Tool Execution Gateway):** `ExecutionEngine` / `ActionRouter` evaluates `PolicyEngine.evaluate_action(action, target, params)` before executing low-level system side-effects (terminal commands, file paths, web URLs).
* **Bypass Invariant:** No capability or tool can bypass policy evaluation.

#### 3. Domain Model & Outcome Semantics
* `PolicyOutcome` defines 4 public outcome states: `ALLOW` (Rank 1), `REQUIRE_CONFIRMATION` (Rank 2), `REQUIRE_AUTHORIZATION` (Rank 3), `DENY` (Rank 4).
* Internal conflict resolution uses **Deny-Override** and **Specificity-Override** algorithms to produce deterministic outcomes. Public `CONFLICT` is explicitly excluded.

#### 4. Absolute Scope Precedence Hierarchy
$$\text{CONSTITUTION} \gt \text{SYSTEM\_IMMUTABLE} \gt \text{SYSTEM\_SECURITY} \gt \text{USER\_POLICY} \gt \text{CONTEXTUAL} \gt \text{DEFAULT\_FALLBACK}$$
* Constitutional principles (Articles I, IV, V) and hardcoded system prohibitions (`SYSTEM_IMMUTABLE`) cannot be overridden by user policies, database edits, or LLM proposals.

#### 5. Fail-Closed Semantics
* Policy evaluation is 100% deterministic, side-effect free, and thread-safe.
* Evaluation errors, malformed user rules, or missing parameters **NEVER** fail open to `ALLOW`; they default deterministically to `DENY` or `REQUIRE_CONFIRMATION`.

#### 6. Restricted Declarative Representation (Anti-Arbitrary Code Execution)
* Policy rules rely strictly on static text patterns, target actions, and structured `RuleOperator` enums (`EQUALS`, `CONTAINS`, `PREFIX_MATCH`, `REGEX_MATCH`, etc.).
* Dynamic code evaluation (`eval()`), untrusted Python callbacks, or executable policy payloads from database or user inputs are strictly prohibited.

#### 7. Memory & Consent Boundary Insulation
* User-defined policy rules are persistent declarative data stored in `ADS-006 PersistentStore` under `category="policy_rule"`.
* `PolicyEngine.reload_user_rules()` populates an in-memory rule snapshot cache at startup without triggering recursive policy evaluations on the startup read itself.
* `ConsentManager` (ADS-006) remains the exclusive authority for Article IV constitutional user consent for persistent memory storage. `PolicyEngine` checks policy rules *before* `ConsentManager` checks explicit human consent.

#### 8. Monotonic Confirmation Composition
* Confirmation requirements between `DecisionEngine` and `PolicyEngine` are cumulative and monotonic. If *either* engine requests user confirmation, `BrainCore` transitions to `WAITING_FOR_USER`. Neither engine can override or cancel a confirmation requested by the other. `PolicyEngine.DENY` overrides any execution-ready proposal.

### Consequences

#### Positive:
* **Bypass-Proof Safety:** Layered policy gateways guarantee 100% governance coverage across all capabilities and OS tools.
* **Neural LLM Protection:** Neural LLM proposal engines cannot bypass safety prohibitions or self-grant elevated privileges.
* **Zero External Dependencies:** Built entirely on Python standard library (`dataclasses`, `enum`, `datetime`, `re`).
* **Architectural Preservation:** Preserves existing ADS-001 through ADS-006 contracts with zero breaking changes.

#### Negative / Constraints:
* **Storage Overhead:** Requires caching user policy rules loaded from `MemoryEngine`.
* **Layered Evaluation Latency:** Introduces lightweight in-memory rule evaluation steps at capability and tool dispatch boundaries.

---


# Founder's Pact

**Date:** 26 June 2026

Founder and Technical Mentor agreed on the following principle:

> Architecture shall never be sacrificed for short-term progress.

Temporary prototypes may simplify implementation.

The long-term architecture shall remain protected.

---

# Open Decisions

The following topics remain intentionally undecided:

* Healthy forgetting
* Memory retention durations
* Emotional intelligence architecture
* Local model strategy
* Plugin security model

These decisions will be revisited as the architecture matures.

---

# Review Process

Engineering Decision Records are living records.

Existing decisions should not be silently modified.

When architecture changes significantly:

* Create a new EDR, or
* Supersede an existing EDR with documented reasoning.

The engineering history of ARGOS should remain traceable throughout the life of the project.

