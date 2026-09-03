# ADS-007 Architecture Design Specification — Policy Engine Subsystem

**Document:** `specs/ADS-007-Policy-Engine.md`  
**Subsystem:** ARGOS Policy Engine Subsystem (`argos.policy`)  
**Version:** 1.1  
**Status:** Approved (Frozen)  
**Created:** 3 September 2026  
**Last Updated:** 3 September 2026  
**Author:** Arjun Saini  
**Technical Mentors:** ChatGPT & Google DeepMind Antigravity Team  

---

## 1. Document Metadata

| Attribute | Specification Value |
| :--- | :--- |
| **Specification ID** | ADS-007 |
| **Subsystem Name** | Policy Engine Subsystem (`argos.policy`) |
| **Target Release** | `v0.7.0-alpha` |
| **Architecture Version** | 1.1 |
| **Specification Status** | **Approved (Frozen)** |
| **Authoritative Baseline** | ADS-001, ADS-002, ADS-003, ADS-004, ADS-005, ADS-006 v1.1 |
| **Governing Documents** | CONSTITUTION.md (Articles I, IV, V, VI, VII, XI, XIV), DECISIONS.md (EDR-002, EDR-005, EDR-006, EDR-007, EDR-025) |

---

## 2. Executive Summary

ADS-007 defines the architecture, domain model, evaluation semantics, security invariants, and subsystem boundaries for the **ARGOS Policy Engine Subsystem** (`argos.policy`). 

The Policy Engine serves as the centralized governance authority for ARGOS. It evaluates operational actions, cognitive capability dispatches, tool executions, memory mutations, and environmental operations against immutable system safety prohibitions, platform security rules, and user-configured policies.

The Policy Engine is deterministic, side-effect free, and model-agnostic. It does not control cognitive loop orchestration, generate plan recipes, execute actions, or maintain dynamic session state. It evaluates proposals and produces auditable decisions (`ALLOW`, `DENY`, `REQUIRE_CONFIRMATION`, `REQUIRE_AUTHORIZATION`) to ensure that no capability, external tool, or artificial intelligence provider can violate system safety, human privacy, or constitutional principles.

---

## 3. Motivation

With the completion of ADS-001 through ADS-006, ARGOS possesses complete request perception, semantic intent classification, recipe planning, action step execution, cognitive loop orchestration (`BrainCore`), and multi-tier memory storage (`MemoryEngine`).

However, prior to ADS-007, safety checks and confirmation bounds were hardcoded, fragmented across capability modules, or inferred heuristically inside `Planner` or `DecisionEngine`. As ARGOS prepares to support real OS hardware execution (file operations, terminal commands, web sockets, external application tools) and neural LLM reasoning providers, relying on implicit or fragmented safety checks introduces critical risks:

1. **Bypass Risk:** Without a centralized policy gateway, a newly added capability or low-level tool could accidentally execute unsafe side-effects without governance inspection.
2. **LLM Safety Risk:** Neural LLMs are untrusted proposal engines. An LLM could generate plan recipes containing destructive OS actions or prompt injection exploits that bypass hardcoded heuristics.
3. **Constitutional Mandate:** Article I (Human First), Article V (Safety), and Article XIV (User Policies) of the ARGOS Constitution require that irreversible or high-impact actions mandate explicit confirmation, and that user-defined policies govern repetitive operations without compromising immutable safety.

ADS-007 fills this architectural gap by establishing a formal, deterministic, layered policy gateway that guarantees safe, policy-compliant operating system automation.

---

## 4. Scope

The scope of ADS-007 includes:

1. **Policy Engine Facade (`PolicyEngine`):** The primary public interface orchestrating rule loading, evaluation, precedence resolution, and decision compilation.
2. **Domain Models & Enums:** Standardized dataclasses (`PolicyRule`, `PolicyDecision`) and enumerations (`PolicyOutcome`, `PolicyScope`, `RuleOperator`).
3. **Layered Policy Gateways:**
   - **Layer 1 (Primary Gateway):** `CapabilityManager` integration for pre-dispatch capability governance.
   - **Layer 2 (Execution Gateway):** `ExecutionEngine` / `ActionRouter` integration for pre-execution tool parameter governance.
4. **Precedence & Conflict Resolution:** Deterministic 4-step resolution rules ensuring constitutional and immutable system prohibitions override all user policies, with deny-override and specificity-override conflict semantics.
5. **Fail-Closed Semantics:** Deterministic fallback mechanisms guaranteeing that evaluation errors, malformed rules, or missing context parameters never fail open to `ALLOW`.
6. **Declarative Rule Representation:** Restricted, JSON-serializable policy rule models prohibiting dynamic string execution (`eval()`) or untrusted Python callbacks.
7. **Integration Contracts:** Interfaces connecting `PolicyEngine` with `BrainCore` (`WAITING_FOR_USER`), `MemoryEngine` (user policy storage), and `ConsentManager` (privacy boundary).

