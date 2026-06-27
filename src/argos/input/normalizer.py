"""Definition of the Normalizer class for input text standardization.

This module provides the logic to trim, lowercase, and compress whitespace
in input text, while raising validation errors if limits are exceeded.
"""

import re

from argos.input.constants import MAX_INPUT_LENGTH
from argos.input.exceptions import EmptyInputError, InputLengthError, ValidationError


class Normalizer:
    """Normalizes raw input text to a standardized, clean format.

    This class is stateless and deterministic. It performs basic syntax cleaning
    (trimming, compressing whitespace, and lowercasing) and enforces input length
    and content presence rules.
    """

    # Compiled regex to match any sequence of whitespace characters
    # (spaces, tabs, newlines)
    _WHITESPACE_PATTERN = re.compile(r"\s+")

    def normalize(self, text: str) -> str:
        """Standardizes formatting of the input text and validates its bounds.

        Args:
            text: The raw string to be normalized.

        Returns:
            The normalized, lowercase string with compressed whitespace.

        Raises:
            InputLengthError: If the raw text length exceeds MAX_INPUT_LENGTH.
            EmptyInputError: If the input text is empty or contains only whitespace.
            ValidationError: If the input text is not a string.
        """
        # Validate that the input is a string (runtime check for safety)
        if not isinstance(text, str):
            raise ValidationError("Input text must be a string.")

        # 1. Validate raw input length before processing to protect resources
        if len(text) > MAX_INPUT_LENGTH:
            raise InputLengthError(
                f"Input length {len(text)} exceeds maximum allowed limit of "
                f"{MAX_INPUT_LENGTH} characters."
            )

        # 2. Trim leading and trailing whitespace
        trimmed = text.strip()

        # 3. Validate that the text is not empty after trimming
        if not trimmed:
            raise EmptyInputError(
                "Input text cannot be empty or consist solely of whitespace."
            )

        # 4. Replace consecutive whitespace sequences (spaces, tabs, newlines)
        # with a single space
        compressed = self._WHITESPACE_PATTERN.sub(" ", trimmed)

        # 5. Convert to lowercase
        return compressed.lower()
