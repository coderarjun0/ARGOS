"""Custom exceptions for the ARGOS intent analysis subsystem.

This module defines the exception hierarchy used throughout the intent pipeline.
All exceptions derive from a common base exception `IntentAnalysisError`.
"""


class IntentAnalysisError(Exception):
    """Base exception for all errors in the ARGOS intent analysis subsystem.

    This exception is caught when handling failures within the intent layer,
    allowing downstream controllers to degrade gracefully.
    """


class ValidationError(IntentAnalysisError):
    """Base exception for all semantic and type validation failures.

    ValidationError is raised when provided data fails type structure, bounds,
    or allowed category checks.
    """


class AnalysisError(IntentAnalysisError):
    """Base exception for internal semantic analysis engine failures.

    AnalysisError represents failures that occur during intent resolution,
    entity parsing, or confidence evaluation steps.
    """


class ProcessingError(IntentAnalysisError):
    """Base exception for general runtime processing failures.

    Reserved for unhandled system failures occurring inside the orchestrator
    pipeline where inputs and engines are valid but processing fails.
    """


class InvalidRequestError(ValidationError):
    """Exception raised when the input request is not an instance of ParsedRequest.

    This enforces type constraints at the public boundary of the intent subsystem.
    """


class UnsupportedIntentError(ValidationError):
    """Exception raised when a classified intent is not in the approved Intent catalog.

    This ensures that downstream systems are never passed unmapped or invalid
    intent classifications.
    """


class InvalidConfidenceError(ValidationError):
    """Exception raised when a calculated confidence score falls outside [0.0, 1.0].

    This ensures that the confidence score adheres strictly to the mathematical
    interval contract.
    """


class RuleEngineError(AnalysisError):
    """Exception raised when the RuleEngine fails during intent mapping.

    This indicates a logic crash or match failure inside the pattern matcher.
    """


class EntityExtractionError(AnalysisError):
    """Exception raised when the EntityExtractor fails to parse text.

    This indicates syntax analysis crashes or extraction regex failure.
    """


class ConfidenceEvaluationError(AnalysisError):
    """Exception raised when the ConfidenceEvaluator fails to calculate score.

    This indicates failure during weight calculations or evaluation rule lookup.
    """
