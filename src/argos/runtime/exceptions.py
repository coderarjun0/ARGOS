"""Exceptions for the ARGOS runtime subsystem."""


class RuntimeError(Exception):
    """Base exception for all ARGOS runtime errors."""

    pass


class RuntimeInitializationError(RuntimeError):
    """Raised when runtime initialization or dependency wiring fails."""

    pass


class RuntimeExecutionError(RuntimeError):
    """Raised when request execution through the runtime fails unexpectedly."""

    pass


class RuntimeShutdownError(RuntimeError):
    """Raised when an operation is performed on a shutdown runtime."""

    pass
