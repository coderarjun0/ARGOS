# ADS-008 — Real Tool Runtime Specification

**Subsystem:** Real Tool Runtime (`src/argos/tools/`)  
**Version:** 1.0.0  
**Status:** Approved & Implemented  
**Target Release:** v0.9.0-alpha  

---

## 1. Overview

ADS-008 defines the architecture, interfaces, and contracts of the **ARGOS Real Tool Runtime**. This subsystem bridges the high-level cognitive planning pipeline (ADS-003, ADS-004, ADS-005) to safe, policy-governed, real host OS executions without modifying frozen subsystem contracts, bypassing Layer 1 or Layer 2 policy gates, or introducing process vulnerabilities.

---

## 2. Subsystem Architecture

```text
[ArgosRuntime Facade]
         │
         ▼
    [BrainCore] ──► [WorkingMemory] / [GoalManager]
         │
         ▼
[CapabilityManager] ──► [PolicyEngine (Layer 1 Gate)]
         │
         ▼
[ExecutionCapability]
         │
         ▼
[ExecutionEngine] ──► [PolicyEngine (Layer 2 Gate)]
         │
         ▼
  [ActionRouter]
         │
         ▼
[ToolExecutorAdapter] (Implements ActionExecutor ABC)
         │
         ▼
    [BaseTool]
         │
         ▼
[PlatformAdapter (Win32PlatformAdapter / MockPlatformAdapter)]
         │
         ▼
    [Host OS]
```

---

## 3. Interfaces & Contracts

### 3.1 BaseTool (`src/argos/tools/base_tool.py`)
```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def manifest(self) -> ToolManifest: ...

    @abstractmethod
    def validate_parameters(self, parameters: dict[str, Any]) -> None: ...

    @abstractmethod
    def run(self, parameters: dict[str, Any]) -> ToolResult: ...
```

### 3.2 ToolExecutorAdapter (`src/argos/tools/tool_executor_adapter.py`)
```python
class ToolExecutorAdapter(ActionExecutor):
    def __init__(self, tool: BaseTool) -> None: ...
    def execute(self, step: PlanStep) -> StepResult: ...
```

### 3.3 BasePlatformAdapter (`src/argos/tools/adapters/base_platform.py`)
```python
class BasePlatformAdapter(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    def launch_known_application(self, application_name: str) -> dict[str, Any]: ...
```

---

## 4. Security & Governance Invariants

1. **Double Policy Gate Enforcement**: Every tool step evaluates Layer 1 (`CapabilityManager`) and Layer 2 (`ExecutionEngine`) policy gates prior to tool dispatch.
2. **No Arbitrary Shell Execution**: `shell=False` is enforced for process execution. No invocation of `cmd.exe /c`, `powershell.exe`, or `bash`.
3. **Whitelist Resolution**: Executable paths are resolved exclusively through immutable platform adapter mappings (`"calculator"` $\rightarrow$ `"calc.exe"`).
4. **Preserved 6-Scope Policy Precedence Hierarchy**:
   $$\text{CONSTITUTION} \gt \text{SYSTEM\_IMMUTABLE} \gt \text{SYSTEM\_SECURITY} \gt \text{USER\_POLICY} \gt \text{CONTEXTUAL} \gt \text{DEFAULT\_FALLBACK}$$
5. **Fail-Closed Semantics**: Any parameter validation error or unmapped application raises `InvalidParameterError` / `PlatformExecutionError` and fails closed.
