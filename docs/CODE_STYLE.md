# ARGOS Code Style Guide

This document establishes the official coding standards, architectural principles, and testing guidelines for Project ARGOS. All future subsystems and modules must conform to these rules to maintain consistency, security, and long-term maintainability.

---

## 1. Philosophy

* **Readability Over Cleverness:** Code is read far more often than it is written. Avoid obscure language features, one-liners, or complex optimizations unless backed by profiled benchmarks.
* **Explicit Over Implicit:** Do not rely on hidden side effects, implicit typing, or magic methods. Let the behavior and boundaries of the code be obvious to any engineer reading it.
* **Single Responsibility Principle (SRP):** Every module, class, and function must have exactly one reason to change. Keep files small, cohesive, and focused.
* **Maintainability Over Micro-Optimizations:** Prioritize architectural cleanliness and readability. Do not optimize performance prematurely at the cost of design simplicity.

---

## 2. Python Version

* **Python 3.13+:** Utilize modern Python features (such as `__slots__` in dataclasses, structural pattern matching, and native type piping).
* **Modern Typing Syntax:** Use native pipe unions (`int | None` instead of `Optional[int]`, `list[str]` instead of `List[str]`).
* **Standard Library First:** Leverage built-in packages and modules (such as `dataclasses`, `logging`, and `datetime`) before introducing third-party dependencies.

---

## 3. Naming Conventions

All names must follow standard Python PEP 8 conventions:

* **Packages:** lowercase (e.g., `argos`, `argos.input`).
* **Modules:** `snake_case` (e.g., `input_request.py`, `normalizer.py`).
* **Classes:** `PascalCase` (e.g., `InputProcessor`, `ParsedRequest`).
* **Functions:** `snake_case` (e.g., `process()`, `tokenize()`).
* **Variables:** `snake_case` (e.g., `raw_text`, `normalized_text`).
* **Constants:** `UPPER_CASE` (e.g., `MAX_INPUT_LENGTH`, `SUPPORTED_SOURCES`).
* **Private Members:** Leading single underscore (e.g., `_normalizer`, `_WHITESPACE_PATTERN`).

### Examples
```python
# Constant
MAX_RETRY_COUNT: int = 3

# Class
class QueryProcessor:
    # Private Class Attribute
    _default_delimiter: str = " "

    def __init__(self, delimiter: str | None = None) -> None:
        # Private Instance Attribute
        self._delimiter = delimiter or self._default_delimiter

    # Function / Method
    def parse_query(self, query_text: str) -> list[str]:
        # Variable
        clean_query = query_text.strip()
        return clean_query.split(self._delimiter)
```

---

## 4. Project Structure

ARGOS repository layout uses the standard `src/` layout:

```text
f:/ARGOS/
├── src/                # All production source code
│   └── argos/          # Core package namespace
│       ├── __init__.py
│       └── [subsystem]/# Module folders (e.g., input/, brain/, memory/)
├── tests/              # All unit, integration, and performance tests
├── docs/               # Development documentation and guides
├── specs/              # Official ARGOS Design Specifications (ADS)
├── pyproject.toml      # Dependency declaration and tool configurations
└── README.md           # Project overview
```

### Folder Responsibilities
* **`src/`**: Houses all modular, distributable source code. Subsystems must be isolated in self-contained package folders.
* **`tests/`**: Contains the testing framework duplicating the layout of `src/`. No production code is allowed here.
* **`docs/`**: Includes architectural logs, developer onboarding manuals, style guides, and engineering logs.
* **`specs/`**: Stores approved system designs (ADS files) and Engineering Decision Records (EDRs) acting as the source of architectural truth.

---

## 5. Imports

Imports must be organized cleanly in three sections, separated by blank lines, and sorted alphabetically within each section:

1. **Standard Library Imports** (e.g., `re`, `logging`, `dataclasses`)
2. **Third-Party Imports** (e.g., `pytest`, `numpy`)
3. **ARGOS Internal Module Imports** (e.g., `from argos.input.exceptions import ValidationError`)

### Rules
* **No Wildcard Imports (`from module import *`)**: Always import names explicitly to keep dependencies clear and avoid namespace pollution.
* **Absolute Imports**: Use absolute paths (`from argos.input.normalizer import Normalizer`) rather than relative paths (`from .normalizer import Normalizer`).

---

## 6. Type Hints

ARGOS requires strict static typing across the entire codebase.

* **Parameters & Returns:** Every function and public/private method must define explicit type annotations and return types. Use `-> None` for functions that do not return values.
* **Attributes:** Annotate all class and instance variables.
* **Explicit Collections:** Always type-hint dictionary keys/values and collection elements (e.g., `dict[str, Any]` instead of `dict`, `list[str]` instead of `list`).

---

## 7. Dataclasses

When creating data structures, prefer `dataclasses` over dictionaries or arbitrary class definitions:

