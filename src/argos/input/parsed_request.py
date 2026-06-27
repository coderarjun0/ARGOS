"""Definition of the ParsedRequest dataclass.

This module contains the structured container representing a parsed request
that has been processed by the input pipeline and is ready for the Brain Core.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ParsedRequest:
    """Represents a structured user request after normalization and tokenization.

    This object serves as the boundary interface between the Input Layer and the
    Brain Core. It contains clean, standardized data for intent recognition.

    Attributes:
        normalized_text: The lowercased, whitespace-trimmed version of the input.
        tokens: The normalized text split into individual word tokens.
        source: The original source system where the request was generated.
        timestamp: The timestamp of when the request was first registered.
    """

    normalized_text: str
    tokens: list[str]
    source: str
    timestamp: datetime