---

## 5. Non-Scope

The following features and responsibilities are **explicitly excluded** from ADS-007:

1. **Arbitrary Code Execution / Dynamic Evaluators:** No support for untrusted Python lambdas, dynamic string evaluation (`eval()`), or remote code execution in rules.
2. **Full JSONPath / Complex Expression Parsers:** Complex query languages are deferred to post-v1.0.
3. **Machine-Learning Policy Evaluation:** No probabilistic or neural policy evaluation. All policy decisions are 100% deterministic.
4. **Authentication & Credential Infrastructure:** `PolicyEngine` does **NOT** authenticate users, issue cryptographic tokens, manage user identity, or store passwords.
5. **Memory Consent Management:** `ConsentManager` (ADS-006) remains the exclusive authority for validating Article IV constitutional consent for persistent memory storage. `PolicyEngine` does not replace `ConsentManager`.
6. **Real OS Tool Implementation:** Real file system or terminal tools belong to execution milestones. ADS-007 defines only the policy enforcement boundaries.
7. **Remote Policy Sync:** Cloud policy synchronization servers are excluded.

---

## 6. Architectural Position

The Policy Engine occupies a central governance role in the ARGOS system architecture:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                COGNITIVE LAYER (Brain Core)                            │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                   BrainCore                                    │   │
│   │             (Cognitive Loop Orchestration & State Transition Control)          │   │
│   └───────┬───────────────────┬────────────────────┬───────────────────┬───────────┘   │
│           │                   │                    │                   │               │
│           ▼                   ▼                    ▼                   ▼               │
│   ┌───────────────┐   ┌───────────────┐    ┌───────────────┐   ┌───────────────┐       │
│   │ WorkingMemory │   │ GoalManager   │    │ DecisionEngine│   │   Observer    │       │
│   │ (Transient)   │   │ (Goal State)  │    │ (Reasoning)   │   │ (Telemetry)   │       │
│   └───────────────┘   └───────────────┘    └───────────────┘   └───────────────┘       │
└───────────────────────────────────────┬────────────────────────────────────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CAPABILITY DISPATCH BOUNDARY                              │
│                                                                                        │
│                         CapabilityManager (Registry & DI)                              │
│                                       │                                                │
│                                       ├───► [ LAYER 1: Primary Policy Gateway ]        │
│                                       │     (PolicyEngine.evaluate_capability)         │
│         ┌───────────────────┬─────────┴─────────┬───────────────────┐                  │
│         ▼                   ▼                   ▼                   ▼                  │
│  InputCapability    IntentCapability    PlanningCapability  ExecutionCapability        │
└─────────────────────────────────────────────────────────────────────┬──────────────────┘
                                                                      │
                                                                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              EXECUTION & TOOL BOUNDARY                                 │
│                                                                                        │
│                                ExecutionEngine                                         │
│                                       │                                                │
│                                       ├───► [ LAYER 2: Tool Execution Gateway ]        │
│                                       │     (PolicyEngine.evaluate_action)             │
│                                       ▼                                                │
│                                  ActionRouter                                          │
│                                       │                                                │
│         ┌───────────────────┬─────────┴─────────┬───────────────────┐                  │
│         ▼                   ▼                   ▼                   ▼                  │
│  ApplicationExecutor  FileExecutor         WebExecutor         SystemExecutor          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Responsibilities

The Policy Engine Subsystem is strictly responsible for:

1. **Centralized Rule Registry:** Maintaining active immutable system prohibitions, platform security rules, and user-defined policies.
2. **Deterministic Evaluation:** Evaluating requested capabilities, actions, parameters, and operational contexts against registered policies in a pure, side-effect-free manner.
3. **Precedence Enforcement:** Guaranteeing that the Constitution and immutable system prohibitions take absolute precedence over user policies and default fallbacks.
4. **Outcome Generation:** Producing immutable `PolicyDecision` records containing evaluation results (`ALLOW`, `DENY`, `REQUIRE_CONFIRMATION`, `REQUIRE_AUTHORIZATION`), matched rule IDs, scopes, and human-readable explanations.
5. **Fail-Closed Protection:** Catching evaluation exceptions, malformed rules, or missing context parameters and enforcing fail-closed outcomes (`DENY` or `REQUIRE_CONFIRMATION`).
6. **Layered Gateway Governance:** Providing standard evaluation interfaces for `CapabilityManager` (Layer 1) and `ExecutionEngine` (Layer 2).

