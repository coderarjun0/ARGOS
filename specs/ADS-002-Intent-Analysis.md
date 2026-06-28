# ADS-002 — Intent Analysis

**Project:** ARGOS (Adaptive Reasoning & General Operating System)  
**Document:** ADS-002-Intent-Analysis.md  
**Version:** 0.2  
**Status:** Draft  
**Created:** 28 June 2026  
**Last Updated:** 28 June 2026  
**Author:** AI Coding Assistant  

---

## 1. Overview

The Intent Analysis subsystem is responsible for transforming a raw, pre-processed user request (`ParsedRequest`) into a structured semantic representation (`IntentResult`). 

This subsystem does not decide what actions the system will execute, nor does it perform cognitive planning or tool activation. Its sole responsibility is to analyze language and extract meaning, providing clean semantic data that downstream subsystems (primarily the Brain Core and the Planner) can use to formulate decisions.

---

## 2. Goals

### The subsystem shall:
* **Analyze Parsed Requests:** Accept a valid `ParsedRequest` as input.
* **Identify Primary Intent:** Classify the user's core intent into a standardized enum category.
* **Extract Entities:** Identify and extract parameters, nouns, and modifiers referenced in the text (e.g., specific file names, application names, dates, times).
* **Estimate Confidence:** Calculate and assign a score indicating the statistical or structural confidence of the classification using an independent evaluator.
* **Produce Structured Output:** Construct a formal `IntentResult` container representing the semantic data.
* **Be Deterministic:** Ensure that identical inputs produce identical intent classifications and extracted entities.
* **Be Independently Testable:** Contain no dependencies on active cognitive loops, memory, or AI models.
* **Support Engine Replacement:** Support future upgrades of the semantic parser (e.g., from regex rules to local models or LLMs) without breaking the public interface.

### The subsystem shall NOT:
* **Execute Commands:** Trigger operating system commands or call system tools.
* **Access the OS:** Perform operations on files, launch processes, or read system state.
* **Modify Memory:** Read, write, or alter working memory, session memory, or long-term databases.
* **Perform Planning:** Devise lists of tasks, execution workflows, or agent scripts.
* **Call External APIs:** Connect to networks or interact with external web APIs.

---

## 3. Public API

The subsystem exposes exactly one public class as its orchestration facade:

### `IntentAnalyzer`

#### Public Method Signature
```python
def analyze(self, request: ParsedRequest) -> IntentResult:
    """Performs semantic analysis on the parsed request to extract intent and entities.

    Args:
        request: The pre-processed, tokenized ParsedRequest container.

    Returns:
        An IntentResult containing the classified primary intent, confidence,
        extracted entities, and telemetry.

    Raises:
        InvalidRequestError: If the input is not a ParsedRequest instance.
        IntentAnalysisError: Base exception for any failure during intent classification.
    """
```

Downstream layers must only interact with `IntentAnalyzer` to request semantic analysis. Helper classes (such as rule engines, extractors, and evaluators) are encapsulated within the package boundaries.

---

## 4. Folder Structure

```text
src/
└── argos/
    └── intent/
        ├── __init__.py            # Exposes IntentAnalyzer, IntentResult, Intent (enum) and exceptions
        ├── constants.py           # Subsystem thresholds, regex patterns, or configurations
        ├── exceptions.py          # Exception hierarchy (base: IntentAnalysisError)
        ├── intent.py              # StrEnum defining valid user intent categories
        ├── intent_result.py       # IntentResult dataclass container
        ├── rule_engine.py         # Determines the core intent based on rules (internal)
        ├── entity_extractor.py    # Extracts nouns, dates, paths, and values (internal)
        ├── confidence_evaluator.py# Calculates semantic confidence (internal)
        └── analyzer.py            # Coordinates the internal processing pipeline (internal class)
```

### Module Responsibilities
* **`__init__.py`**: Serves as the public API boundary, exposing only the facade class, result model, intent enum, and exception classes.
* **`constants.py`**: Declares thresholds (e.g., minimum confidence levels) and internal pattern-matching resources.
* **`exceptions.py`**: Houses custom exceptions to ensure no low-level Python errors escape the boundary.
* **`intent.py`**: Holds the `StrEnum` mapping of standardized, machine-readable user intents.
* **`intent_result.py`**: Defines the final structured dataclass returned to callers.
* **`rule_engine.py`**: Implements deterministic, rules-based pattern mapping to assign a primary intent and possible alternatives. It does not calculate confidence.
* **`entity_extractor.py`**: Parses text to extract specific domain variables (e.g., application names, targets, parameters).
* **`confidence_evaluator.py`**: Independently evaluates classification confidence based on matching rules, entity presence, ambiguity, and classification quality.
* **`analyzer.py`**: Implements the public-facing orchestrator class `IntentAnalyzer`, passing data through the engine and managing logging/error mapping.

---

## 5. Internal Processing Pipeline

