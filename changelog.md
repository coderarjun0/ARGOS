# Changelog

**Project:** ARGOS (Adaptive Reasoning & General Operating System)

**Document:** CHANGELOG.md

**Version:** 0.2

**Status:** Active

**Created:** 25 June 2026

**Last Updated:** 26 June 2026

**Maintainer:** Arjun Saini

---

# Purpose

This document records significant changes made throughout the development of ARGOS.

It serves as the official release history of the project and documents major architectural milestones, engineering progress, and platform evolution.

ARGOS follows Semantic Versioning with milestone codenames to represent each major phase of development.

---

# Version 0.1.0 — Genesis

**Release Date:** 25 June 2026

## Overview

The birth of Project ARGOS.

This release established the project's identity, vision, engineering philosophy, and documentation foundation.

## Added

### Project Foundation

- Project officially named **ARGOS**
- Vision and Mission established
- Project philosophy defined
- Repository structure created

### Documentation

- GitHub repository initialized
- Obsidian knowledge vault created
- Notion workspace established
- Initial README completed

### Engineering

- Documentation-first workflow adopted
- Multi-model development strategy selected
- Engineering Decision Record (EDR) system introduced
- EDR-001: Multi-Model Architecture completed

---

# Version 0.2.0 — Blueprint

**Release Date:** 26 June 2026

## Overview

Designed the complete high-level architecture of ARGOS.

This milestone transformed ARGOS from a concept into a structured Cognitive Operating System architecture.

## Added

### Governance

- ARGOS Constitution
- Founder's Pact

### Architecture

- Layered Architecture
- Modular Architecture
- Event-Driven Architecture
- Universal Request Lifecycle
- ARGOS Kernel

### Core Systems

- Brain Core
- Policy Engine
- Model Router
- Agent Orchestrator
- Event Bus
- State Manager
- Task Scheduler
- Capability Registry

### Memory System

- Working Memory
- Session Memory
- Long-Term Memory
- Knowledge Base
- Skills Library
- Archive
- Memory Consent concept

### Agent Architecture

- Permanent System Agents
- Dynamic Task Agents
- Tool vs Agent separation

### Documentation

- CONSTITUTION.md
- ARCHITECTURE.md
- DECISIONS.md
- ENGINEERING_LOG.md
- CHANGELOG.md

### Engineering Decisions

- EDR-002: Universal Reasoning Pipeline
- EDR-003: Layered Memory Architecture
- EDR-004: Hybrid Agent Architecture
- EDR-005: Layered Cognitive Architecture
- EDR-006: ARGOS Kernel
- EDR-007: Policy-Based Decision Making

---

# Version v0.1.0-alpha — Framework Implementations

**Release Date:** 28 June 2026

## Overview

First functional codebase release of ARGOS implementing the fundamental parsing framework. This release contains the production code for the Input Processing and Intent Analysis layers.

## Added

### ADS-001 — Input Processing Subsystem

* **InputProcessor**: Public facade coordinating the validation and parsing pipeline.
* **Normalizer**: Trims input, standardizes whitespace, and lowercases text.
* **Tokenizer**: Splits normalized text into word tokens on space boundaries.
* **Parser**: Maps processed data into final parsed requests.
* **Public API Boundary**: Encapsulates internal helpers, exporting only `InputProcessor`, `InputRequest`, `ParsedRequest`, and exceptions via package `__init__.py`.
* **100% Statement Coverage**: Comprehensive test suite consisting of 14 unit tests covering type safety, UTF-8 checks, and bounds validations.

### ADS-002 — Intent Analysis Subsystem

* **IntentAnalyzer**: Public facade class orchestrating semantic intent classification.
* **RuleEngine**: Matches keyword rules and patterns to determine primary intent and candidate alternatives.
* **EntityExtractor**: Parses normalized text and lists entities (application, file, folder, website, url, person, date, time, command).
* **ConfidenceEvaluator**: Estimates classification confidence scores using deterministic heuristic weighting.
* **IntentResult**: Output model storing intent, alternatives, confidence, and engine telemetry.
* **Public API Boundary**: Exports only facade, result models, enums, and exceptions, encapsulating rule engines and extractors.
* **100% Statement Coverage**: Comprehensive test suite of 21 tests covering clamping bounds, mock injections, and log privacy boundaries.

---