---

## 8. Non-Responsibilities

The Policy Engine Subsystem MUST NOT:

1. **Control Cognition:** It does not initiate cognitive loop transitions, manage goal states, or drive `BrainCore`.
2. **Perform Cognitive Reasoning:** It does not decide what capability should execute next (`DecisionEngine` responsibility).
3. **Generate Plans:** It does not construct plan recipes or action steps (`Planner` responsibility).
4. **Execute Actions or Tools:** It does not run system CLI commands, modify files, or trigger capabilities (`ExecutionEngine` responsibility).
5. **Own Memory Storage:** It does not manage SQLite databases, create memory records, or clear session stores (`MemoryEngine` responsibility).
6. **Validate Constitutional Memory Consent:** It does not replace `ConsentManager` (ADS-006 responsibility).
7. **Authenticate Users or Issue Tokens:** It does not store passwords, check cryptographic identities, or act as an identity provider.
8. **Use Neural AI / LLMs:** It does not invoke neural language models or non-deterministic APIs to evaluate rules.

---

## 9. Domain Concepts

### Fundamental Architecture Triad:

- **DecisionEngine:** *"What capability/step should cognition execute next?"*
- **PolicyEngine:** *"Is the proposed capability/action allowed under system and user policies, and under what conditions?"*
- **Capability / Executor:** *"How is the mechanical operation performed?"*

### Policy Terminology:

- **Policy:** A structured collection of rules governing system actions, capability access, data persistence, and security boundaries.
- **Constraint:** An individual boundary condition specifying parameter limits, target patterns, and comparison operators.
- **System Prohibition:** An immutable, non-bypassable safety rule protecting data integrity, hardware, and human safety.
- **System Security Policy:** Platform-level rules enforcing security sandboxes and restricted operational boundaries.
- **User Policy:** Declarative, user-configured rules granting pre-authorization or restricting specific safe operations.
- **Contextual Rule:** A policy conditional upon active environmental parameters (e.g., network state, session mode).

---

## 10. Public API

The `argos.policy` package exposes a single public facade class, domain models, outcomes, scopes, and exception types. Internal rule matchers and predicate evaluators remain encapsulated.

```python
# Namespace exports for argos.policy
from argos.policy.exceptions import (
    PolicyEngineError,
    PolicyEvaluationError,
    PolicyInitializationError,
    PolicyValidationError,
)
from argos.policy.models import (
    PolicyDecision,
    PolicyOutcome,
    PolicyScope,
    RuleOperator,
)
from argos.policy.policy_engine import PolicyEngine

__all__ = [
    "PolicyEngine",
    "PolicyOutcome",
    "PolicyScope",
    "RuleOperator",
    "PolicyRule",
    "PolicyDecision",
    "PolicyEngineError",
    "PolicyInitializationError",
    "PolicyValidationError",
    "PolicyEvaluationError",
]
```

### Facade Interface (`PolicyEngine`):

```python
class PolicyEngine:
    """Public facade for the ARGOS Policy Engine Subsystem.
    
    Evaluates capabilities and low-level actions against deterministic rules.
    Evaluation is side-effect-free and stateless with respect to runtime cognition.
    Maintains an internal in-memory rule snapshot cache loaded from code and MemoryEngine.
    """

    def __init__(self, memory_engine: Any | None = None) -> None:
        """Initializes PolicyEngine, loading system rules and optional user policies.

        Args:
            memory_engine: Optional MemoryEngine instance for loading user policy rules.
        """
        ...

    def evaluate_capability(
        self, capability_name: str, action: str, kwargs: dict[str, Any] | None = None
    ) -> PolicyDecision:
        """Evaluates whether a capability invocation is permitted by policy (Layer 1).

        Args:
            capability_name: Target capability name (e.g. 'memory', 'execution').
            action: Capability action identifier.
            kwargs: Keyword arguments passed to capability.

        Returns:
            PolicyDecision container with evaluation outcome.
        """
        ...

    def evaluate_action(
        self, action: str, target: str | None = None, parameters: dict[str, Any] | None = None
    ) -> PolicyDecision:
        """Evaluates whether a low-level action execution is permitted by policy (Layer 2).

        Args:
            action: Execution action string (e.g. 'run_command', 'delete_file').
            target: Resource target string (e.g. file path, URL, application name).
            parameters: Action parameters dictionary.

        Returns:
            PolicyDecision container with evaluation outcome.
        """
        ...

    def register_user_rule(self, rule: PolicyRule) -> None:
        """Registers a user-defined policy rule in memory cache.

        Args:
            rule: PolicyRule instance to register.

        Raises:
            PolicyValidationError: If rule is invalid or attempts to override system rules.
        """
        ...

    def reload_user_rules(self) -> None:
        """Reloads user policy rules from PersistentStore via MemoryEngine without recursion."""
        ...
```