Data flows linearly through the subsystem to guarantee determinism and facilitate debugging:

```text
ParsedRequest
     │
     ▼
IntentAnalyzer (Orchestrator)
     │
     ├───► RuleEngine ───────────────► Determines Intent & Alternatives
     │
     ├───► EntityExtractor ──────────► Extracts Nouns & Values
     │
     ├───► ConfidenceEvaluator ──────► Calculates Confidence Score
     │
     ▼
Assembles final IntentResult container
     │
     ▼
IntentResult
```

### Core Responsibilities
* **`RuleEngine`**: Inspects normalized text and token lists to identify the structural action requested (e.g., matching keyword verbs like "open", "create", "delete"). It identifies the primary intent and secondary alternatives.
* **`EntityExtractor`**: Independently scans normalized text and tokens to extract key-value structures representing system targets (e.g., file paths, date constraints, application labels).
* **`ConfidenceEvaluator`**: Accepts the primary intent, alternatives, and extracted entities to evaluate the classification quality and assign a numerical score.
* **`IntentAnalyzer`**: Validates structural types on entry, coordinates execution of the rule engine, entity extractor, and confidence evaluator, logs progress, catches internal failures, and builds the final `IntentResult`.

---

## 6. Intent Model

Intents are represented by a standard Python `StrEnum` to guarantee strict type validation and machine-readability.

### Initial Intent Catalog
* **`UNKNOWN`**: Core action could not be identified with sufficient confidence.
* **`OPEN_APPLICATION`**: Launch a program (e.g., "Open VS Code").
* **`CLOSE_APPLICATION`**: Terminate a program (e.g., "Close Chrome").
* **`OPEN_FILE`**: Open a file in an editor or viewer.
* **`CREATE_FILE`**: Create a new file (e.g., "Create a text file").
* **`DELETE_FILE`**: Delete a file or directory.
* **`READ_FILE`**: Retrieve the content of a file.
* **`WRITE_FILE`**: Write or append data to a file.
* **`SEARCH_WEB`**: Execute a web search (e.g., "Search the web for python guides").
* **`RUN_COMMAND`**: Run a terminal shell command.
* **`GET_INFORMATION`**: Query information (e.g., "What is the time?").
* **`SET_REMINDER`**: Establish a task or reminder alarm.
* **`CONTROL_SYSTEM`**: Adjust system properties (e.g., adjust brightness/volume).

### Why Enums are Preferred Over String Literals
* **Static Analysis Support:** Typos in intent categories are caught at compile-time/static analysis stages instead of failing silently at runtime.
* **Controlled Vocabulary:** Restricts the intent space to a set of categories approved by downstream planners, preventing downstream translation bloat.

---

## 7. IntentResult Model

The `IntentResult` model represents the final structured semantic representation returned by `IntentAnalyzer.analyze()`.

### Fields
* **`primary_intent: Intent`**: The classified core user intent from the approved catalog.
* **`confidence: float`**: A score between `0.0` and `1.0` indicating classification confidence.
* **`entities: dict[str, list[str]]`**: A dictionary grouping extracted entities by their category (e.g., `{"application": ["vscode"]}`).
* **`alternatives: list[Intent]`**: A fallback list of alternative intent classifications.
* **`analysis_engine: str`**: Records which analysis engine produced the result (e.g., `"rule_engine"`).
* **`metadata: dict[str, Any]`**: Contextual metadata (e.g., matching rule names, processing latency, engine versions).

### Downstream Consumption
The `IntentResult` is the **only** model consumed by downstream systems (like the Brain Core) to represent the meaning of user request payloads.

The `analysis_engine` field is crucial for debugging, telemetry, performance benchmarking, and managing future engine interoperability as new parsers are introduced.

---

## 8. Entity Extraction

The `EntityExtractor` isolates nouns and values from raw or normalized text strings.

### Initial Supported Categories
* **`application`**: Software names (e.g., `"chrome"`, `"vscode"`).
* **`file`**: Filenames or paths (e.g., `"notes.txt"`, `"F:/workspace/docs"`).
* **`folder`**: Directory references.
* **`website`**: Website names (e.g., `"google"`, `"wikipedia"`).
* **`url`**: Standard URL links (e.g., `"https://google.com"`).
* **`person`**: Proper human names.
* **`date`**: Calendar dates (e.g., `"tomorrow"`, `"June 28"`).
* **`time`**: Specific times of day (e.g., `"2:00 PM"`).
* **`command`**: Raw code blocks or CLI commands (e.g., `"git status"`).

Entity extraction runs independently of classification. A sentence like "Delete notes.txt" extracts the file entity `"notes.txt"` regardless of whether the intent classifier maps it to `DELETE_FILE` or `UNKNOWN`.

---

## 9. Confidence Model

Confidence scores are expressed as floating-point values between `0.0` (complete uncertainty) and `1.0` (absolute certainty).

