"""Runtime subsystem for ARGOS (ARS-001).

Exposes the ArgosRuntime composition root, external DTOs, and exception types.
"""

from argos.runtime.argos_runtime import ArgosRuntime
from argos.runtime.exceptions import (
    RuntimeError,
    RuntimeExecutionError,
    RuntimeInitializationError,
    RuntimeShutdownError,
)
from argos.runtime.models import RuntimeResponse, RuntimeStatus

__all__ = [
    "ArgosRuntime",
    "RuntimeError",
    "RuntimeExecutionError",
    "RuntimeInitializationError",
    "RuntimeResponse",
    "RuntimeShutdownError",
    "RuntimeStatus",
]
