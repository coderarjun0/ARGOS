"""State and status enumerations for the ARGOS Brain Core subsystem.

Defines the coarse public session status (BrainStatus) and the internal
cognitive lifecycle phases (CognitiveState) according to ADS-005.
"""

from enum import StrEnum


class BrainStatus(StrEnum):
    """Public lifecycle status of the Brain Core session and BrainResult.

    Represents the coarse outcome or current operational status of the brain.
    """

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class CognitiveState(StrEnum):
    """Internal cognitive phases representing the reasoning loop lifecycle.

    These represent internal cognitive phases rather than execution state,
    tracking progression through the reasoning loop:
    IDLE -> PERCEIVING -> INTERPRETING -> REASONING -> PLANNING / EXECUTING
    -> EVALUATING -> WAITING_FOR_USER / COMPLETED / FAILED / TERMINATED.
    """

    IDLE = "IDLE"
    PERCEIVING = "PERCEIVING"
    INTERPRETING = "INTERPRETING"
    REASONING = "REASONING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    EVALUATING = "EVALUATING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"
