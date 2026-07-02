"""Configuration constants for the ARGOS execution subsystem.

This module houses the default execution engine identification, step limits,
and length limitations.
"""

from typing import Final

# Default engine identification string for telemetry
DEFAULT_EXECUTION_ENGINE: Final[str] = "mock_execution_engine"

# Subsystem limits
MAX_PLAN_STEPS: Final[int] = 100
MAX_STEP_MESSAGE_LENGTH: Final[int] = 1024
