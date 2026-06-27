"""Definition of the Parser class for structured request assembly.

This module provides the logic to construct a ParsedRequest object from the
normalized data and metadata generated in previous pipeline steps.
"""

from datetime import datetime

from argos.input.parsed_request import ParsedRequest


class Parser:
    """Assembles normalized text and tokens into a structured ParsedRequest.

    This class is stateless and deterministic. It performs no cognitive processing,
    intent recognition, or validation; its sole responsibility is data mapping
    and container construction.
    """

    def parse(
        self,
        normalized_text: str,
        tokens: list[str],
        source: str,
        timestamp: datetime,
    ) -> ParsedRequest:
        """Constructs a structured ParsedRequest container.

        Args:
            normalized_text: The cleaned, lowercase representation of user input.
            tokens: The list of space-split word tokens.
            source: The originating client source.
            timestamp: The datetime when the request was received.

        Returns:
            An instance of ParsedRequest populated with the input arguments.
        """
        return ParsedRequest(
            normalized_text=normalized_text,
            tokens=tokens,
            source=source,
            timestamp=timestamp,
        )
