"""Definition of the ExecutionEngine facade class.

This module coordinates plan validation, step-by-step routing, result aggregation,
Layer 2 Policy Gateway enforcement, and exception boundary translations.
"""

import logging
from typing import Any

from argos.execution.action_executor import ActionExecutor
from argos.execution.action_router import ActionRouter
from argos.execution.application_executor import ApplicationExecutor
from argos.execution.constants import (
    DEFAULT_EXECUTION_ENGINE,
    MAX_PLAN_STEPS,
    MAX_STEP_MESSAGE_LENGTH,
)
from argos.execution.exceptions import (
    ExecutionError,
    InvalidPlanError,
    InvalidStepError,
    ProcessingError,
    ValidationError,
)
from argos.execution.execution_aggregator import ExecutionAggregator
from argos.execution.execution_result import ExecutionResult
from argos.execution.file_executor import FileExecutor
from argos.execution.step_result import StepResult
from argos.execution.system_executor import SystemExecutor
from argos.execution.web_executor import WebExecutor
from argos.planning.action import Action
from argos.planning.plan import Plan
from argos.planning.plan_step import PlanStep
from argos.policy.models import PolicyOutcome
from argos.policy.policy_engine import PolicyEngine

logger = logging.getLogger(__name__)


class _ClarificationExecutor(ActionExecutor):
    """Internal executor handling plan clarification steps."""

    def execute(self, step: PlanStep) -> StepResult:
        if step.action != Action.ASK_CLARIFICATION:
            raise InvalidStepError(
                f"_ClarificationExecutor cannot execute action: {step.action}"
            )
        msg = step.parameters.get("message", "Clarification requested.")
        return StepResult(
            step_id=step.step_id,
            action=step.action,
            success=True,
            message=msg,
        )


