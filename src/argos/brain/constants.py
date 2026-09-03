"""Core constants and limits for the ARGOS Brain Core subsystem.

This module defines system identifiers, iteration boundaries, and confidence
thresholds governing cognitive loop execution.
"""

# Default identifier for the Brain Core engine (ADS-005 Section 10).
DEFAULT_BRAIN_ENGINE: str = "argos-brain-v1"

# Maximum number of cognitive loop cycles before triggering infinite loop
# safeguards (ADS-005 Section 14 limit safeguards policy).
DEFAULT_MAX_COGNITIVE_CYCLES: int = 10

# Confidence threshold above which plans can execute directly without
# requiring user confirmation (aligned with ADS-003 / EDR-015 policy).
CONFIRMATION_CONFIDENCE_THRESHOLD: float = 0.80

# Confidence threshold below which intents require user clarification
# rather than execution (aligned with ADS-003 / EDR-015 policy).
CLARIFICATION_CONFIDENCE_THRESHOLD: float = 0.60

# Maximum number of goals tracked in Working Memory / Goal Manager simultaneously.
MAX_GOALS_TRACKED: int = 50

# Standard capability names registered within the Brain Core.
CAPABILITY_INPUT: str = "input_processing"
CAPABILITY_INTENT: str = "intent_analysis"
CAPABILITY_PLANNING: str = "planning"
CAPABILITY_EXECUTION: str = "execution"
CAPABILITY_MEMORY: str = "memory"