---

## 11. Domain Models

All public domain models are immutable dataclasses utilizing `slots=True`.

### `PolicyRule` Model:

```python
@dataclass(slots=True)
class PolicyRule:
    """Represents a declarative policy rule definition."""

    rule_id: str
    scope: PolicyScope
    target_capability: str  # Capability name or '*' for all
    target_action: str  # Action string or '*' for all
    parameter_name: str | None  # Target parameter name or None
    operator: RuleOperator  # Comparison operator
    expected_value: str  # Expected comparison value string
    outcome: PolicyOutcome  # Outcome if rule matches
    explanation: str  # Human-readable policy justification
```

### `PolicyDecision` Model:

```python
@dataclass(slots=True)
class PolicyDecision:
    """Represents the immutable result of a policy evaluation."""

    outcome: PolicyOutcome
    matched_rule_id: str | None
    scope: PolicyScope
    explanation: str
    timestamp: datetime
```

---

## 12. Policy Outcomes

The `PolicyOutcome` enumeration defines the four public outcome states produced by policy evaluation:

```python
class PolicyOutcome(StrEnum):
    """Public evaluation outcomes produced by PolicyEngine."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REQUIRE_AUTHORIZATION = "require_authorization"
```

### Outcome Definitions & Severity Ranking:

1. **`ALLOW` (Severity Rank 1)**: The requested operation complies with all system and user policies. Execution proceeds without interruption.
2. **`DENY` (Severity Rank 4)**: The requested operation violates an immutable prohibition or active security policy. Execution is halted immediately (terminal for that action).
3. **`REQUIRE_CONFIRMATION` (Severity Rank 2)**: The operation is sensitive or contextually restricted. Execution pauses, and `BrainCore` enters `WAITING_FOR_USER` to seek explicit human approval.
4. **`REQUIRE_AUTHORIZATION` (Severity Rank 3)**: The operation requires an explicit elevated authorization payload passed in context (e.g. `AuthorizationRecord`). V1 authorization is **action-scoped** for the target execution attempt.

*Severity Ranking Rationale:* `REQUIRE_AUTHORIZATION` (Rank 3) is more restrictive than `REQUIRE_CONFIRMATION` (Rank 2) because it requires explicit privilege elevation and provenance metadata, whereas confirmation requires interactive approval.

*Note on Internal Conflict Resolution:* `CONFLICT` is **not** a public enum value. Internal rule conflicts resolve deterministically to `DENY` or `REQUIRE_CONFIRMATION` before producing the public `PolicyDecision`.

---

## 13. Policy Scopes & Absolute Authority Hierarchy

The `PolicyScope` enumeration defines the hierarchy and precedence layers for policy rules:

```python
class PolicyScope(StrEnum):
    """Hierarchy and precedence scopes for policy rules."""

    CONSTITUTION = "constitution"
    SYSTEM_IMMUTABLE = "system_immutable"
    SYSTEM_SECURITY = "system_security"
    USER_POLICY = "user_policy"
    CONTEXTUAL = "contextual"
    DEFAULT_FALLBACK = "default_fallback"
```

### Absolute Precedence Hierarchy:
$$\text{CONSTITUTION} \gt \text{SYSTEM\_IMMUTABLE} \gt \text{SYSTEM\_SECURITY} \gt \text{USER\_POLICY} \gt \text{CONTEXTUAL} \gt \text{DEFAULT\_FALLBACK}$$

1. **`CONSTITUTION`**: The highest governing document (CONSTITUTION.md). Below which no policy rule, user preference, interactive confirmation, authorization token, or LLM proposal can operate.
2. **`SYSTEM_IMMUTABLE`**: Hardcoded kernel safety prohibitions. Non-bypassable by any user policy, database record, or LLM proposal.
3. **`SYSTEM_SECURITY`**: Platform security rules enforcing safe path sandboxes and process boundaries.
4. **`USER_POLICY`**: User-configured preferences and pre-authorization rules stored in `PersistentStore`.
5. **`CONTEXTUAL`**: Time-bounded or environment-bounded operational rules.
6. **`DEFAULT_FALLBACK`**: Safe baseline outcomes applied when no specific policy rule matches.

