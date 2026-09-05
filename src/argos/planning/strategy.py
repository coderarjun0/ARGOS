"""Definition of the Strategy ABC and concrete implementation classes.

This module provides the abstract base class Strategy and the deterministic
rule-based DefaultStrategy and FallbackStrategy implementations.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from argos.intent import Intent
from argos.intent.intent_result import IntentResult
from argos.planning.action import Action
from argos.planning.exceptions import (
    InvalidParameterError,
    MissingParameterError,
    UnsupportedActionError,
)
from argos.planning.plan_step import PlanStep
from argos.planning.validator import SchemaValidator

if TYPE_CHECKING:
    from argos.capabilities.capability_registry import CapabilityRegistry
    from argos.capabilities.models import ActionSchemaDescriptor



class Strategy(ABC):
    """Abstract Base Class for planning strategies."""

    @abstractmethod
    def build_steps(self, intent_result: IntentResult) -> list[PlanStep]:
        """Builds plan steps based on a semantic intent result.

        Args:
            intent_result: The semantic output of intent analysis.

        Returns:
            A list of ordered PlanStep objects.
        """


class DefaultStrategy(Strategy):
    """Deterministic rule-based planning strategy for valid intent requests."""

    def build_steps(self, intent_result: IntentResult) -> list[PlanStep]:
        """Maps standard intent parameters to atomic actions."""
        intent = intent_result.primary_intent
        entities = intent_result.entities
        steps: list[PlanStep] = []

        if intent == Intent.OPEN_APPLICATION:
            apps = entities.get("application", [])
            if not apps:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={
                            "message": "Please specify an application to open."
                        },
                    )
                )
            else:
                for i, app in enumerate(apps, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.OPEN_APP,
                            parameters={"application": app},
                        )
                    )

        elif intent == Intent.CLOSE_APPLICATION:
            apps = entities.get("application", [])
            if not apps:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={
                            "message": "Please specify an application to close."
                        },
                    )
                )
            else:
                for i, app in enumerate(apps, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.CLOSE_APP,
                            parameters={"application": app},
                        )
                    )

        elif intent in (Intent.OPEN_FILE, Intent.READ_FILE):
            files = entities.get("file", [])
            if not files:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={"message": "Please specify a file to read."},
                    )
                )
            else:
                for i, file in enumerate(files, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.READ_FILE,
                            parameters={"file_path": file},
                        )
                    )

        elif intent == Intent.CREATE_FILE:
            files = entities.get("file", [])
            if not files:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={"message": "Please specify a file to create."},
                    )
                )
            else:
                for i, file in enumerate(files, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.CREATE_FILE,
                            parameters={"file_path": file},
                        )
                    )

        elif intent == Intent.DELETE_FILE:
            files = entities.get("file", [])
            folders = entities.get("folder", [])
            targets = files + folders
            if not targets:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={
                            "message": (
                                "Please specify a file or folder to delete."
                            )
                        },
                    )
                )
            else:
                for i, target in enumerate(targets, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.DELETE_FILE,
                            parameters={"target": target},
                        )
                    )

        elif intent == Intent.WRITE_FILE:
            files = entities.get("file", [])
            if not files:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={"message": "Please specify a file to write to."},
                    )
                )
            else:
                for i, file in enumerate(files, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.WRITE_FILE,
                            parameters={"file_path": file},
                        )
                    )

        elif intent == Intent.SEARCH_WEB:
            urls = entities.get("url", [])
            websites = entities.get("website", [])
            queries = urls + websites
            if not queries:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={"message": "Please specify a web search query."},
                    )
                )
            else:
                for i, query in enumerate(queries, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.SEARCH_WEB,
                            parameters={"query": query},
                        )
                    )

        elif intent == Intent.RUN_COMMAND:
            commands = entities.get("command", [])
            if not commands:
                steps.append(
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={"message": "Please specify a command to run."},
                    )
                )
            else:
                for i, cmd in enumerate(commands, 1):
                    steps.append(
                        PlanStep(
                            step_id=i,
                            action=Action.RUN_COMMAND,
                            parameters={"command": cmd},
                        )
                    )

        else:
            # Fallback for remaining intents (GET_INFORMATION, CONTROL_SYSTEM,
            # SET_REMINDER)
            steps.append(
                PlanStep(
                    step_id=1,
                    action=Action.ASK_CLARIFICATION,
                    parameters={
                        "message": f"Intent '{intent}' requires manual confirmation."
                    },
                )
            )

        return steps


class FallbackStrategy(Strategy):
    """Planner strategy for unknown or low-confidence intent requests."""

    def build_steps(self, intent_result: IntentResult) -> list[PlanStep]:
        """Returns a single clarification request step."""
        return [
            PlanStep(
                step_id=1,
                action=Action.ASK_CLARIFICATION,
                parameters={
                    "message": (
                        f"Could not resolve intent '{intent_result.primary_intent}' "
                        f"with confidence {intent_result.confidence}."
                    )
                },
            )
        ]



class SchemaAwareStrategy(Strategy):
    """Base Class for strategies utilizing CapabilityRegistry metadata."""

    def __init__(self, capability_registry: CapabilityRegistry | None = None) -> None:
        """Initializes SchemaAwareStrategy with an optional CapabilityRegistry.

        Args:
            capability_registry: Read-only CapabilityRegistry instance.
        """
        self._capability_registry = capability_registry

    @property
    def capability_registry(self) -> CapabilityRegistry | None:
        """Returns the injected CapabilityRegistry instance."""
        return self._capability_registry


class DomainPlannerStrategy(SchemaAwareStrategy):
    """Domain-based strategy validating parameter schemas via CapabilityRegistry."""

    def build_steps(self, intent_result: IntentResult) -> list[PlanStep]:
        """Maps intent result to domain actions and validates schemas."""
        from argos.capabilities.exceptions import (
            ActionNotFoundError,
            AmbiguousActionError,
        )

        intent = intent_result.primary_intent
        entities = intent_result.entities or {}

        # 1. Map intent to target Action
        target_action: Action
        if intent == Intent.OPEN_APPLICATION:
            target_action = Action.OPEN_APP
        elif intent == Intent.CLOSE_APPLICATION:
            target_action = Action.CLOSE_APP
        elif intent in (Intent.OPEN_FILE, Intent.READ_FILE):
            target_action = Action.READ_FILE
        elif intent == Intent.CREATE_FILE:
            target_action = Action.CREATE_FILE
        elif intent == Intent.WRITE_FILE:
            target_action = Action.WRITE_FILE
        elif intent == Intent.SEARCH_WEB:
            target_action = Action.SEARCH_WEB
        elif intent in (Intent.CONTROL_SYSTEM, Intent.GET_INFORMATION):
            target_action = Action.QUERY_SYS_INFO
        else:
            # Intents outside ARS-004 domain mapping (DELETE_FILE, RUN_COMMAND, etc.)
            raise UnsupportedActionError(
                f"Action for intent '{intent}' is unsupported by domain capabilities."
            )

        # 2. Resolve ActionSchemaDescriptor from CapabilityRegistry
        schema: ActionSchemaDescriptor

        try:
            if self._capability_registry is None:
                raise UnsupportedActionError("CapabilityRegistry is not configured.")
            schema = self._capability_registry.get_schema_for_action(target_action)
        except ActionNotFoundError as err:
            raise UnsupportedActionError(
                f"Action '{target_action.value}' is unsupported by capability domains."
            ) from err
        except AmbiguousActionError as err:
            # Check candidate tool hint
            tool_hint = (
                entities.get("tool_id")
                or entities.get("tool")
                or intent_result.metadata.get("tool_id")
            )
            if isinstance(tool_hint, list) and tool_hint:
                tool_hint = tool_hint[0]

            matching_schema: ActionSchemaDescriptor | None = None
            if tool_hint and isinstance(tool_hint, str):
                all_schemas = self._capability_registry.get_action_schemas()
                candidates = [
                    s
                    for s in all_schemas
                    if s.action == target_action and s.tool_id == tool_hint
                ]
                if len(candidates) == 1:
                    matching_schema = candidates[0]

            if matching_schema is not None:
                schema = matching_schema
            else:
                act_str = target_action.value
                return [
                    PlanStep(
                        step_id=1,
                        action=Action.ASK_CLARIFICATION,
                        parameters={
                            "message": f"Multiple tools for action '{act_str}'."
                        },
                        metadata={"candidate_tools": str(err)},
                    )
                ]



        # 3. Extract and map entity parameters
        raw_parameters = self._extract_raw_parameters(target_action, entities)

        # 4. Validate parameters using SchemaValidator
        try:
            validated_params, unmapped_entities = (
                SchemaValidator.validate_and_coerce(schema, raw_parameters)
            )
        except (MissingParameterError, InvalidParameterError) as err:
            return [
                PlanStep(
                    step_id=1,
                    action=Action.ASK_CLARIFICATION,
                    parameters={"message": str(err)},
                )
            ]

        # 5. Build output PlanStep with isolated metadata
        step_metadata: dict[str, Any] = {}
        if unmapped_entities:
            step_metadata["unmapped_entities"] = unmapped_entities

        return [
            PlanStep(
                step_id=1,
                action=target_action,
                parameters=validated_params,
                metadata=step_metadata,
            )
        ]

    def _extract_raw_parameters(
        self, action: Action, entities: dict[str, Any]
    ) -> dict[str, Any]:
        """Extracts raw parameter dictionary from intent entities."""
        raw: dict[str, Any] = {}
        for k, v in entities.items():
            val = v[0] if isinstance(v, list) and len(v) > 0 else v
            raw[k] = val

        # Handle canonical entity key aliases per action
        if action in (Action.OPEN_APP, Action.CLOSE_APP):
            if "app" in raw and "application" not in raw:
                raw["application"] = raw.pop("app")
        elif action in (Action.READ_FILE, Action.CREATE_FILE, Action.WRITE_FILE):
            if "file" in raw and "file_path" not in raw:
                raw["file_path"] = raw.pop("file")
            if "target" in raw and "file_path" not in raw:
                raw["file_path"] = raw.pop("target")
        elif action == Action.SEARCH_WEB:
            if "url" in raw and "query" not in raw:
                raw["query"] = raw.pop("url")
            elif "website" in raw and "query" not in raw:
                raw["query"] = raw.pop("website")

        return raw