### Recommended Downstream Interpretation
* **`0.95 – 1.00` (Very High)**: The Planner may assume intent is clear and execute corresponding tools automatically.
* **`0.80 – 0.94` (High)**: The Planner may execute corresponding tools automatically if the action is considered safe.
* **`0.60 – 0.79` (Medium)**: The Planner should consider prompting the user for verification.
* **`Below 0.60` (Low)**: The Planner should reject execution and request user clarification.

> [!IMPORTANT]
> The Intent Analyzer **never** makes execution or policy decisions. It only evaluates and reports confidence. The logic to confirm or block actions remains with the Policy Engine and the Planner.

---

## 10. Error Handling

The subsystem handles failures gracefully using a dedicated exception hierarchy:

```text
IntentAnalysisError (Base Exception)
│
├── InvalidRequestError (Raised if input is not a ParsedRequest)
└── EngineError         (Raised if internal parsing engines fail/crash)
```

Internal low-level errors (e.g., index out of bounds during token lookup or regex compilation errors) must be caught internally and wrapped in `EngineError` before propagating to callers.

---

## 11. Logging

To debug the pipeline while preserving security, logs follow a strict classification scheme:

* **`INFO` Level:** Emits high-level lifecycle events ("Intent analysis started", "Intent classification completed"). No user content is logged here.
* **`DEBUG` Level:** Emits detailed diagnostic context. It is the only level permitted to log the detected intent, extracted entities, confidence scores, and alternative lists.
* **`ERROR` Level:** Emits failure exceptions and processing stack traces when parsing fails.

---

## 12. Verification Plan

The subsystem requires automated test suites in `tests/` targeting **100% line coverage**:

* **Intent Classification:** Verify correct mapping of typical commands (e.g., "Open chrome" -> `OPEN_APPLICATION`).
* **Entity Extraction:** Confirm file paths, URLs, dates, and application titles are parsed correctly.
* **Confidence Generation:** Assert that rules generate expected confidence scores for clean versus ambiguous phrases.
* **Invalid Requests:** Verify that non-`ParsedRequest` objects raise `InvalidRequestError`.
* **Dependency Injection:** Mock `RuleEngine`, `EntityExtractor`, and `ConfidenceEvaluator` to test their isolated functionality.
* **Logging Assertions:** Use fixtures to assert that private user strings are only logged at the `DEBUG` level.
* **Exception Propagation:** Ensure internal system crashes are successfully caught and wrapped into an `EngineError`.

---

## 13. Future Improvements

Future iterations will replace the rule-based parsing engine without changing public interfaces:

* **Machine-Learning Recognizer:** Introduce local classifier models (e.g., scikit-learn or ONNX) for semantic classification.
* **LLM-Powered Recognizer:** Call small local LLMs to parse complex, conversational commands.
* **Multilingual Support:** Integrate translation layers or multilingual embeddings.
* **Context-Aware Intent Analysis:** Incorporate chat history/session state when resolving intent (e.g., resolving "Open it" using the previous turn's target file).
* **Plugin-Based Recognizers:** Allow external plugins to register custom intent patterns and categories.

Every future analysis engine must return exactly the same `IntentResult` model and expose the same public API through `IntentAnalyzer`. This guarantees that the Planner and downstream subsystems never depend on implementation details of the parser.

---

## 14. Architectural Decisions

* **Intent Analysis Over Recognition:** We select the term "Analysis" to highlight that the subsystem performs semantic parsing and entity extraction rather than simple string matching.
* **RuleEngine & ConfidenceEvaluator Separation:** Isolating intent matching from confidence calculation keeps modules simple and allows us to change the confidence weighting logic without modifying keyword rules.
* **Orchestrated Control:** `IntentAnalyzer` acts as a coordinator, ensuring stateless execution and wrapping errors cleanly.
* **Decoupled Decisions:** The subsystem classifies meaning but never decides what action to execute. Execution policies belong in downstream layers.
* **Interchangeable Engine Backend:** Abstracting the parsing logic ensures that migrating from a rule-based engine to a machine-learning engine can be accomplished with zero changes to caller subsystems.
* **Deterministic Behavior:** For the same `ParsedRequest`, analysis engine, and configuration, the Intent Analysis subsystem must always produce the exact same `IntentResult`. Deterministic behavior facilitates testing, simplifies debugging, enables reproducible benchmarks, and guarantees confidence in the overall system architecture.
* **Public Facade Principle:** The only public entry point of this subsystem is `IntentAnalyzer`. `RuleEngine`, `EntityExtractor`, and `ConfidenceEvaluator` must remain internal implementation details and must never be imported directly by other ARGOS subsystems.

---

## 15. Design Philosophy

> "The purpose of the Intent Analysis subsystem is to transform language into structured meaning. It interprets user requests but never decides what actions should be taken. By separating interpretation from planning and execution, ARGOS maintains clean subsystem boundaries and remains extensible as new recognition engines and AI capabilities are introduced."
