"""Custom exceptions for the ARGOS execution subsystem.

This module defines a structured exception hierarchy to ensure no internal details
leak through the subsystem boundary.
"""


class ExecutionError(Exception):
    """Base exception for all errors in the ARGOS execution subsystem.

    This exception is caught when handling failures within the execution layer,
    allowing downstream controllers to degrade gracefully.
    """


class ValidationError(ExecutionError):
    """Base exception for all type structure and semantic validation failures."""


class InvalidPlanError(ValidationError):
    """Exception raised when the input is not an instance of Plan."""


class InvalidStepError(ValidationError):
    """Exception raised when a step structure or parameter set is invalid."""


class RoutingError(ExecutionError):
    """Exception raised when the router fails to find an executor for an action type."""


class ExecutorError(ExecutionError):
    """Exception raised when an individual executor fails during execution."""


class ProcessingError(ExecutionError):
    """Exception raised when an unexpected runtime failure occurs.

    Raised inside the pipeline.
    """
