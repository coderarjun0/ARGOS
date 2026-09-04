"""Exception hierarchy for the ARGOS Real Tool Runtime subsystem."""


class ToolError(Exception):
    """Base exception for all tool execution failures."""


class InvalidParameterError(ToolError):
    """Raised when tool parameters fail validation."""


class ToolRegistrationError(ToolError):
    """Raised when tool registration in ToolRegistry fails."""


class ToolNotFoundError(ToolError):
    """Raised when requested tool ID is not registered."""


class PlatformExecutionError(ToolError):
    """Raised when platform OS execution encounters an unrecoverable failure."""
