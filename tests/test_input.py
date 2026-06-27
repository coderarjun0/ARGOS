"""Unit tests for the ARGOS input subsystem.

This module contains the comprehensive test suite to verify the correctness,
robustness, and coverage of the input processing pipeline.
"""

import logging
from datetime import datetime
from unittest.mock import Mock

import pytest

from argos.input import (
    EmptyInputError,
    InputLengthError,
    InputProcessor,
    InputRequest,
    InvalidEncodingError,
    InvalidRequestError,
    ParsedRequest,
    ProcessingError,
    UnsupportedSourceError,
    ValidationError,
)
from argos.input.constants import MAX_INPUT_LENGTH
from argos.input.normalizer import Normalizer
from argos.input.parser import Parser
from argos.input.tokenizer import Tokenizer

# =====================================================================
# Model and Dataclass Tests
# =====================================================================


def test_input_request_creation() -> None:
    """Verifies that InputRequest is correctly instantiated.

    Checks default fields and type properties.
    """
    timestamp = datetime.now()
    request = InputRequest(
        raw_text="Open VS Code",
        source="cli",
        timestamp=timestamp,
    )
    assert request.raw_text == "Open VS Code"
    assert request.source == "cli"
    assert request.timestamp == timestamp
    assert request.metadata == {}

    # Verify slots are working (should not be able to set arbitrary attributes)
    with pytest.raises(AttributeError):
        request.arbitrary_field = "unallowed"  # type: ignore


def test_parsed_request_creation() -> None:
    """Verifies that ParsedRequest is correctly instantiated."""
    timestamp = datetime.now()
    request = ParsedRequest(
        normalized_text="open vs code",
        tokens=["open", "vs", "code"],
        source="cli",
        timestamp=timestamp,
    )
    assert request.normalized_text == "open vs code"
    assert request.tokens == ["open", "vs", "code"]
    assert request.source == "cli"
    assert request.timestamp == timestamp

    # Verify slots are working
    with pytest.raises(AttributeError):
        request.arbitrary_field = "unallowed"  # type: ignore


# =====================================================================
# Normalizer Tests
# =====================================================================


def test_normalizer_success() -> None:
    """Verifies successful normalization transformations."""
    normalizer = Normalizer()

    # Case normalization, stripping, and whitespace compression
    assert normalizer.normalize("  Open    VS   Code  ") == "open vs code"
    assert normalizer.normalize("Line1\nLine2\tTabbed") == "line1 line2 tabbed"
    assert normalizer.normalize("already normalized") == "already normalized"

    # Punctuation must be preserved
    assert normalizer.normalize("hello, world!") == "hello, world!"


def test_normalizer_validation_failures() -> None:
    """Verifies that Normalizer raises the appropriate custom exceptions."""
    normalizer = Normalizer()

    # Type verification
    with pytest.raises(ValidationError) as excinfo:
        normalizer.normalize(12345)  # type: ignore
    assert "must be a string" in str(excinfo.value)

    # Empty inputs
    with pytest.raises(EmptyInputError):
        normalizer.normalize("")

    # Whitespace-only inputs
    with pytest.raises(EmptyInputError):
        normalizer.normalize("     ")
    with pytest.raises(EmptyInputError):
        normalizer.normalize("\n\t  \r")

    # Exceeding MAX_INPUT_LENGTH
    long_text = "a" * (MAX_INPUT_LENGTH + 1)
    with pytest.raises(InputLengthError) as excinfo:
        normalizer.normalize(long_text)
    assert "exceeds maximum allowed limit" in str(excinfo.value)


# =====================================================================
# Tokenizer Tests
# =====================================================================


def test_tokenizer_success() -> None:
    """Verifies successful tokenization splitting."""
    tokenizer = Tokenizer()

    assert tokenizer.tokenize("open vs code") == ["open", "vs", "code"]
    assert tokenizer.tokenize("help") == ["help"]
    assert tokenizer.tokenize("") == []


def test_tokenizer_validation_failures() -> None:
    """Verifies that Tokenizer checks inputs correctly."""
    tokenizer = Tokenizer()

    # Type verification
    with pytest.raises(ValidationError) as excinfo:
        tokenizer.tokenize(None)  # type: ignore
    assert "must be a string" in str(excinfo.value)


# =====================================================================
# Parser Tests
# =====================================================================


def test_parser_success() -> None:
    """Verifies that the Parser builds ParsedRequest without modifications."""
    parser = Parser()
    timestamp = datetime.now()
    parsed = parser.parse(
        normalized_text="open vs code",
        tokens=["open", "vs", "code"],
        source="cli",
        timestamp=timestamp,
    )
    assert isinstance(parsed, ParsedRequest)
    assert parsed.normalized_text == "open vs code"
    assert parsed.tokens == ["open", "vs", "code"]
    assert parsed.source == "cli"
    assert parsed.timestamp == timestamp


# =====================================================================
# InputProcessor Orchestrator Tests
# =====================================================================


