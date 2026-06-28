"""Definition of the IntentAnalyzer class.

This module provides the public orchestrator class for the intent analysis layer,
integrating intent classification, parameter extraction, and scoring.
"""

import logging

from argos.input.parsed_request import ParsedRequest
from argos.intent.confidence_evaluator import ConfidenceEvaluator
from argos.intent.constants import DEFAULT_ANALYSIS_ENGINE
from argos.intent.entity_extractor import EntityExtractor
from argos.intent.exceptions import (
    IntentAnalysisError,
    InvalidRequestError,
    ProcessingError,
)
from argos.intent.intent_result import IntentResult
from argos.intent.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """Public facade for orchestrating user intent analysis.

    This class serves as the sole external interface for the intent subsystem,
    coordinating internal components (RuleEngine, EntityExtractor,
    ConfidenceEvaluator) via dependency injection.
    """

    def __init__(
        self,
        rule_engine: RuleEngine | None = None,
        entity_extractor: EntityExtractor | None = None,
        confidence_evaluator: ConfidenceEvaluator | None = None,
    ) -> None:
        """Initializes the IntentAnalyzer with optional injected components.

        Args:
            rule_engine: Optional custom RuleEngine implementation.
            entity_extractor: Optional custom EntityExtractor implementation.
            confidence_evaluator: Optional custom ConfidenceEvaluator implementation.
        """
        self._rule_engine = rule_engine or RuleEngine()
        self._entity_extractor = entity_extractor or EntityExtractor()
        self._confidence_evaluator = confidence_evaluator or ConfidenceEvaluator()

    def analyze(self, request: ParsedRequest) -> IntentResult:
        """Performs semantic classification and entity parsing on a parsed request.

        Args:
            request: The parsed, tokenized request to analyze.

        Returns:
            An IntentResult containing intent, confidence, entities, and metadata.

        Raises:
            InvalidRequestError: If request is not an instance of ParsedRequest.
            IntentAnalysisError: If any pipeline validation or parsing check fails.
            ProcessingError: For unexpected runtime system failures.
        """
        # 1. Validate request type
        if not isinstance(request, ParsedRequest):
            raise InvalidRequestError(
                "The provided request must be an instance of ParsedRequest."
            )

        logger.info("Intent analysis started for source: %s", request.source)
        logger.debug("Parsing normalized text: %r", request.normalized_text)

        try:
            # 2. Classify intent
            primary_intent, alternatives = self._rule_engine.classify(request)
            logger.info("Intent classification completed")
            logger.debug(
                "Primary Intent: %s, Alternatives: %s",
                primary_intent,
                alternatives,
            )

            # 3. Extract entities
            entities = self._entity_extractor.extract(request)
            logger.info("Entity extraction completed")
            logger.debug("Extracted entities: %s", entities)

            # 4. Evaluate confidence
            confidence = self._confidence_evaluator.evaluate(
                primary_intent=primary_intent,
                alternatives=alternatives,
                entities=entities,
            )
            logger.info("Confidence evaluation completed")
            logger.debug("Confidence score: %f", confidence)

            # 5. Build final IntentResult DTO
            result = IntentResult(
                primary_intent=primary_intent,
                confidence=confidence,
                analysis_engine=DEFAULT_ANALYSIS_ENGINE,
                entities=entities,
                alternatives=alternatives,
                metadata={
                    "request_timestamp": request.timestamp.isoformat(),
                    "source": request.source,
                },
            )
            logger.info("Intent analysis result constructed successfully")
            return result

        except IntentAnalysisError as e:
            logger.error("Intent analysis exception occurred: %s", str(e))
            raise
        except Exception as e:
            # Wrap any unhandled core/system exceptions in a ProcessingError
            logger.error(
                "Unexpected error in intent analyzer pipeline: %s",
                str(e),
                exc_info=True,
            )
            raise ProcessingError(
                f"An unexpected error occurred during intent analysis: {e}"
            ) from e
