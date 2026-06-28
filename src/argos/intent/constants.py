"""Configuration constants for the ARGOS intent analysis subsystem.

This module isolates configurable parameters, boundary limits, and threshold
values used during intent classification, entity extraction, and confidence evaluation.
"""

from typing import Final

# Thresholds for classification confidence levels
CONFIDENCE_VERY_HIGH: Final[float] = 0.95
CONFIDENCE_HIGH: Final[float] = 0.80
CONFIDENCE_MEDIUM: Final[float] = 0.60

# Safety boundary limits to prevent resource exhaustion
MAX_ENTITY_LENGTH: Final[int] = 512
MAX_ALTERNATIVE_INTENTS: Final[int] = 5

# Subsystem metadata settings
DEFAULT_ANALYSIS_ENGINE: Final[str] = "rule_engine"
