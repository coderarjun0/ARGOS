# ADS-009 — Capability Ecosystem & Domain Registry Specification

**Subsystem:** Capability Ecosystem & Domain Registry (`src/argos/capabilities/`)  
**Version:** 1.0.0  
**Status:** Approved & Frozen  
**Target Release:** v0.10.0-alpha (ARS-003)  
**Baseline:** ARS-002 v0.9.0-alpha (Commit `903d65e`), ARS-003 Revision 0.2.2-alpha  

---

## 1. Overview

ADS-009 defines the formal architecture, interfaces, DTOs, and contracts of the **ARGOS Capability Ecosystem & Domain Registry** (`src/argos/capabilities/`). This subsystem provides a modular, domain-grouped metadata discovery layer exposing real tool capability schemas to the cognitive planner (`ADS-003 / ADS-005`) without exposing implementation-specific Python objects (`BaseTool` instances, `PlatformAdapter` instances, or OS binary paths).

ADS-009 establishes `ToolManifest` as the single source of truth for metadata, preserves `ParameterSpec` ownership in `src/argos/tools/base_tool.py`, maintains `BrainCore` as the sole cognitive orchestrator, preserves `PolicyEngine` as the sole governance decision authority, maintains `ActionRouter` as the single-path execution router, and enforces strict composition-root registry ownership.

---

## 2. Subsystem Architecture

```text
[ArgosRuntime Composition Root]
            │  Populates Registries at Startup
            ├──► [ToolRegistry] (Indexes BaseTool Instances for ActionRouter)
            └──► [CapabilityRegistry] (Indexes ToolManifest Metadata for Planner)

[BrainCore / Planner Subsystem (ADS-003 / ADS-005)]
            │  Queries Abstract Action Schemas for Plan Generation
            ▼
   [CapabilityRegistry] (Metadata Discovery Layer - ADS-009)
            │  Returns Abstract DTOs (ActionSchemaDescriptor)
            ▼
[Planner Output: PlanStep(Action, parameters)]
            │
            ▼
[PolicyEngine Layer 1 & Layer 2 Gates (ADS-007)]
            │  Evaluates Governance Rules
            ▼
[ActionRouter -> ToolExecutorAdapter -> BaseTool -> PlatformAdapter (ADS-004 / ADS-008)]
```

---

## 3. CognitiveCapability vs CapabilityDomain Boundary

ADS-009 maintains absolute separation between subsystem cognitive capabilities and tool capability domains:

```text
[BrainCore]
    └── [CapabilityManager]  <-- Manages 6 Cognitive Capabilities (ADS-005)
           ├── InputCapability (ADS-001)
           ├── IntentCapability (ADS-002)
           ├── PlanningCapability (ADS-003)
           ├── ExecutionCapability (ADS-004)
           ├── MemoryCapability (ADS-006)
           └── PolicyCapability (ADS-007)

[ExecutionCapability / Tool Runtime]
    └── [CapabilityRegistry]  <-- Organizational Metadata Groupings for Tools (ADS-009)
           ├── ApplicationDomain    (ApplicationLauncherTool)
           ├── FileSystemDomain     (FileReadTool, DirectoryListTool)
           ├── SystemInfoDomain     (SystemInfoTool)
           └── WebDomain            (WebSearchTool)
```

### Boundary Invariants
1. `CapabilityManager` (ADS-005) manages the **6 Cognitive Capabilities** required to run the cognitive cycle.
2. `CapabilityRegistry` (ADS-009) manages **tool metadata discovery DTOs** used by `Planner`.
3. `CapabilityRegistry` **CANNOT** evaluate policy, execute steps, or replace `CapabilityManager`.

---

## 4. Single Source of Truth & Registry Architecture

### A. Manifest as Single Source of Truth
`ToolManifest` is the **single authoritative source of truth** for all tool metadata, supported actions, risk classifications, and parameter specifications (`ParameterSpec`). `ParameterSpec` is declared canonically in `src/argos/tools/base_tool.py`. `CapabilityRegistry` indexes `ToolManifest` metadata directly; it does **NOT** maintain duplicate parameter schemas, ensuring zero schema drift.

### B. Composition Root Ownership & Registration Lifecycle
Tools and registries are populated exclusively during Composition Root setup (`ArgosRuntime.create_default()`):
1. Composition Root instantiates trusted `BaseTool` instances.
2. Registers tools in `ToolRegistry`.
3. Registers domains and indexes `ToolManifest` metadata in `CapabilityRegistry`.
4. Calls `capability_registry.freeze()` to lock the registry against post-initialization mutation.
5. Binds `ToolExecutorAdapter` instances into `ActionRouter`.

Unsafe filesystem auto-scanning, dynamic module imports, and arbitrary plugin auto-loading are strictly prohibited.

---

## 5. Discovery DTO Contracts

