"""Definition of the Strategy ABC and concrete implementation classes.

This module provides the abstract base class Strategy and the deterministic
rule-based DefaultStrategy and FallbackStrategy implementations.
"""

from abc import ABC, abstractmethod

from argos.intent import Intent
from argos.intent.intent_result import IntentResult
from argos.planning.action import Action
from argos.planning.plan_step import PlanStep


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