---

## 14. Rule Representation

To guarantee security and eliminate dynamic execution vulnerabilities, V1 policy rules use a **restricted declarative model**.

```python
class RuleOperator(StrEnum):
    """Supported rule evaluation operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    PREFIX_MATCH = "prefix_match"
    SUFFIX_MATCH = "suffix_match"
    REGEX_MATCH = "regex_match"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
```

### Security Enforcement:
- **No `eval()`:** No string evaluation or dynamic code execution is permitted.
- **No Dynamic Callbacks:** Policy rules loaded from databases or configuration files consist strictly of static text patterns and `RuleOperator` enums.
- **Built-in System Predicates:** Complex system safety checks (e.g. system directory path traversal) are implemented as hardcoded, inspectable Python functions inside `argos.policy.predicates` and assigned exclusively to `SYSTEM_IMMUTABLE` rules.

---

## 15. Evaluation Semantics & Statelessness Clarification

When `PolicyEngine.evaluate_capability()` or `evaluate_action()` is called:

1. **Stateless Evaluation:** The evaluation process is pure, side-effect-free, and stateless with respect to cognitive runtime state. It reads the in-memory rule snapshot cache and returns an immutable `PolicyDecision`.
2. **Context Normalization:** Inputs (`capability_name`, `action`, `kwargs`/`parameters`) are sanitized, lowercased, and packaged into an internal `EvaluationContext`.
3. **Scope Precedence Scanning:** Rules are scanned in strict scope precedence (`CONSTITUTION` $\rightarrow$ `SYSTEM_IMMUTABLE` $\rightarrow$ `SYSTEM_SECURITY` $\rightarrow$ `USER_POLICY` $\rightarrow$ `CONTEXTUAL` $\rightarrow$ `DEFAULT_FALLBACK`). Matching at a higher scope terminates lower-scope processing.
4. **Decision Compilation:** A frozen `PolicyDecision` container is returned containing outcome, rule ID, scope, explanation string, and UTC timestamp.

---

## 16. Canonical Deterministic Conflict Resolution Algorithm

To ensure two conforming implementations produce identical outcomes from the same rule set, evaluation follows an unambiguous 4-step algorithm:

### Step 1: Scope Precedence Scanning
Evaluation scans policy scopes in strict sequential order (`CONSTITUTION` $\rightarrow$ `SYSTEM_IMMUTABLE` $\rightarrow$ `SYSTEM_SECURITY` $\rightarrow$ `USER_POLICY` $\rightarrow$ `CONTEXTUAL` $\rightarrow$ `DEFAULT_FALLBACK`). If any matching rule exists at a higher scope layer, lower scopes are **ignored**.

### Step 2: Deny-Override Inspection
Within the active matching scope layer, if any matching rule returns `DENY` (Severity Rank 4), the evaluated outcome is immediately **`DENY`**.

### Step 3: Specificity Ranking
Order remaining matching rules within the scope by Specificity Rank:
- *Specificity 3:* Exact Capability + Exact Action + Parameter Match
- *Specificity 2:* Exact Capability + Exact Action
- *Specificity 1:* Exact Capability + Wildcard Action (`"*"`)
- *Specificity 0:* Wildcard Capability (`"*"`) + Wildcard Action (`"*"`)

Filter to matching rules tied at the highest Specificity Rank.

### Step 4: Severity Selection & Deterministic Tie-Break
1. Among the rules tied at the highest Specificity Rank, select the outcome with the highest Severity Rank (`DENY` [4] > `REQUIRE_AUTHORIZATION` [3] > `REQUIRE_CONFIRMATION` [2] > `ALLOW` [1]).
2. If multiple rules tied at the same scope, specificity, and severity produce different explanations, sort matching rules lexicographically by `rule_id` and select the first.

---

## 17. Conflict Resolution & Monotonic Composition

### DecisionEngine + PolicyEngine Monotonic Safety Composition:
Confirmation and restriction requirements between `DecisionEngine` and `PolicyEngine` are **cumulative and monotonic**:

