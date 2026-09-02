"""Transient working memory container for the ARGOS Brain Core.

Maintains short-term cognitive state, active goals, intermediate capability outputs,
and decision histories during cognitive loop execution.
"""

from dataclasses import dataclass, field
from typing import Any

from argos.brain.brain_status import CognitiveState
from argos.execution.execution_result import ExecutionResult
from argos.input.input_request import InputRequest
from argos.input.parsed_request import ParsedRequest
from argos.intent.intent_result import IntentResult
from argos.planning.plan import Plan


@dataclass(slots=True)
class WorkingMemory:
    """Transient cognitive state container owned by the Brain.

    Holds active session variables, intermediate data transfer objects,
    decision logs, and state flags for the duration of a cognitive session.
    """

    raw_input: InputRequest | None = None
    parsed_request: ParsedRequest | None = None
    intent_result: IntentResult | None = None
    plan: Plan | None = None
    execution_result: ExecutionResult | None = None
    cognitive_state: CognitiveState = CognitiveState.IDLE
    cycle_count: int = 0
    active_goal_id: str | None = None
    active_goal_name: str | None = None
    decision_history: list[str] = field(default_factory=list)
    observations: list[Any] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def record_decision(self, decision: str) -> None:
        """Appends a reasoning step or decision to the decision history.

        Args:
            decision: Description of the decision taken by the Brain.
        """
        self.decision_history.append(decision)

    def record_observation(self, observation: Any) -> None:
        """Records an observation generated after capability execution.

        Args:
            observation: The observation record to append.
        """
        self.observations.append(observation)

    def transition_to(self, new_state: CognitiveState) -> None:
        """Updates the internal cognitive lifecycle phase.

        Args:
            new_state: The new CognitiveState to transition into.
        """
        self.cognitive_state = new_state

    def increment_cycle(self) -> int:
        """Increments and returns the cognitive loop iteration count.

        Returns:
            The updated cycle count.
        """
        self.cycle_count += 1
        return self.cycle_count

    def set_context(self, key: str, value: Any) -> None:
        """Stores a contextual key-value pair in transient memory.

        Args:
            key: Context identifier.
            value: Context value.
        """
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieves a contextual value from transient memory.

        Args:
            key: Context identifier.
            default: Value to return if key is not found.

        Returns:
            The stored value or the default.
        """
        return self.context.get(key, default)

    def reset(self) -> None:
        """Resets all transient memory fields to their initial states."""
        self.raw_input = None
        self.parsed_request = None
        self.intent_result = None
        self.plan = None
        self.execution_result = None
        self.cognitive_state = CognitiveState.IDLE
        self.cycle_count = 0
        self.active_goal_id = None
        self.active_goal_name = None
        self.decision_history.clear()
        self.observations.clear()
        self.context.clear()
