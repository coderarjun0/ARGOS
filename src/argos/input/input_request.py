"""Definition of the InputRequest dataclass.

This module contains the structured container representing a raw request
received by the ARGOS input subsystem.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class InputRequest:
    """Represents a raw user request before normalization or tokenization.

    This class serves as the initial container for any request processed
    by the ARGOS input pipeline.

    Attributes:
        raw_text: The original, unaltered text input from the user.
        source: The origin of the request (e.g., 'cli', 'voice', 'gui').
        timestamp: The exact time the request was received or created.
        metadata: Optional additional contextual information about the request,
            such as client identifiers, coordinate data, or platform details.
    """

    raw_text: str
    source: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