# Version v0.3.0-alpha — Planning Layer

**Release Date:** 2 July 2026

## Overview

Second codebase release of ARGOS implementing the Planning Layer subsystem (ADS-003). This subsystem parses user intent results into structured, ordered recipe steps ready for execution.

## Added

### ADS-003 — Planning Layer Subsystem

* **Planner**: Public facade coordinating type-validation, strategy selection based on confidence levels, and plan compilation.
* **Strategy Architecture**: Stateless Strategy abstract base class with concrete mappings:
  * **DefaultStrategy**: Maps standard intents and extracted entities directly to execution step parameters.
  * **FallbackStrategy**: Handles low-confidence or unknown intents by generating user clarification steps.
* **Plan**: Dataclass representing the final recipe container, including step list, telemetry tags, and verification flags.
* **PlanStep**: Dataclass representing a single action step containing sequence IDs and parameters. Extraneous execution state is decoupled.
* **Action StrEnum**: Definition of atomic commands (open, close, read, write, create, delete, web search, command run, and clarification).
* **26 Unit Tests**: Verifying DTO encapsulation, confirmation bounds, mock-based strategy injection, and logging privacy.
* **100% Statement Coverage**: Zero statement coverage gaps across the entire package.

---

# Version v0.4.0-alpha — Execution Layer

**Release Date:** 2 July 2026

## Overview

Third codebase release of ARGOS implementing the Execution Layer subsystem (ADS-004). This subsystem orchestrates step execution, routes commands to their respective mock executors, and aggregates outcome results.

## Added

### ADS-004 — Execution Subsystem

* **ExecutionEngine**: Public facade class orchestrating plan validations, steps limits verification, sequential execution, and compilation routing.
* **ActionRouter**: Registry-based routing table mapping action type enums directly to executors, supporting runtime registration for dynamic extensions.
* **ActionExecutor**: Abstract base class (`ActionExecutor(ABC)`) defining the standard execution protocol interface.
* **Concrete ActionExecutor Implementations**:
  * **ApplicationExecutor**: Simulated execution for opening and closing applications.
  * **FileExecutor**: Simulated execution for file creation, reading, writing, and deletion.
  * **WebExecutor**: Simulated execution for web search tasks.
  * **SystemExecutor**: Simulated execution for running system CLI terminal commands.
* **ExecutionAggregator**: Stateless aggregator compiling step-level results into overall statuses.
* **ExecutionStatus**: StrEnum representing overall plan outcomes (`SUCCESS`, `PARTIAL_SUCCESS`, `FAILED`).
* **DTO Models**:
  * **ExecutionResult**: Stores final compiled outcomes, step result lists, engine ID, and metadata.
  * **StepResult**: Stores execution success state, step ID, action type, and verification details.
* **25 Unit Tests**: Verifying DTO slot boundary safety, registry routing, execution status aggregation, message truncation, logging safety, and exception translation.
* **100% Code Coverage**: Comprehensive test coverage across all execution package modules.

---

# Version v0.5.0-alpha — Brain Core Subsystem

**Release Date:** 2 July 2026

## Overview

Fourth functional codebase release of ARGOS implementing the central cognitive hub (ADS-005). This release transforms ARGOS from a sequential processing pipeline into an active Cognitive Operating System driven by an explicit cognitive loop.

## Added

### ADS-005 — Brain Core Subsystem

* **BrainCore**: Public facade orchestrating the cognitive reasoning loop (`Perceive` -> `Understand` -> `Reason` -> `Decide` -> `Act` -> `Observe` -> `Reflect` -> `Terminate/Repeat`).
* **CognitiveState & BrainStatus**: Explicit StrEnums distinguishing transient internal cognitive phases from coarse session lifecycle outcomes.
* **WorkingMemory**: Transient cognitive state container managing active goals, intermediate DTOs, decision histories, and short-term context.
* **GoalManager**: Dedicated goal lifecycle coordinator supporting creation, prioritization, retrieval, completion, and cancellation.
* **DecisionEngine**: Pure reasoning component evaluating working memory to determine capability transitions, clarification needs, and user confirmation bounds.
* **CapabilityManager & Adapters**: Pluggable registry treating Input, Intent, Planning, and Execution subsystems as cognitive capabilities, intercepting subsystem errors and wrapping them at the capability boundary.
* **Observer**: Lightweight feedback tracker updating working memory and signaling discrepancies when execution deviates from expectations.
* **BrainResult**: DTO container compiled at loop termination, aggregating telemetry, decisions, and execution outcomes with `slots=True`.
* **29 Unit Tests**: Bringing the full repository suite to 114 tests.
* **100% Statement Coverage**: Preserving zero statement coverage gaps across all 1190 statements in `src/argos/`.

