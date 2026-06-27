"""Public API for the ARGOS Input layer subsystem.

This module exposes only the components intended for public consumption by other
subsystems (e.g., the Brain Core). All internal components (Normalizer,
Tokenizer, and Parser) remain encapsulated.
"""

from argos.input.exceptions import (
    EmptyInputError,
    InputLengthError,
    InputProcessingError,
    InvalidEncodingError,
    InvalidRequestError,
    ProcessingError,
    UnsupportedSourceError,
    ValidationError,
)
from argos.input.input_request import InputRequest
from argos.input.parsed_request import ParsedRequest
from argos.input.processor import InputProcessor

__all__ = [
    "InputRequest",
    "ParsedRequest",
    "InputProcessor",
    "InputProcessingError",
    "ValidationError",
    "ProcessingError",
    "EmptyInputError",
    "InputLengthError",
    "InvalidEncodingError",
    "UnsupportedSourceError",
    "InvalidRequestError",
]
