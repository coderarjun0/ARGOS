"""Definition of the Tokenizer class for text tokenization.

This module provides the logic to split pre-normalized text into space-separated
tokens without modifying word structures, casing, or punctuation.
"""


from argos.input.exceptions import ValidationError


class Tokenizer:
    """Splits normalized text into a list of individual tokens.

    This class is stateless and deterministic. It performs basic tokenization
    by splitting strings on space boundaries, leaving punctuation intact.
    """

    def tokenize(self, text: str) -> list[str]:
        """Splits the normalized input text into individual string tokens.

        Args:
            text: A normalized, lowercase string with compressed whitespace.

        Returns:
            A list of string tokens.

        Raises:
            ValidationError: If the input text is not a string.
        """
        if not isinstance(text, str):
            raise ValidationError("Input text must be a string.")

        # Since the input is pre-normalized, whitespace is compressed to single spaces,
        # and leading/trailing whitespace is removed. Splitting on a single space is
        # sufficient and highly efficient.
        if not text:
            return []

        return text.split(" ")