class ExecutionEngine:
    """Public facade for orchestrating Plan execution.

    Coordinates validators, routers, executors, Layer 2 Policy Gateway, and
    result aggregators. Supports constructor dependency injection.
    """

    def __init__(
        self,
        router: ActionRouter | None = None,
        aggregator: ExecutionAggregator | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        """Initializes the ExecutionEngine with optional injected components.

        Args:
            router: Optional custom ActionRouter instance.
            aggregator: Optional custom ExecutionAggregator instance.
            policy_engine: Optional custom PolicyEngine instance.
        """
        self._router = router or self._build_default_router()
        self._aggregator = aggregator or ExecutionAggregator()
        self._policy_engine = policy_engine or PolicyEngine()

    @property
    def policy_engine(self) -> PolicyEngine:
        """Public access to underlying PolicyEngine instance."""
        return self._policy_engine

    def _build_default_router(self) -> ActionRouter:
        """Creates the default ActionRouter and registers concrete executors."""
        router = ActionRouter()
        app_exec = ApplicationExecutor()
        file_exec = FileExecutor()
        web_exec = WebExecutor()
        sys_exec = SystemExecutor()

        # Register standard mappings
        router.register(Action.OPEN_APP, app_exec)
        router.register(Action.CLOSE_APP, app_exec)
        router.register(Action.CREATE_FILE, file_exec)
        router.register(Action.READ_FILE, file_exec)
        router.register(Action.WRITE_FILE, file_exec)
        router.register(Action.DELETE_FILE, file_exec)
        router.register(Action.SEARCH_WEB, web_exec)
        router.register(Action.RUN_COMMAND, sys_exec)

        # Register clarification mapping
        router.register(Action.ASK_CLARIFICATION, _ClarificationExecutor())

        return router

    def execute(self, plan: Plan, authorization: Any | None = None) -> ExecutionResult:
        """Orchestrates sequential execution of plan steps through Policy Gateway.

        Args:
            plan: The Plan object containing recipe steps.
            authorization: Optional user authorization record.

        Returns:
            An ExecutionResult compiled from step results.

        Raises:
            InvalidPlanError: If the input is not a Plan instance.
            ValidationError: If plan steps count exceeds threshold boundaries.
            ExecutionError: For general subsystem-related execution crashes.
            ProcessingError: For unexpected runtime system crashes
                wrapped at the boundary.
        """
        # 1. Type validation
        if not isinstance(plan, Plan):
            raise InvalidPlanError(
                "The provided plan must be an instance of Plan."
            )

        # 2. Limit boundary verification
        if len(plan.steps) > MAX_PLAN_STEPS:
            raise ValidationError(
                f"Plan steps count {len(plan.steps)} exceeds maximum limit "
                f"of {MAX_PLAN_STEPS} steps."
            )

        logger.info(
            "Execution started for engine: %s",
            DEFAULT_EXECUTION_ENGINE,
        )
        logger.debug(
            "Executing plan with %d steps for intent: %s",
            len(plan.steps),
            plan.primary_intent,
        )

        step_results: list[StepResult] = []

        try:
            # 3. Iterate, evaluate policy, and route steps
            for step in plan.steps:
                logger.info("Executing step ID: %d", step.step_id)
                logger.debug(
                    "Routing step action: %s, parameters: %s",
                    step.action,
                    step.parameters,
                )

                # Layer 2 Policy Gateway Execution Action Evaluation
                action_str = (
                    step.action.value
                    if hasattr(step.action, "value")
                    else str(step.action)
                )
                target_str = (
                    step.parameters.get("target") or step.parameters.get("path")
                )
                decision = self._policy_engine.evaluate_action(
                    action=action_str,
                    target=str(target_str) if target_str is not None else None,
                    parameters=step.parameters,
                )

                if decision.outcome == PolicyOutcome.DENY:
                    logger.warning(
                        "Step %d denied by Layer 2 Policy: %s",
                        step.step_id,
                        decision.explanation,
                    )
                    step_result = StepResult(
                        step_id=step.step_id,
                        action=step.action,
                        success=False,
                        message=f"Policy DENY: {decision.explanation}",
                    )
                    step_results.append(step_result)
                    break

                if decision.outcome in (
                    PolicyOutcome.REQUIRE_CONFIRMATION,
                    PolicyOutcome.REQUIRE_AUTHORIZATION,
                ):
                    auth = step.parameters.get("authorization") or authorization
                    if not auth or getattr(auth, "granted", False) is not True:
                        logger.info(
                            "Step %d requires policy confirmation: %s",
                            step.step_id,
                            decision.explanation,
                        )
                        step_result = StepResult(
                            step_id=step.step_id,
                            action=step.action,
                            success=False,
                            message=f"Policy requirement: {decision.explanation}",
                        )
                        step_results.append(step_result)
                        break

                executor = self._router.route(step.action)
                step_result = executor.execute(step)

                # 4. Truncate long confirmation messages to stay within safety limits
                msg = step_result.message
                if len(msg) > MAX_STEP_MESSAGE_LENGTH:
                    msg = msg[:MAX_STEP_MESSAGE_LENGTH]
                    step_result = StepResult(
                        step_id=step_result.step_id,
                        action=step_result.action,
                        success=step_result.success,
                        message=msg,
                        metadata=step_result.metadata,
                    )

                step_results.append(step_result)

                if not step_result.success:
                    break

            # 5. Compile results using aggregator
            status = self._aggregator.aggregate(step_results)
            logger.info("Execution completed with status: %s", status)

            result = ExecutionResult(
                status=status,
                step_results=step_results,
                execution_engine=DEFAULT_EXECUTION_ENGINE,
                metadata={
                    "plan_intent": plan.primary_intent,
                    "requires_confirmation": plan.requires_confirmation,
                },
            )
            return result

        except ExecutionError as e:
            logger.error("Execution subsystem exception occurred: %s", str(e))
            raise
        except Exception as e:
            # Wrap any unhandled system crashes in a ProcessingError
            logger.error(
                "Unexpected error in execution engine pipeline: %s",
                str(e),
                exc_info=True,
            )
            raise ProcessingError(
                f"An unexpected error occurred during execution: {e}"
            ) from e
