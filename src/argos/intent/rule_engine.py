"""Definition of the RuleEngine class for intent classification.

This module implements the deterministic keyword and regular expression matching
rules to resolve user requests into canonical intents.
"""

import re

from argos.input.parsed_request import ParsedRequest
from argos.intent.constants import MAX_ALTERNATIVE_INTENTS
from argos.intent.exceptions import ValidationError
from argos.intent.intent import Intent


class RuleEngine:
    """Classifies user intent based on deterministic keyword matching rules.

    This class is stateless and handles only primary action classification
    and fallback alternatives. It does not evaluate confidence or extract entities.
    """

    # Compiled regex patterns ordered from most specific to least specific.
    # Order prevents generic keywords (e.g. 'open') from overshadowing specific
    # compound intents (e.g. 'open file').
    _RULE_PATTERNS: list[tuple[Intent, re.Pattern[str]]] = [
        (
            Intent.RUN_COMMAND,
            re.compile(
                r"\b(run\s+command|execute\s+command|terminal|shell|bash|cmd|powershell)\b"
            ),
        ),
        (
            Intent.SET_REMINDER,
            re.compile(r"\b(remind|reminder|alarm|alert|set\s+reminder)\b"),
        ),
        (
            Intent.CONTROL_SYSTEM,
            re.compile(
                r"\b(mute|unmute|volume|brightness|shutdown|restart|reboot|sleep)\b"
            ),
        ),
        (
            Intent.OPEN_FILE,
            re.compile(
                r"\b(open|view|show|display|load)\s+.*?\b(file|document|notes|doc|txt|pdf|csv)\b"
            ),
        ),
        (
            Intent.CREATE_FILE,
            re.compile(
                r"\b(create|make|new|generate)\s+.*?\b(file|document|notes|doc|txt|pdf|csv)\b"
            ),
        ),
        (
            Intent.DELETE_FILE,
            re.compile(
                r"\b(delete|remove|erase|destroy)\s+.*?\b(file|folder|directory|doc|txt)\b"
            ),
        ),
        (
            Intent.READ_FILE,
            re.compile(r"\b(read|cat|view|print|display)\s+.*?\b(content|text|inside)\b"),
        ),
        (
            Intent.WRITE_FILE,
            re.compile(
                r"\b(write|append|save|edit|update)\s+.*?\b(to|into|file|document)\b"
            ),
        ),
        (
            Intent.SEARCH_WEB,
            re.compile(r"\b(search|google|lookup|find\s+on\s+web)\b"),
        ),
        (
            Intent.OPEN_APPLICATION,
            re.compile(r"\b(open|launch|run|start)\b"),
        ),
        (
            Intent.CLOSE_APPLICATION,
            re.compile(r"\b(close|exit|terminate|quit|stop|kill)\b"),
        ),
        (
            Intent.GET_INFORMATION,
            re.compile(
                r"\b(what|who|where|how|info|status|time|weather|date|tell\s+me)\b"
            ),
        ),
    ]

    def classify(self, request: ParsedRequest) -> tuple[Intent, list[Intent]]:
        """Determines the core primary intent and candidate alternatives.

        Args:
            request: The parsed request to classify.

        Returns:
            A tuple of (primary_intent, list_of_alternative_intents).

        Raises:
            ValidationError: If the input is not a ParsedRequest instance.
        """
        if not isinstance(request, ParsedRequest):
            raise ValidationError(
                "The provided request must be an instance of ParsedRequest."
            )

        text = request.normalized_text
        matching_intents: list[Intent] = []

        # Find all patterns that match the normalized text
        for intent, pattern in self._RULE_PATTERNS:
            if pattern.search(text):
                if intent not in matching_intents:
                    matching_intents.append(intent)

        # Handle the case where no rules matched
        if not matching_intents:
            return Intent.UNKNOWN, []

        # The first match in our prioritized rule list is the primary intent
        primary = matching_intents[0]

        # Remaining matching intents serve as fallback alternatives,
        # up to the configured limit
        alternatives = matching_intents[1 : 1 + MAX_ALTERNATIVE_INTENTS]

        return primary, alternatives