| DecisionEngine Output | PolicyEngine Output | BrainCore Combined Behavior | Rationale |
| :--- | :--- | :--- | :--- |
| `REQUIRE_CONFIRMATION` | `ALLOW` | **`WAITING_FOR_USER`** | DecisionEngine heuristic requirement preserved. |
| `ALLOW` / Ready | `REQUIRE_CONFIRMATION` | **`WAITING_FOR_USER`** | PolicyEngine rule requirement preserved. |
| `REQUIRE_CONFIRMATION` | `REQUIRE_CONFIRMATION` | **`WAITING_FOR_USER`** | Cumulative agreement. |
| `REQUIRE_CONFIRMATION` | `REQUIRE_AUTHORIZATION` | **`WAITING_FOR_USER`** (seeking Auth) | Highest restriction enforced. |
| Allows execution | `DENY` | **`BrainStatus.FAILED`** | PolicyEngine `DENY` overrides DecisionEngine proposal. |

**Infallibility Invariant:** Neither engine can override, cancel, or weaken a safety requirement requested by the other.

---

## 18. Policy Storage & Failure Semantics Matrix

User policy rules are persistent declarative data stored externally in `ADS-006 PersistentStore` (`category="policy_rule"`).

`PolicyEngine.reload_user_rules()` queries `MemoryEngine` at startup to populate its in-memory rule snapshot cache. To prevent infinite recursion, `reload_user_rules()` consumes policy data from `MemoryEngine` **without executing policy evaluation on the startup read operation itself**. `PolicyEngine` consumes policy data; it does **not** become `MemoryEngine`.

### Deterministic Failure Semantics Matrix:

| Failure / Context Scenario | Target Action Category | Evaluated Outcome | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **A. Engine OK, PersistentStore Unavailable** | Mutation / OS Execution | **`DENY`** | Fail-closed: Cannot verify user safety rules for dangerous side-effects. |
| **A. Engine OK, PersistentStore Unavailable** | Read / Perceive | **`ALLOW`** | Safe baseline evaluated against immutable code rules. |
| **B. User Policy Data Load Fails** | Mutation / OS Execution | **`DENY`** | Fail-closed: Missing safety rules forces execution block. |
| **B. User Policy Data Load Fails** | Read / Perceive | **`ALLOW`** | Baseline reads governed by built-in system rules. |
| **C. Specific Malformed Persisted Rule** | Matching target action | **`REQUIRE_CONFIRMATION`** | Intercepts malformed user rule safely without silent `ALLOW`. |
| **D. Persisted Rule Unavailable** | Matching target action | **`DEFAULT_FALLBACK`** | Falls back to system default action rule. |
| **E. Internal Engine Exception** | Any action | **`DENY`** | Fail-closed security intercept. |
| **F. Immutable System Rule Match** | Prohibited action | **`DENY`** | Non-bypassable kernel safety prohibition. |
| **G. No Applicable User Rule** | Known safe action | **`ALLOW`** | System default fallback for standard operations. |
| **G. No Applicable User Rule** | Unrecognized / OS action | **`REQUIRE_CONFIRMATION`** | System default fallback for unrecognized actions. |

---

## 19. CapabilityManager Integration (Layer 1 Gateway)

`CapabilityManager` acts as the **Primary Policy Gateway**. Every capability execution request is intercepted and evaluated before capability dispatch:

```text
BrainCore.process()
      │
      ▼
CapabilityManager.execute(name, action, *args, **kwargs)
      │
      ▼
PolicyEngine.evaluate_capability(name, action, kwargs)
      │
      ├───────────────────────┬───────────────────────┐
      ▼                       ▼                       ▼
   ALLOW                   DENY             REQUIRE_CONFIRMATION
      │                       │                       │
      ▼                       ▼                       ▼
Dispatch to             Raise PolicyError       Transition BrainCore to
CognitiveCapability    (Brain Status FAILED)     WAITING_FOR_USER
```

### Outcome Mapping at Layer 1:
- **`ALLOW`**: `CapabilityManager` dispatches execution to `CognitiveCapability.execute()`.
- **`DENY`**: `CapabilityManager` raises `PolicyEvaluationError`. `BrainCore` catches the error and marks goal as `FAILED`.
- **`REQUIRE_CONFIRMATION`**: `CapabilityManager` returns a policy pause signal. `BrainCore` transitions to `CognitiveState.WAITING_FOR_USER`.
- **`REQUIRE_AUTHORIZATION`**: Handled via `authorization` parameter check in context.

---

## 20. ExecutionEngine Integration (Layer 2 Gateway)

`ExecutionEngine` acts as the **Tool Execution Gateway**. Before routing an action step to an `ActionExecutor` (e.g., file deletion, running system terminal commands), `ExecutionEngine` evaluates the low-level action parameters:

```python
# Conceptual Layer 2 policy evaluation inside ExecutionEngine
decision = self._policy_engine.evaluate_action(
    action=step.action.value,
    target=step.parameters.get("target"),
    parameters=step.parameters
)
if decision.outcome == PolicyOutcome.DENY:
    return StepResult(step_id=step.step_id, status=StepStatus.FAILED, details=decision.explanation)
```

