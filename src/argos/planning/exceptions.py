"""Custom exceptions for the ARGOS planning subsystem.

This module defines a structured exception hierarchy to ensure no internal details
leak through the subsystem boundary.
"""


class PlanningError(Exception):
    """Base exception for all errors in the ARGOS planning subsystem.

    This exception is caught when handling failures within the planning layer,
    allowing downstream controllers to degrade gracefully.
    """


class ValidationError(PlanningError):
    """Base exception for all type structure and semantic validation failures."""


class InvalidIntentResultError(ValidationError):
    """Exception raised when the input result is not an instance of IntentResult."""


class InvalidParameterError(ValidationError):
    """Exception raised when generated plan steps have invalid parameters."""


class StrategyResolutionError(PlanningError):
    """Exception raised when the planning strategy fails to construct steps."""


class ProcessingError(PlanningError):
    """Exception raised when an unexpected runtime failure occurs.

    Raised inside the pipeline.
    """
