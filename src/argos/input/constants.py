"""Constants for the ARGOS input processing pipeline.

This module contains configurable limits and validation settings
used by the normalizer and processors of the input subsystem.
"""

from typing import Final

# The maximum allowed character length of raw user input to protect resources.
MAX_INPUT_LENGTH: Final[int] = 65536

# The set of sources permitted by the input processing pipeline.
SUPPORTED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "cli",
        "voice",
        "webhook",
        "gui",
        "api",
    }
)
