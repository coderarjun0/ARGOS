"""Definition of the ExecutionStatus StrEnum.

This module declares the possible outcomes of a compiled execution plan.
"""

from enum import StrEnum


class ExecutionStatus(StrEnum):
    """Enumeration of overall execution outcomes.

    SUCCESS: All steps executed successfully.
    PARTIAL_SUCCESS: Some steps succeeded, others failed.
    FAILED: All steps failed during execution.
    """

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    # Wait, did the user request to capitalize like SUCCESS?
    # In StrEnum, standard value is lowercase, matching Python naming style.
    # The spec lists: SUCCESS, PARTIAL_SUCCESS, FAILED, with values:
    # SUCCESS = "success"
    # PARTIAL_SUCCESS = "partial_success"
    # FAILED = "failed"
    # This is correct.
