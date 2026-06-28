"""Definition of the ConfidenceEvaluator class.

This module implements the heuristic calculations to assign a numerical
confidence score to the semantic intent analysis result.
"""

from typing import Final

from argos.intent.exceptions import InvalidConfidenceError, ValidationError
from argos.intent.intent import Intent

# Mathematical bounds for confidence scores
MIN_CONFIDENCE: Final[float] = 0.0
MAX_CONFIDENCE: Final[float] = 1.0


class ConfidenceEvaluator:
    """Evaluates the confidence score of intent analysis results.

    This class is stateless and deterministic. It uses heuristic analysis of
    rule matches, alternative candidates, and entity completeness to estimate
    a score between 0.0 and 1.0.
    """

    def evaluate(
        self,
        primary_intent: Intent,
        alternatives: list[Intent],
        entities: dict[str, list[str]],
    ) -> float:
        """Heuristically calculates a confidence score for classified intent.

        Args:
            primary_intent: The primary classified Intent enum.
            alternatives: List of secondary alternative Intent candidates.
            entities: Dictionary of extracted entities.

        Returns:
            A float confidence score between 0.0 and 1.0.

        Raises:
            ValidationError: If input parameters violate type assertions.
            InvalidConfidenceError: If calculated confidence falls outside bounds.
        """
        # 1. Type validation
        if not isinstance(primary_intent, Intent):
            raise ValidationError(
                "primary_intent must be an instance of Intent StrEnum."
            )
        if not isinstance(alternatives, list):
            raise ValidationError("alternatives must be a list of Intent enums.")
        if not all(isinstance(alt, Intent) for alt in alternatives):
            raise ValidationError(
                "All items in alternatives must be instances of Intent."
            )
        if not isinstance(entities, dict):
            raise ValidationError("entities must be a dictionary.")

        # 2. Heuristic scoring logic
        # If intent could not be identified, confidence is absolute zero
        if primary_intent == Intent.UNKNOWN:
            return MIN_CONFIDENCE

        # Baseline confidence for a matched rule pattern
        score = 0.85

        # Penalty for ambiguity: each candidate alternative reduces confidence
        ambiguity_penalty = len(alternatives) * 0.05
        score -= ambiguity_penalty

        # Bonus for completeness: presence of target parameters (entities)
        # indicates a more complete and actionable command.
        # We add 0.05 for each unique entity category found, up to a max of 0.15
        entity_bonus = len(entities) * 0.05
        score += min(entity_bonus, 0.15)

        # 3. Clamping and boundary checks
        clamped_score = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, score))

        # Enforce mathematical contract bounds
        if not (MIN_CONFIDENCE <= clamped_score <= MAX_CONFIDENCE):
            raise InvalidConfidenceError(
                f"Calculated confidence {clamped_score} is out of boundaries "
                f"[{MIN_CONFIDENCE}, {MAX_CONFIDENCE}]."
            )

        return float(round(clamped_score, 2))
