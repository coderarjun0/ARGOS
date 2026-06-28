"""Public API boundary for the ARGOS Intent Analysis subsystem.

This module exposes only the components intended for public consumption by other
subsystems (e.g., the Brain Core and the Planner). All internal helper engines
(RuleEngine, EntityExtractor, and ConfidenceEvaluator) remain encapsulated.
"""

from argos.intent.analyzer import IntentAnalyzer
from argos.intent.exceptions import (
    AnalysisError,
    ConfidenceEvaluationError,
    EntityExtractionError,
    IntentAnalysisError,
    InvalidConfidenceError,
    InvalidRequestError,
    ProcessingError,
    RuleEngineError,
    UnsupportedIntentError,
    ValidationError,
)
from argos.intent.intent import Intent
from argos.intent.intent_result import IntentResult

__all__ = [
    "IntentAnalyzer",
    "Intent",
    "IntentResult",
    "IntentAnalysisError",
    "ValidationError",
    "InvalidRequestError",
    "UnsupportedIntentError",
    "InvalidConfidenceError",
    "AnalysisError",
    "RuleEngineError",
    "EntityExtractionError",
    "ConfidenceEvaluationError",
    "ProcessingError",
]