---

# Version v0.6.0-alpha — Memory System Subsystem

**Release Date:** 3 September 2026

## Overview

Fifth functional codebase release of ARGOS implementing the Memory System subsystem (ADS-006). This release equips ARGOS with multi-tier memory capabilities, supporting transient Session Memory, durable SQLite Persistent Semantic Memory, explicit user consent authorization, unified facade management via `MemoryEngine`, and seamless, capability-agnostic integration with `BrainCore`.

## Added

### ADS-006 — Memory System Subsystem

* **SessionStore**: In-memory, bounded FIFO turn store (`DEFAULT_MAX_SESSION_TURNS = 50`) providing transient multi-turn context without filesystem side-effects.
* **PersistentStore / SQLiteStore**: Standard-library SQLite storage backend supporting ACID-compliant atomic transactions, versioned key-category key-value persistence (`SCHEMA_VERSION = 1`), prefix searches, category listings, read-only inspection, and structured JSON exports.
* **ConsentManager**: Stateless authorization gateway validating explicit user consent (`EXPLICIT_USER_CONSENT`) prior to persistent semantic memory mutations. In V1, policy pre-authorization and system default authorization are strictly rejected to guarantee privacy and provenance integrity.
* **MemoryEngine**: Public facade orchestrating transient session state, persistent SQLite storage, and authorization validation with constructor-based dependency injection for in-memory test databases (`:memory:`).
* **MemoryCapability**: Cognitive capability adapter implementing `CognitiveCapability` interface with `CAPABILITY_MEMORY = "memory"`, enabling dynamic execution of session, persistent read, persistent mutation, and consent helper operations.
* **Brain Core Integration & Cognitive Capability Routing**: Integrated `MemoryCapability` into `BrainCore` and `CapabilityManager` with generic, capability-agnostic capability routing in `DecisionEngine` (`pending_capability`). Preserves automatic `SessionTurn` recording during reflection (`REFLECT`), explicit cognition-driven session recall during `REASONING`, and stateful two-step `WAITING_FOR_USER` consent pause and resumption.
* **214 Unit & Integration Tests**: Comprehensive test suite verifying zero memory storage side-effects during read-only ops, strict consent validation, bounded FIFO evictions, atomic SQLite mutations, generic capability selection, and two-step consent pause/resume workflows.
* **100% Statement Coverage**: Complete coverage across all 1,737 statements in `src/argos/` with zero Ruff linter errors.

---

# Upcoming Releases

## Version 0.5.0 — Foundation

**Planned**

- Stable core platform
- Modular plugin architecture
- Robust scheduling
- Improved reliability
- Core feature completion

---

## Version 0.5.0 — Foundation

**Planned**

- Stable core platform
- Modular plugin architecture
- Robust scheduling
- Improved reliability
- Core feature completion

---

## Version 1.0.0 — ARGOS

**Planned**

First complete public release of ARGOS as a Cognitive Operating System.

Expected characteristics:

- Mature architecture
- Stable APIs
- Production-ready documentation
- Fully integrated core modules
- Long-term extensibility

---

# Versioning Strategy

ARGOS follows Semantic Versioning.

### Major Version

Breaking architectural or platform changes.

Example:

```
1.0.0 → 2.0.0
```

---

### Minor Version

Major subsystem additions and platform capabilities.

Example:

```
0.2.0 → 0.3.0
```

---

### Patch Version

Documentation updates, bug fixes, optimizations, and minor improvements.

Example:

```
0.2.0 → 0.2.1
```

---

# Release Philosophy

ARGOS releases represent engineering milestones rather than arbitrary dates.

A release is considered complete only when:

- Documentation is updated
- Engineering decisions are recorded
- Architecture remains consistent
- Quality standards are maintained

---

# Notes

This changelog records only significant project milestones.

Daily engineering activities, discussions, and observations are recorded separately in **ENGINEERING_LOG.md**.
