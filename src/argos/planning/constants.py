"""Configuration constants for the ARGOS planning subsystem.

This module houses the default planning engine identification, confidence thresholds,
and status strings.
"""

from typing import Final

# Default engine identification string for telemetry
DEFAULT_PLANNING_ENGINE: Final[str] = "rule_planner"

# Confidence thresholds for planning workflow routing
CONFIDENCE_CONFIRMATION_THRESHOLD: Final[float] = 0.80
CONFIDENCE_CLARIFICATION_THRESHOLD: Final[float] = 0.60