This guarantees that even if a high-level capability approves a plan, individual low-level tool operations (e.g., executing a command containing `rm -rf /`) are intercepted and blocked at Layer 2.

---

## 21. BrainCore Integration

`BrainCore` integrates `PolicyDecision` outcomes into the cognitive loop:

1. **`ALLOW`**: Cognition continues seamlessly.
2. **`DENY`**: `BrainCore` records the policy denial in `WorkingMemory.decision_history`, aborts active goal execution, and sets status `BrainStatus.FAILED`.
3. **`REQUIRE_CONFIRMATION`**: `BrainCore` sets `CognitiveState.WAITING_FOR_USER` and pauses the loop.
   - *Resumption:* When the user approves, `process(request, authorization=auth)` resumes execution with the active working memory and goal intact.
   - *Denial:* When the user refuses, `BrainCore` records the refusal, completes the goal (`COMPLETED`), and returns cleanly without error.

---

## 22. Memory / Consent Boundary

`ConsentManager` (ADS-006) and `PolicyEngine` (ADS-007) maintain strict architectural boundaries:

```text
                  Persistent Memory Mutation Request
                                  │
                                  ▼
                       [ ADS-007 PolicyEngine ]
             "Is memory storage permitted by policy?"
                                  │
                 ┌────────────────┴────────────────┐
                 │ DENY                            │ ALLOW
                 ▼                                 ▼
         Abort Mutation                 [ ADS-006 ConsentManager ]
       (Policy Violation)         "Is explicit user consent granted?"
                                                   │
                                 ┌─────────────────┴─────────────────┐
                                 │ Missing                           │ Granted
                                 ▼                                   ▼
                        WAITING_FOR_USER                     SQLite Commit
                      (Seek User Consent)                 (Persistent Memory)
```

- **`ConsentManager` Scope:** Manages Article IV constitutional user consent for persistent memory mutations.
- **`PolicyEngine` Scope:** Manages general system governance, safety prohibitions, and user policies.
- **Separation Guarantee:** `PolicyEngine` does not inspect `sqlite3` memory tables directly, and `ConsentManager` does not evaluate system security policies.

---

## 23. Autonomy Model

ADS-007 V1 supports three explicit **Autonomy Levels**:

- **Level 0 (User-Directed):** Every action requires explicit user command.
- **Level 1 (User-Confirmed):** Standard operation; sensitive or medium-confidence actions trigger `REQUIRE_CONFIRMATION`.
- **Level 2 (Pre-Authorized):** User policy rules grant pre-approval for specific safe, repetitive tasks (e.g., automatic local summaries).

*Constitutional Boundary:* Autonomy levels apply only to `USER_POLICY` and `CONTEXTUAL` rules. An autonomy level setting **can NEVER override or weaken a `SYSTEM_IMMUTABLE` prohibition**.

---

## 24. Privacy

1. **Log Isolation:** Raw user inputs, personal memory values, and secret parameters MUST NEVER appear in policy log messages or explanation strings.
2. **Local-Only:** Policy evaluation is 100% local and offline.
3. **Inspectability:** Users can list and view all active user policy rules stored in `PersistentStore`.

---

## 25. Auditability

Every policy evaluation produces a lightweight, frozen `PolicyDecision` containing:
- `outcome`: `PolicyOutcome`
- `matched_rule_id`: String ID of rule triggered
- `scope`: `PolicyScope`
- `explanation`: Human-readable justification
- `timestamp`: UTC timestamp

`BrainCore` records `PolicyDecision` fields directly into `WorkingMemory.decision_history` for full session auditability.

---

## 26. Error Semantics

All exceptions in `argos.policy` derive from `PolicyEngineError`:

```text
PolicyEngineError (Base Policy Exception)
    ├── PolicyInitializationError (Raised when rule loading fails)
    ├── PolicyValidationError (Raised when a rule structure is invalid)
    └── PolicyEvaluationError (Raised when policy evaluation encounters a terminal error)
```

When intercepted at `CapabilityManager`, policy exceptions are wrapped cleanly into `ProcessingError`, preserving clean package boundaries.

---

## 27. Dependency Direction

```text
BrainCore ────► CapabilityManager ────► PolicyEngine ────► MemoryEngine
                                              │
                                              ▼
                                   Built-in System Rules
```

