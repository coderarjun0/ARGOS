"""Domain-specific exception hierarchy for the ARGOS Memory subsystem (ADS-006).

All memory exceptions inherit from MemoryError, keeping the subsystem completely
independent of argos.brain exceptions and preserving 100% dependency inversion.
"""


class MemoryError(Exception):
    """Base exception for all errors originating within the memory subsystem."""


class MemoryValidationError(MemoryError):
    """Raised when key, category, scope, session ID, or payload validation fails."""


class MemoryStorageError(MemoryError):
    """Raised when SQLite storage access, commit, disk I/O, or corruption fails."""


class MemoryAuthorizationError(MemoryError):
    """Raised when persistent memory mutation lacks valid user consent."""


class MemoryNotFoundError(MemoryError):
    """Raised when an operation targets a non-existent category and key."""
