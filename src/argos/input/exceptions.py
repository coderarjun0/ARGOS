"""Custom exceptions for the ARGOS input processing subsystem.

This module defines the exception hierarchy used throughout the input pipeline.
All exceptions derive from a common base exception `InputProcessingError`.
"""


class InputProcessingError(Exception):
    """Base exception for all errors in the ARGOS input processing subsystem.

    This exception should be caught when handling any failure within the input
    layer, allowing higher-level systems (such as the Brain Core) to degrade
    gracefully.
    """


class ValidationError(InputProcessingError):
    """Base exception for all input validation failures.

    ValidationError is raised when the provided raw input fails validation
    checks (e.g., empty string, too long, invalid encoding, or unsupported source).
    """


class ProcessingError(InputProcessingError):
    """Base exception for runtime processing failures.

    Reserved for future runtime processing failures where the input structure is
    valid but processing cannot complete due to internal issues.
    """


class EmptyInputError(ValidationError):
    """Exception raised when the input is empty or contains only whitespace.

    This error indicates that there is no content to normalize, tokenize,
    or parse.
    """


class InputLengthError(ValidationError):
    """Exception raised when the input text exceeds the maximum allowed length.

    This protects the system from resource exhaustion caused by abnormally large
    inputs.
    """


class InvalidEncodingError(ValidationError):
    """Exception raised when the input text cannot be decoded or processed as UTF-8.

    This indicates that the raw text contains malformed character encodings.
    """


class UnsupportedSourceError(ValidationError):
    """Exception raised when the input request source is not recognized or supported.

    This enforces that all inputs come from an approved origin as defined in the
    system constants.
    """


class InvalidRequestError(ValidationError):
    """Exception raised when the object passed to the processor is not an InputRequest.

    This enforces structural type safety at the input boundary.
    """

