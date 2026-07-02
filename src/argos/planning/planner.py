"""Definition of the Planner orchestrator facade class.

This module integrates strategies, thresholds, and container mappings.
"""

import logging

from argos.intent.intent_result import IntentResult
from argos.planning.constants import (
    CONFIDENCE_CLARIFICATION_THRESHOLD,
    CONFIDENCE_CONFIRMATION_THRESHOLD,
    DEFAULT_PLANNING_ENGINE,
)
from argos.planning.exceptions import (
    InvalidIntentResultError,
    PlanningError,
    ProcessingError,
)
from argos.planning.plan import Plan
from argos.planning.strategy import DefaultStrategy, FallbackStrategy, Strategy

logger = logging.getLogger(__name__)


class Planner:
    """Public orchestrator and boundary facade for the planning subsystem.

    Coordinates data validation, strategy selection, step resolution, and DTO mapping.
    """

    def __init__(
        self,
        default_strategy: Strategy | None = None,
        fallback_strategy: Strategy | None = None,
    ) -> None:
        """Initializes the Planner with optional injected strategies.

        Args:
            default_strategy: Optional custom Strategy for standard intent paths.
            fallback_strategy: Optional custom Strategy for fallback paths.
        """
        self._default_strategy = default_strategy or DefaultStrategy()
        self._fallback_strategy = fallback_strategy or FallbackStrategy()

    def plan(self, intent_result: IntentResult) -> Plan:
        """Generates an ordered Plan sequence from a semantic IntentResult.

        Args:
            intent_result: The semantic result of intent analysis.

        Returns:
            A constructed Plan containing recipe steps and configuration flags.

        Raises:
            InvalidIntentResultError: If the input is not an IntentResult instance.
            PlanningError: For subsystem-related validation or strategy
                resolution failures.
            ProcessingError: For unexpected runtime crashes wrapped at the boundary.
        """
        # 1. Type validation
        if not isinstance(intent_result, IntentResult):
            raise InvalidIntentResultError(
                "The provided input must be an instance of IntentResult."
            )

        logger.info(
            "Planning started for primary intent: %s",
            intent_result.primary_intent,
        )
        logger.debug(
            "Incoming entities mapping: %s, confidence: %f",
            intent_result.entities,
            intent_result.confidence,
        )

        try:
            # 2. Select strategy and check confirmation paths based on thresholds
            confidence = intent_result.confidence

            # Fallback path (low confidence or unknown intent)
            if (
                confidence < CONFIDENCE_CLARIFICATION_THRESHOLD
                or intent_result.primary_intent == "unknown"
            ):
                logger.info("Routing request to clarification fallback strategy")
                strategy = self._fallback_strategy
                requires_confirmation = False
            else:
                # Standard path
                strategy = self._default_strategy
                # Confirmation path (confidence between 0.60 and 0.80)
                if confidence < CONFIDENCE_CONFIRMATION_THRESHOLD:
                    logger.info("Plan requires user confirmation prior to execution")
                    requires_confirmation = True
                else:
                    requires_confirmation = False

            # 3. Build plan steps
            steps = strategy.build_steps(intent_result)
            logger.info("Plan steps generation completed successfully")

            # 4. Construct output DTO
            plan_obj = Plan(
                steps=steps,
                primary_intent=intent_result.primary_intent,
                confidence=confidence,
                requires_confirmation=requires_confirmation,
                planning_engine=DEFAULT_PLANNING_ENGINE,
                metadata={
                    "analysis_engine": intent_result.analysis_engine,
                    "request_metadata": intent_result.metadata,
                },
            )
            logger.info("Plan construction completed")
            return plan_obj

        except PlanningError as e:
            logger.error("Planning subsystem exception occurred: %s", str(e))
            raise
        except Exception as e:
            # Wrap any unhandled system crashes in a ProcessingError
            logger.error(
                "Unexpected error in planner orchestrator pipeline: %s",
                str(e),
                exc_info=True,
            )
            raise ProcessingError(
                f"An unexpected error occurred during plan generation: {e}"
            ) from e