- `PolicyEngine` depends ONLY on `MemoryEngine` (for loading user rules) and standard library modules.
- `PolicyEngine` does NOT depend on `BrainCore`, `DecisionEngine`, `Planner`, `ExecutionEngine`, or LLM modules.
- Zero circular dependencies.

---

## 28. Security Invariants

ADS-007 establishes 10 non-bypassable security invariants:

1. **Immutable Prohibitions Invariant:** `SYSTEM_IMMUTABLE` prohibitions can NEVER be overridden by user policy, database edits, or LLM proposals.
2. **Fail-Closed Invariant:** Policy evaluation errors or malformed rules can NEVER fail open to `ALLOW`.
3. **No Dynamic Execution Invariant:** Policy rules can NEVER execute arbitrary Python code, dynamic strings (`eval()`), or untrusted callbacks.
4. **Primary Gateway Invariant:** No registered capability can execute without passing Layer 1 policy evaluation in `CapabilityManager`.
5. **Tool Gateway Invariant:** No low-level execution step can run without passing Layer 2 policy evaluation in `ExecutionEngine`.
6. **LLM Non-Bypass Invariant:** LLM proposals are untrusted inputs and cannot modify rules or self-grant authorizations.
7. **Stateless Evaluation Invariant:** `PolicyEngine` is deterministic and side-effect free during evaluation.
8. **Consent Separation Invariant:** `PolicyEngine` cannot override or bypass `ConsentManager` for persistent memory mutations.
9. **Log Privacy Invariant:** Sensitive payload data cannot be logged in policy audit traces.
10. **State Non-Mutation Invariant:** `PolicyEngine` cannot directly alter `BrainCore` cognitive states.

---

## 29. Testing Strategy

Implementation of ADS-007 requires a comprehensive unit and integration test suite (`tests/test_policy.py`) verifying:

1. **Rule Evaluation:** Exact string, wildcard, prefix, suffix, regex, and list operators.
2. **Precedence Hierarchy:** Verifying `CONSTITUTION` and `SYSTEM_IMMUTABLE` override `USER_POLICY`.
3. **Conflict Resolution:** Verifying Deny-Override and Specificity-Override semantics.
4. **Fail-Closed Semantics:** Verifying malformed rules and missing context default to `DENY` / `REQUIRE_CONFIRMATION`.
5. **Layer 1 Integration:** Verifying `CapabilityManager` enforcement.
6. **Layer 2 Integration:** Verifying `ExecutionEngine` action enforcement.
7. **BrainCore Integration:** Verifying `WAITING_FOR_USER` transition on `REQUIRE_CONFIRMATION`.
8. **Memory/Consent Boundary:** Verifying policy check precedes `ConsentManager`.
9. **Security Invariants:** Verifying `eval()` prevention and LLM non-bypass rules.
10. **Coverage:** 100% statement coverage across all `argos.policy` modules with 0 Ruff errors.

---

## 30. Extensibility

Developers can add custom system security predicates by registering built-in predicate functions in `argos.policy.predicates`. User policy rules can be added dynamically via `PolicyEngine.register_user_rule()`.

---

## 31. Deferred Features

The following capabilities are explicitly deferred to post-v1.0 milestones:
- Complex JSONPath / AST expression evaluators.
- Machine-learning anomaly detection.
- Remote policy synchronization servers.
- Multi-tenant role-based access control (RBAC).
- Level 3 bounded autonomous execution.

---

## 32. Open Questions

### Critical / High
- *None.* All critical architectural boundaries, evaluation locations, storage rules, precedence algorithms, and outcome semantics have been fully resolved during the correction review.

### Medium
1. **Default Fallback Policy Configuration:** Should `DEFAULT_FALLBACK` for unrecognized user commands be configurable via environment variables (`ARGOS_STRICT_POLICY_MODE=1`)?

### Low
2. **Policy Rule Metadata Tags:** Should `PolicyRule` support optional tags (e.g. `tags=["network", "privacy"]`) for user filtering in inspection UI?

---

## 33. Acceptance Criteria

ADS-007 is considered implementation-ready when:

1. `specs/ADS-007-Policy-Engine.md` receives human architectural review and approval.
2. All 10 security invariants are documented and approved.
3. Public facade (`PolicyEngine`), models (`PolicyRule`, `PolicyDecision`), and enums (`PolicyOutcome`, `PolicyScope`) are finalized.
4. Layer 1 (`CapabilityManager`) and Layer 2 (`ExecutionEngine`) enforcement contracts are confirmed.

---

## 34. Specification Status & Readiness Verdict

**Status:** **Approved (Frozen)**

### ADS-007 Final Status:

**`APPROVED (FROZEN)`**