All discovery DTOs exposed to `Planner` and `BrainCore` are strictly typed, immutable dataclasses:

```python
@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """Specification contract for a tool parameter (Declared in src/argos/tools/base_tool.py)."""
    name: str
    param_type: type
    required: bool = True
    default: Any = None
    allowed_values: tuple[Any, ...] | None = None


@dataclass(frozen=True, slots=True)
class ActionSchemaDescriptor:
    """Abstract descriptor exposing an action's parameter schema for discovery."""
    action: Action
    tool_id: str
    risk_class: RiskClass
    parameters: tuple[ParameterSpec, ...]


@dataclass(frozen=True, slots=True)
class DomainDescriptor:
    """Abstract descriptor exposing domain discovery metadata."""
    domain_id: str
    name: str
    description: str
    supported_actions: tuple[Action, ...]


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """Abstract descriptor exposing tool discovery metadata."""
    tool_id: str
    version: str
    description: str
    supported_actions: tuple[Action, ...]
    risk_class: RiskClass
```

---

## 6. Discovery & Ambiguity Handling Contracts

```python
class CapabilityRegistry:
    """Discovery registry indexing tool manifests and capability domains."""

    def __init__(self) -> None: ...
    def register_domain(self, domain: CapabilityDomain) -> None: ...
    def index_tool(self, tool: BaseTool) -> None: ...
    def freeze(self) -> None: ...

    # Read-Only Discovery Interfaces
    def list_domains(self) -> tuple[DomainDescriptor, ...]: ...
    def get_domain(self, domain_id: str) -> DomainDescriptor: ...
    def get_action_schemas(self) -> tuple[ActionSchemaDescriptor, ...]: ...
    def get_schema_for_action(self, action: Action) -> ActionSchemaDescriptor: ...
```

### Deterministic Resolution & Ambiguity Rules
1. **Deterministic Ordering**: Discovery queries returning tuples sort descriptors lexicographically by `domain_id` or `action.value`.
2. **Deterministic ActionRouter Binding**: Exactly **one active execution binding per `Action` enum** exists within `ActionRouter`.
3. **Explicit `AmbiguousActionError`**:
   - `0 matching tools` $\rightarrow$ raises `ActionNotFoundError`
   - `1 matching tool` $\rightarrow$ returns its `ActionSchemaDescriptor`
   - `>1 matching tools` $\rightarrow$ raises `AmbiguousActionError` (forces `Planner` to inspect `get_action_schemas()`).

---

## 7. Security Invariants & Policy Integration

1. **Reserved `_risk_class` Parameter**: `_risk_class` is an ARGOS-internal reserved policy parameter injected by `ToolExecutorAdapter` immediately prior to `PolicyEngine.evaluate_action()`. `BaseTool.validate_parameters()` rejects any parameter payload containing keys prefixed with `_`.
2. **Canonical Sandbox Root Ownership**: `sandbox_root` is trusted runtime configuration established at Composition Root. `sandbox_root` MUST exist and be a directory. Both `sandbox_root` and target paths are resolved canonically (`.resolve()`) before containment checks (`is_relative_to()`) to eliminate symlink escapes. Nonexistent target paths resolve their parent directory canonically prior to containment verification.
3. **Sole Governance Authority**: `RiskClass` is operational metadata. `PolicyEngine` alone decides `ALLOW`, `DENY`, `REQUIRE_CONFIRMATION`, or `REQUIRE_AUTHORIZATION`.
4. **Untrusted LLM Boundary**: Neural LLMs act strictly as proposal generators. LLMs cannot execute tools, satisfy authorization contexts, or mutate registries.

---

## 8. Inviolable Architectural Invariants

1. `BrainCore` remains the sole cognitive center.
2. `CapabilityRegistry` metadata discovery does NOT execute steps or replace `CapabilityManager`.
3. `ToolManifest` is the single authoritative source of truth for tool metadata and schemas; `ParameterSpec` is owned canonically in `src/argos/tools/base_tool.py`.
4. Execution routing is 100% deterministic (exactly one active execution binding per `Action` in `ActionRouter`).
5. Registry population is owned 100% by the Composition Root; no dynamic auto-scanning.
6. `_risk_class` is an ARGOS-controlled reserved parameter rejected on external input.
7. `sandbox_root` is trusted, canonical runtime configuration injected at Composition Root; it MUST exist and be a directory. Symlink resolution MUST NOT escape `canonical_sandbox_root`.
8. `SystemInfoTool` queries host metrics through `BasePlatformAdapter.query_system_info()`.
9. `RiskClass` provides operational metadata; `PolicyEngine` alone decides policy outcomes.
10. Neural LLMs act strictly as proposal generators with zero execution authority.
11. Frozen ADS-001 through ADS-008 specifications remain 100% untouched.
