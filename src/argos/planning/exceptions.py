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


class SchemaValidationError(ValidationError):
    """Base exception for parameter schema validation errors."""


class MissingParameterError(SchemaValidationError):
    """Exception raised when a required parameter is missing from planning input."""


class ReservedParameterError(SchemaValidationError):
    """Exception raised when parameter key starts with reserved prefix ('_')."""


class InvalidParameterError(SchemaValidationError):
    """Exception raised when generated plan steps have invalid parameters."""


class StrategyResolutionError(PlanningError):
    """Exception raised when the planning strategy fails to construct steps."""


class UnsupportedActionError(StrategyResolutionError):
    """Exception raised when action is unsupported by capability domains."""


class AmbiguousPlannerActionError(StrategyResolutionError):
    """Exception raised when multiple tools match action without tool hint."""



class ProcessingError(PlanningError):
    """Exception raised when an unexpected runtime failure occurs.

    Raised inside the pipeline.
    """