* **Use `@dataclass(slots=True)`:** Generates classes with `__slots__` enabled, reducing memory overhead and preventing runtime pollution of instance dictionaries.
* **Avoid Mutable Defaults:** Never assign mutable objects (like lists or dictionaries) directly as default arguments.
* **Use `default_factory`:** Always use `field(default_factory=...)` to assign new instances of mutable types.

### Example
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(slots=True)
class EventData:
    event_id: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## 8. Exceptions

Subsystems must fail gracefully and predictably without exposing inner module details.

* **Boundary Encapsulation:** Never let standard built-in exceptions (e.g., `IndexError`, `KeyError`, `UnicodeEncodeError`) propagate raw past a subsystem boundary.
* **Subsystem Base Exceptions:** Every subsystem must implement a unified custom base exception (e.g., `InputProcessingError`).
* **Specific Subclasses:** Inherit from the subsystem base or validation base to handle distinct error cases (e.g., `EmptyInputError`, `UnsupportedSourceError`).

### Example
```python
# argos/input/exceptions.py
class InputProcessingError(Exception):
    """Base exception for the input subsystem."""

class ValidationError(InputProcessingError):
    """Validation failure exception."""
```

---

## 9. Logging

ARGOS uses standard structured logging to track system states while protecting privacy:

* **`INFO` Level:** Reserved for high-level lifecycle transitions (e.g., "Request received", "Normalization complete", "Task scheduled").
* **`DEBUG` Level:** Reserved for troubleshooting and verbose trace details. Sensitive data, raw user inputs, or generated tokens must **only** be logged at the `DEBUG` level.
* **`ERROR` Level:** Used to log failures, catches, and stack traces when execution degrades.
* **No Secret Leaks:** Do not log secrets, authentication tokens, or sensitive user data (like passwords, keys, or personal text) at `INFO` level or above.

---

## 10. Testing

Testing is an essential requirement of the engineering workflow:

* **Unit Tests Required:** Every new module or functionality must be accompanied by comprehensive tests under the `tests/` directory.
* **Coverage Targets:** 
  * The **minimum** acceptable line coverage is **90%**.
  * The goal for core cognitive and input pipeline modules is **100%**.
* **Path Coverage:** Write tests for both happy path scenarios (standard processing flows) and failure scenarios (crashes, bad inputs, validation errors).
* **Isolation:** Use mock components (`unittest.mock.Mock`) to isolate units of code and assert dependency interaction.

---

## 11. Documentation

All modules, classes, and methods must contain clear, descriptive docstrings in **Google Style**:

* **Module Docstrings:** Placed at the top of every file, detailing what the module contains and its role.
* **Class Docstrings:** Summarizes the class responsibilities and documents attributes.
* **Method/Function Docstrings:** Describes arguments, return types, and exceptions raised.

### Example
```python
def process_data(data: list[str], limit: int) -> int:
    """Filters data items and returns the number of processed records.

    Args:
        data: A list of raw string records.
        limit: The maximum allowed index to process.

    Returns:
        The total count of successfully processed items.

    Raises:
        ValidationError: If the limit is negative or data is empty.
    """
    if limit < 0:
        raise ValidationError("Limit must be positive.")
    ...
```

---

## 12. Architecture Rules

* **Single Responsibility Modules:** Keep helper structures and modules focused. E.g., do not bundle tokenization inside normalizer code.
* **Composition Over Inheritance:** Prefer building objects using smaller components rather than constructing deep, complex class inheritance trees.
* **Dependency Injection:** Inject helper dependencies (such as loggers, normalizers, and parsers) into constructor interfaces rather than hardcoding instantiations. This ensures code is loosely coupled and testable.
* **Respect Subsystem Boundaries:** Higher-level systems (such as the Brain Core) must interact only with a subsystem's public orchestrator facade (e.g., `InputProcessor`), leaving helper components hidden.
* **Typed Models:** Always communicate data between subsystems via typed dataclasses rather than raw strings, tuples, or dictionaries.

---

## 13. Review Checklist

Before opening a pull request or merging a subsystem, verify:

- [ ] All code conforms to **Python 3.13** standards.
- [ ] Explicit type hints are defined for all parameters, returns, and variables.
- [ ] No raw built-in exceptions escape subsystem boundary checks.
- [ ] Logging of sensitive user data or tokens is strictly confined to `DEBUG` levels.
- [ ] imports are alphabetized and ordered correctly.
- [ ] Dataclasses employ `@dataclass(slots=True)` and lack mutable default arguments.
- [ ] Google-style docstrings are present for all public classes, methods, and modules.
- [ ] No wildcard imports are used.
- [ ] Unit tests cover both successful execution paths and validation error paths.
- [ ] Subsystem test coverage meets or exceeds **90%** (100% for core components).
- [ ] Static check analysis (`ruff check`) yields zero warnings or format errors.
