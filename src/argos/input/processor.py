"""Definition of the InputProcessor class for request orchestration.

This module provides the main orchestration layer of the input subsystem,
integrating validation, normalization, tokenization, and parsing stages.
"""

import logging

from argos.input.constants import SUPPORTED_SOURCES
from argos.input.exceptions import (
    InputProcessingError,
    InvalidEncodingError,
    InvalidRequestError,
    ProcessingError,
    UnsupportedSourceError,
)
from argos.input.input_request import InputRequest
from argos.input.normalizer import Normalizer
from argos.input.parsed_request import ParsedRequest
from argos.input.parser import Parser
from argos.input.tokenizer import Tokenizer

logger = logging.getLogger(__name__)


class InputProcessor:
    """Orchestrates the processing of raw requests into structured requests.

    This class serves as the sole public interface of the input subsystem,
    hiding the internal details of Normalizer, Tokenizer, and Parser behind
    a single entry point.
    """

    def __init__(
        self,
        normalizer: Normalizer | None = None,
        tokenizer: Tokenizer | None = None,
        parser: Parser | None = None,
    ) -> None:
        """Initializes the InputProcessor with optional injected components.

        Args:
            normalizer: Optional custom Normalizer implementation.
            tokenizer: Optional custom Tokenizer implementation.
            parser: Optional custom Parser implementation.
        """
        self._normalizer = normalizer or Normalizer()
        self._tokenizer = tokenizer or Tokenizer()
        self._parser = parser or Parser()

    def process(self, request: InputRequest) -> ParsedRequest:
        """Runs the validation, normalization, tokenization, and parsing flow.

        Args:
            request: The raw InputRequest to be processed.

        Returns:
            A structured ParsedRequest ready for the Brain Core.

        Raises:
            InvalidRequestError: If the request is not an instance of InputRequest.
            UnsupportedSourceError: If the source of the request is not supported.
            InvalidEncodingError: If the raw text contains encoding violations.
            InputProcessingError: For general validation or parsing failures.
        """
        # Validate that we received an InputRequest instance
        if not isinstance(request, InputRequest):
            raise InvalidRequestError(
                "The provided request must be an instance of InputRequest."
            )

        logger.info("Request received from source: %s", request.source)
        logger.debug("Raw input text for processing: %r", request.raw_text)

        try:
            # 1. Validate the source
            if request.source not in SUPPORTED_SOURCES:
                raise UnsupportedSourceError(
                    f"Input source '{request.source}' is not supported. "
                    f"Supported sources are: {SUPPORTED_SOURCES}"
                )

            # 2. Validate encoding by verifying if it can be encoded to UTF-8
            try:
                request.raw_text.encode("utf-8")
            except UnicodeEncodeError as e:
                raise InvalidEncodingError(
                    "Input text contains character encodings that are invalid "
                    "for UTF-8."
                ) from e

            # 3. Normalize the text
            normalized_text = self._normalizer.normalize(request.raw_text)
            logger.info("Normalization complete")
            logger.debug("Normalized input text: %r", normalized_text)

            # 4. Tokenize the normalized text
            tokens = self._tokenizer.tokenize(normalized_text)
            logger.info("Tokenization complete")
            logger.debug("Tokens generated: %r", tokens)

            # 5. Assemble final ParsedRequest
            parsed_request = self._parser.parse(
                normalized_text=normalized_text,
                tokens=tokens,
                source=request.source,
                timestamp=request.timestamp,
            )
            logger.info("Parser complete")

            return parsed_request

        except InputProcessingError as e:
            logger.error("Processing error occurred: %s", str(e))
            raise
        except Exception as e:
            # Wrap any unhandled system exceptions in a ProcessingError
            logger.error("Unexpected processing error: %s", str(e), exc_info=True)
            raise ProcessingError(
                "An unexpected error occurred during input processing: "
                f"{e}"
            ) from e
