# ADS-003 — Task Planning Subsystem & Schema-Aware Strategy Engine Specification

**Subsystem:** Task Planning (`src/argos/planning/`)  
**Version:** 1.0.0  
**Status:** Approved & Frozen  
**Target Release:** v0.11.0-alpha (ARS-004)  
**Baseline:** ARS-003 v0.10.0-alpha (Commit `fd3bf56`), ADS-009 v1.0.0  

---

## 1. Overview

ADS-003 defines the formal architecture, interfaces, DTOs, strategies, and validation contracts of the **ARGOS Task Planning Subsystem & Strategy Engine** (`src/argos/planning/`).

The Task Planning Subsystem consumes semantic intent data (`IntentResult` from `ADS-002`) and read-only capability discovery descriptors (`ActionSchemaDescriptor` from `ADS-009` `CapabilityRegistry`), validates intent parameters against authoritative `ParameterSpec` contracts (`ADS-008`), and dynamically generates policy-testable `Plan` sequences (`PlanStep`) without exposing live tool execution instances, platform adapters, or OS process handles.

ADS-003 establishes `Planner` strictly as an untrusted proposal generator, maintains `BrainCore` as the sole cognitive orchestrator, preserves `PolicyEngine` as the sole governance decision authority, maintains `ActionRouter` as the single-path execution router, and enforces explicit Composition Root dependency injection.

---

## 2. Subsystem Architecture & Boundary Invariants

```text
[IntentAnalyzer (ADS-002)]
            │  Produces Semantic DTO
            ▼
     [IntentResult]
            │
            ▼
[BrainCore / CapabilityManager (ADS-005)]
            │  Dispatches CAPABILITY_PLANNING
            ▼
[PlanningCapability / Planner (ADS-003 / ARS-004)]
            │  Queries Abstract Discovery Schemas
            ├──► [CapabilityRegistry (ADS-009)] (Reads ActionSchemaDescriptors)
            └──► [SchemaValidator (ADS-003)]     (Validates ParameterSpecs)
            │
            ▼
  [Plan Output: PlanStep(Action, parameters)]
            │
            ▼
[PolicyEngine Layer 1 & Layer 2 Gates (ADS-007)]
            │  Evaluates Policy Scopes & Risk Rules
            ▼
[ActionRouter -> ToolExecutorAdapter -> BaseTool -> PlatformAdapter (ADS-004 / ADS-008)]
```

### Boundary Invariants
1. **Proposal Generator Only**: `Planner` acts strictly as an untrusted proposal generator. `Planner` CANNOT execute steps, access live `BaseTool` instances, evaluate policy rules, or bypass `PolicyEngine`.
2. **Abstract Metadata Boundary**: `Planner` receives abstract `ActionSchemaDescriptor` DTOs (strings, enums, parameter types, risk ratings). `Planner` NEVER receives `BaseTool` instances, `PlatformAdapter` instances, OS process handles, or binary paths.
3. **Internal Parameter Protection**: `Planner` MUST NOT emit `_risk_class` or any `_`-prefixed keys in `PlanStep.parameters`. `_risk_class` remains strictly an internal policy parameter injected downstream by `ToolExecutorAdapter`.
4. **Informational Risk Ratings**: `RiskClass` on `ActionSchemaDescriptor` is read by `Planner` as informational metadata only. `PolicyEngine` remains the sole policy decision authority.

---

## 3. Dependency Boundary & Composition Root Ownership

`CapabilityRegistry` is injected into `Planner` via explicit constructor dependency injection:

```python
class Planner:
    def __init__(
        self,
        capability_registry: CapabilityRegistry | None = None,
        default_strategy: Strategy | None = None,
        fallback_strategy: Strategy | None = None,
    ) -> None:
        self._capability_registry = capability_registry
        self._default_strategy = default_strategy or DomainPlannerStrategy(capability_registry)
        self._fallback_strategy = fallback_strategy or FallbackStrategy()
```

### Ownership Lifecycle
1. **Composition Root Ownership**: `ArgosRuntime.create_default()` instantiates, populates, and freezes `CapabilityRegistry` before injecting it into `Planner`.
2. **No Hidden State**: Prohibits global state, thread-local storage, hidden runtime lookups, or Service Locator anti-patterns.
3. **Deterministic Testability**: Enables unit testing `Planner` with frozen stub `CapabilityRegistry` instances without requiring full runtime setup.

---

## 4. Ambiguous Action Resolution Algorithm

When multiple tools advertise the same `Action`, `CapabilityRegistry.get_schema_for_action(action)` raises `AmbiguousActionError`. `Planner` MUST NOT silently choose an arbitrary tool.

