"""Definition of the IntentResult dataclass.

This module provides the dataclass container representing the semantic output
contract of the intent analysis subsystem.
"""

from dataclasses import dataclass, field
from typing import Any

from argos.intent.intent import Intent


@dataclass(slots=True)
class IntentResult:
    """Represents the structured result of semantic intent analysis.

    This dataclass holds the classified intent, extraction entities, confidence
    levels, and processing metadata. It serves as the data transfer object
    passed to downstream components.

    Attributes:
        primary_intent: The core classified intent of the user.
        confidence: The confidence score assigned to the classification (0.0 to 1.0).
        analysis_engine: The name of the engine that generated this result.
        entities: Dictionary mapping entity categories to lists of parsed target values.
        alternatives: Ordered list of potential alternative intent classifications.
        metadata: Diagnostic context and benchmarking measurements.
    """

    primary_intent: Intent
    confidence: float
    analysis_engine: str
    entities: dict[str, list[str]] = field(default_factory=dict)
    alternatives: list[Intent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