def test_processor_success() -> None:
    """Verifies that InputProcessor integrates components successfully."""
    processor = InputProcessor()
    timestamp = datetime.now()
    request = InputRequest(
        raw_text="  Show    System   Status  ",
        source="voice",
        timestamp=timestamp,
    )

    parsed = processor.process(request)
    assert isinstance(parsed, ParsedRequest)
    assert parsed.normalized_text == "show system status"
    assert parsed.tokens == ["show", "system", "status"]
    assert parsed.source == "voice"
    assert parsed.timestamp == timestamp


def test_processor_invalid_request_type() -> None:
    """Verifies that passing a non-InputRequest raises InvalidRequestError."""
    processor = InputProcessor()
    with pytest.raises(InvalidRequestError) as excinfo:
        processor.process("not an InputRequest")  # type: ignore
    assert "must be an instance of InputRequest" in str(excinfo.value)


def test_processor_unsupported_source() -> None:
    """Verifies that using an unsupported source raises UnsupportedSourceError."""
    processor = InputProcessor()
    request = InputRequest(
        raw_text="help",
        source="unknown_client",
        timestamp=datetime.now(),
    )
    with pytest.raises(UnsupportedSourceError) as excinfo:
        processor.process(request)
    assert "is not supported" in str(excinfo.value)


def test_processor_invalid_encoding() -> None:
    """Verifies that invalid characters raise InvalidEncodingError.

    We use a lone surrogate string U+D800, which cannot be encoded in UTF-8.
    """
    processor = InputProcessor()
    request = InputRequest(
        raw_text="hello \ud800 world",
        source="cli",
        timestamp=datetime.now(),
    )
    with pytest.raises(InvalidEncodingError) as excinfo:
        processor.process(request)
    assert "invalid for UTF-8" in str(excinfo.value)


def test_processor_dependency_injection() -> None:
    """Verifies that custom components are injected and called correctly."""
    mock_normalizer = Mock(spec=Normalizer)
    mock_tokenizer = Mock(spec=Tokenizer)
    mock_parser = Mock(spec=Parser)

    mock_normalizer.normalize.return_value = "mocked normalized text"
    mock_tokenizer.tokenize.return_value = ["mocked", "tokens"]
    mock_parser.parse.return_value = ParsedRequest(
        normalized_text="mocked normalized text",
        tokens=["mocked", "tokens"],
        source="cli",
        timestamp=datetime.min,
    )

    processor = InputProcessor(
        normalizer=mock_normalizer,
        tokenizer=mock_tokenizer,
        parser=mock_parser,
    )

    timestamp = datetime.now()
    request = InputRequest(
        raw_text="Arbitrary Text",
        source="cli",
        timestamp=timestamp,
    )

    parsed = processor.process(request)

    # Verify components were called with expected inputs
    mock_normalizer.normalize.assert_called_once_with("Arbitrary Text")
    mock_tokenizer.tokenize.assert_called_once_with("mocked normalized text")
    mock_parser.parse.assert_called_once_with(
        normalized_text="mocked normalized text",
        tokens=["mocked", "tokens"],
        source="cli",
        timestamp=timestamp,
    )
    assert parsed.normalized_text == "mocked normalized text"


def test_processor_unexpected_internal_error() -> None:
    """Verifies that unexpected standard errors are wrapped in a ProcessingError."""
    mock_normalizer = Mock(spec=Normalizer)
    mock_normalizer.normalize.side_effect = RuntimeError(
        "Database offline or system crash"
    )

    processor = InputProcessor(normalizer=mock_normalizer)
    request = InputRequest(
        raw_text="help",
        source="cli",
        timestamp=datetime.now(),
    )

    with pytest.raises(ProcessingError) as excinfo:
        processor.process(request)
    assert "An unexpected error occurred" in str(excinfo.value)
    assert "Database offline" in str(excinfo.value)


def test_processor_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies that log events are emitted and user privacy is preserved."""
    processor = InputProcessor()
    request = InputRequest(
        raw_text="secret password text",
        source="cli",
        timestamp=datetime.now(),
    )

    # Run processing with logs captured
    with caplog.at_level(logging.INFO):
        processor.process(request)

    # Verify standard logs are logged at INFO level
    log_messages = [record.message for record in caplog.records]
    assert any("Request received from source: cli" in msg for msg in log_messages)
    assert any("Normalization complete" in msg for msg in log_messages)
    assert any("Tokenization complete" in msg for msg in log_messages)
    assert any("Parser complete" in msg for msg in log_messages)

    # Verify sensitive data is NOT logged at INFO level
    assert not any("secret password" in msg for msg in log_messages)

    # Verify logging errors upon pipeline failures
    caplog.clear()
    bad_request = InputRequest(
        raw_text="   ",
        source="cli",
        timestamp=datetime.now(),
    )
    with pytest.raises(EmptyInputError):
        processor.process(bad_request)

    error_log_messages = [record.message for record in caplog.records]
    assert any("Processing error occurred" in msg for msg in error_log_messages)
