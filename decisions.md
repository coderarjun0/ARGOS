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