```text
                                [Action Lookup]
                                       │
                         [get_schema_for_action(action)]
                                       │
                 ┌─────────────────────┼─────────────────────┐
                 ▼                     ▼                     ▼
          [0 Matching Tools]    [1 Matching Tool]   [>1 Matching Tools]
                 │                     │                     │
                 ▼                     ▼                     ▼
       ActionNotFoundError      Return Schema      AmbiguousActionError
                 │                     │                     │
                 ▼                     │                     ▼
      UnsupportedActionError           │          Attempt Intent Resolution
       (Fallback / Clarify)            │          (Check tool_id entity)
                                       │                     │
                                       │       ┌─────────────┴─────────────┐
                                       │       ▼                           ▼
                                       │  [Resolved]                 [Unresolved]
                                       │       │                           │
                                       └───────┼───────────────────────────┘
                                               │                           │
                                               ▼                           ▼
                                       Build PlanStep          Action.ASK_CLARIFICATION
                                     (Validated Params)          (Request explicit tool)
```

If resolution fails, `Planner` emits a clarification step using the existing Action catalog member:
`PlanStep(step_id=1, action=Action.ASK_CLARIFICATION, parameters={"message": "Multiple tools handle action '...'..."})`.

---

## 5. Schema Validation & Parameter Defaults Contract

`SchemaValidator` validates entity parameters against canonical `ParameterSpec` contracts (`src/argos/tools/base_tool.py`):

```python
class SchemaValidator:
    """Validates intent entity parameters against authoritative ParameterSpec contracts."""

    @staticmethod
    def validate_and_coerce(
        schema: ActionSchemaDescriptor,
        raw_parameters: dict[str, Any],
    ) -> dict[str, Any]: ...
```

### Deterministic Parameter Handling Rules
1. **Required Parameter Missing**: Raises `MissingParameterError` $\rightarrow$ Strategy emits `Action.ASK_CLARIFICATION`.
2. **Optional Parameter Omitted**: If `ParameterSpec.default` is present, injects `validated[name] = spec.default`.
3. **Invalid Parameter Type / Coercion Failure**: Raises `InvalidParameterError` $\rightarrow$ Strategy emits `Action.ASK_CLARIFICATION`.
4. **Allowed-Value Constraint Violation**: Raises `InvalidParameterError` $\rightarrow$ Strategy emits `Action.ASK_CLARIFICATION`.
5. **Reserved `_`-prefixed Parameter**: Raises `ReservedParameterError` $\rightarrow$ Terminates planning immediately.
6. **Unmapped Extra Entities**: Preserved under `PlanStep.metadata["unmapped_entities"]`.

---

## 6. Strategy Hierarchy & Exception Model

### Strategy Hierarchy
- `Strategy` (ABC): Base planning strategy interface.
- `FallbackStrategy`: Generates clarification request steps for low-confidence or unknown intents.
- `SchemaAwareStrategy` (ABC): Base strategy for schema-aware capability planning.
- `DomainPlannerStrategy`: Concrete strategy mapping intents to capability domains (`domain.application`, `domain.filesystem`, `domain.system_info`, `domain.web`).

### Exception Hierarchy (`src/argos/planning/exceptions.py`)
```text
PlanningError (Base Exception)
├── InvalidIntentResultError (Existing)
├── ProcessingError (Existing)
├── SchemaValidationError (ADS-003 Base)
│   ├── MissingParameterError (Triggers Action.ASK_CLARIFICATION)
│   ├── InvalidParameterError (Triggers Action.ASK_CLARIFICATION)
│   └── ReservedParameterError (Terminates Planning)
└── StrategyResolutionError (ADS-003 Base)
    ├── UnsupportedActionError (Triggers FallbackStrategy)
    └── AmbiguousPlannerActionError (Triggers Action.ASK_CLARIFICATION)
```

---

## 7. Inviolable Architectural Invariants

1. `BrainCore` remains the sole cognitive center.
2. `Planner` is an untrusted proposal generator with ZERO execution authority.
3. `CapabilityRegistry` is injected via constructor injection; no Service Locator or global state.
4. `SchemaValidator` enforces canonical `ParameterSpec` contracts from `src/argos/tools/base_tool.py`.
5. `_risk_class` and `_`-prefixed keys are strictly internal policy parameters and MUST be rejected on input.
6. Ambiguous tool actions emit `Action.ASK_CLARIFICATION` and are NEVER resolved silently.
7. `PolicyEngine` remains the sole policy gate; `RiskClass` is informational to `Planner`.
8. Frozen ADS-001 through ADS-009 specifications remain 100% untouched.
