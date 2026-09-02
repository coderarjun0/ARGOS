"""Goal management component for the ARGOS Brain Core subsystem.

Coordinates goal creation, tracking, prioritization, completion, and cancellation
in compliance with ADS-005 Section 7.1.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from argos.brain.exceptions import ValidationError


class GoalStatus(StrEnum):
    """Lifecycle statuses for goals managed by the GoalManager."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class Goal:
    """Represents an active or tracked objective in the Brain Core.

    Attributes:
        goal_id: Unique identifier for the goal.
        name: Concise name or description of the objective.
        priority: Priority weighting (higher integers represent higher priority).
        status: Current lifecycle status of the goal.
        created_at: Timestamp when the goal was created.
        metadata: Contextual data and diagnostics associated with the goal.
    """

    goal_id: str
    name: str
    priority: int = 1
    status: GoalStatus = GoalStatus.PENDING
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class GoalManager:
    """Coordinates goal tracking, prioritization, and lifecycle transitions.

    Provides the foundation for objective coordination, ensuring the Brain
    maintains explicit awareness of its current goals.
    """

    def __init__(self) -> None:
        """Initializes an empty GoalManager."""
        self._goals: dict[str, Goal] = {}
        self._active_goal_id: str | None = None
        self._counter: int = 0

    def create_goal(
        self,
        name: str,
        priority: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        """Creates and tracks a new goal.

        Args:
            name: Non-empty description of the goal.
            priority: Priority weighting (default 1, must be >= 0).
            metadata: Optional contextual metadata.

        Returns:
            The created Goal instance.

        Raises:
            ValidationError: If name is empty or priority is invalid.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Goal name must be a non-empty string.")
        if not isinstance(priority, int) or priority < 0:
            raise ValidationError("Goal priority must be a non-negative integer.")

        self._counter += 1
        goal_id = f"goal-{self._counter}"
        goal = Goal(
            goal_id=goal_id,
            name=name.strip(),
            priority=priority,
            status=GoalStatus.PENDING,
            metadata=metadata or {},
        )
        self._goals[goal_id] = goal

        # Automatically set as active if no goal is currently active
        if self._active_goal_id is None:
            self._active_goal_id = goal_id
            goal.status = GoalStatus.ACTIVE

        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        """Retrieves a goal by its unique identifier.

        Args:
            goal_id: Unique goal identifier.

        Returns:
            The Goal instance or None if not found.
        """
        return self._goals.get(goal_id)

    def get_active_goal(self) -> Goal | None:
        """Retrieves the currently active goal.

        Returns:
            The active Goal instance, or None if no goal is active.
        """
        if self._active_goal_id:
            return self._goals.get(self._active_goal_id)

        # Fallback to the highest-priority pending goal
        pending_goals = [
            g for g in self._goals.values() if g.status == GoalStatus.PENDING
        ]
        if pending_goals:
            pending_goals.sort(key=lambda g: g.priority, reverse=True)
            chosen = pending_goals[0]
            chosen.status = GoalStatus.ACTIVE
            self._active_goal_id = chosen.goal_id
            return chosen

        return None

    def set_active_goal(self, goal_id: str) -> None:
        """Explicitly sets a goal as the active objective.

        Args:
            goal_id: Identifier of the goal to activate.

        Raises:
            ValidationError: If goal_id is not tracked.
        """
        if goal_id not in self._goals:
            raise ValidationError(f"Cannot activate untracked goal: {goal_id}")

        if self._active_goal_id and self._active_goal_id in self._goals:
            if self._goals[self._active_goal_id].status == GoalStatus.ACTIVE:
                self._goals[self._active_goal_id].status = GoalStatus.PENDING

        goal = self._goals[goal_id]
        goal.status = GoalStatus.ACTIVE
        self._active_goal_id = goal_id

    def list_goals(self) -> list[Goal]:
        """Returns a list of all tracked goals.

        Returns:
            List of Goal instances.
        """
        return list(self._goals.values())

    def reprioritize_goal(self, goal_id: str, priority: int) -> None:
        """Updates the priority score for an existing goal.

        Args:
            goal_id: Unique identifier of the goal to reprioritize.
            priority: New priority value (must be >= 0).

        Raises:
            ValidationError: If goal_id is unknown or priority is invalid.
        """
        if goal_id not in self._goals:
            raise ValidationError(f"Cannot reprioritize untracked goal: {goal_id}")
        if not isinstance(priority, int) or priority < 0:
            raise ValidationError("Priority must be a non-negative integer.")

        self._goals[goal_id].priority = priority

    def complete_goal(self, goal_id: str) -> None:
        """Marks a goal as successfully completed.

        Args:
            goal_id: Unique identifier of the goal.

        Raises:
            ValidationError: If goal_id is unknown.
        """
        if goal_id not in self._goals:
            raise ValidationError(f"Cannot complete untracked goal: {goal_id}")

        self._goals[goal_id].status = GoalStatus.COMPLETED
        if self._active_goal_id == goal_id:
            self._active_goal_id = None

    def fail_goal(self, goal_id: str, reason: str = "") -> None:
        """Marks a goal as failed with an optional diagnostic reason.

        Args:
            goal_id: Unique identifier of the goal.
            reason: Optional explanation of the failure.

        Raises:
            ValidationError: If goal_id is unknown.
        """
        if goal_id not in self._goals:
            raise ValidationError(f"Cannot fail untracked goal: {goal_id}")

        goal = self._goals[goal_id]
        goal.status = GoalStatus.FAILED
        if reason:
            goal.metadata["failure_reason"] = reason
        if self._active_goal_id == goal_id:
            self._active_goal_id = None

    def cancel_goal(self, goal_id: str) -> None:
        """Cancels a tracked goal.

        Args:
            goal_id: Unique identifier of the goal.

        Raises:
            ValidationError: If goal_id is unknown.
        """
        if goal_id not in self._goals:
            raise ValidationError(f"Cannot cancel untracked goal: {goal_id}")

        self._goals[goal_id].status = GoalStatus.CANCELLED
        if self._active_goal_id == goal_id:
            self._active_goal_id = None

    def has_active_goals(self) -> bool:
        """Checks whether any goals remain pending or active.

        Returns:
            True if any goals are PENDING or ACTIVE, otherwise False.
        """
        return any(
            g.status in (GoalStatus.ACTIVE, GoalStatus.PENDING)
            for g in self._goals.values()
        )

    def clear(self) -> None:
        """Clears all goals and resets tracking state."""
        self._goals.clear()
        self._active_goal_id = None
        self._counter = 0
