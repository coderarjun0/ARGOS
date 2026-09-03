"""Exception hierarchy for the ARGOS Policy Engine Subsystem."""


class PolicyEngineError(Exception):
    """Base exception for all Policy Engine subsystem errors."""


class PolicyInitializationError(PolicyEngineError):
    """Raised when policy engine initialization or rule loading fails."""


class PolicyValidationError(PolicyEngineError):
    """Raised when a policy rule structural validation fails."""


class PolicyEvaluationError(PolicyEngineError):
    """Raised when a terminal policy evaluation failure or DENY occurs."""
