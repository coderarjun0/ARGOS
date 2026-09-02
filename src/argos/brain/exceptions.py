"""Custom exception hierarchy for the ARGOS Brain Core subsystem.

All custom errors inherit from BrainError. Subsystem and capability exceptions
are caught at the boundary and wrapped in ProcessingError to preserve subsystem
isolation.
"""


class BrainError(Exception):
    """Base exception for all errors raised within the Brain Core subsystem."""


class ValidationError(BrainError):
    """Raised when input parameters, configurations, or structures fail validation."""


class ProcessingError(BrainError):
    """Raised when an unexpected error or wrapped capability exception occurs."""


class CapabilityNotFoundError(ValidationError):
    """Raised when an operation requests a capability that is not registered."""


class MaxCyclesExceededError(ProcessingError):
    """Raised when the cognitive loop exceeds its maximum iteration threshold."""
