"""Unit tests for the ARGOS intent analysis subsystem.

This module contains the comprehensive test suite to verify the correctness,
robustness, and coverage of the intent analysis pipeline.
"""

import logging
from datetime import datetime
from unittest.mock import Mock

import pytest

from argos.input.parsed_request import ParsedRequest
from argos.intent import (
    Intent,
    IntentAnalyzer,
    IntentResult,
    InvalidConfidenceError,
    InvalidRequestError,
    ProcessingError,
    ValidationError,
)
from argos.intent.confidence_evaluator import ConfidenceEvaluator
from argos.intent.entity_extractor import EntityExtractor
from argos.intent.rule_engine import RuleEngine

# =====================================================================
# Intent Enum Tests
# =====================================================================


def test_intent_enum_values() -> None:
    """Verifies that the canonical Intent enum contains all expected members."""
    expected_intents = {
        "UNKNOWN",
        "OPEN_APPLICATION",
        "CLOSE_APPLICATION",
        "OPEN_FILE",
        "CREATE_FILE",
        "DELETE_FILE",
        "READ_FILE",
        "WRITE_FILE",
        "SEARCH_WEB",
        "RUN_COMMAND",
        "GET_INFORMATION",
        "SET_REMINDER",
        "CONTROL_SYSTEM",
    }
    actual_members = set(Intent.__members__.keys())
    assert expected_intents.issubset(actual_members)


def test_intent_enum_str_behavior() -> None:
    """Verifies that Intent behaves as a StrEnum."""
    assert Intent.OPEN_APPLICATION == "open_application"
    assert isinstance(Intent.OPEN_APPLICATION, str)
    assert f"{Intent.SEARCH_WEB}" == "search_web"


# =====================================================================
# IntentResult Dataclass Tests
# =====================================================================


def test_intent_result_creation() -> None:
    """Verifies IntentResult instantiation and default parameters."""
    result = IntentResult(
        primary_intent=Intent.OPEN_APPLICATION,
        confidence=0.9,
        analysis_engine="test_engine",
    )
    assert result.primary_intent == Intent.OPEN_APPLICATION
    assert result.confidence == 0.9
    assert result.analysis_engine == "test_engine"
    assert result.entities == {}
    assert result.alternatives == []
    assert result.metadata == {}


def test_intent_result_slots() -> None:
    """Verifies that slots=True prevents dynamic attribute additions."""
    result = IntentResult(
        primary_intent=Intent.UNKNOWN,
        confidence=0.0,
        analysis_engine="test_engine",
    )
    with pytest.raises(AttributeError):
        result.extra_attribute = "unallowed"  # type: ignore


def test_intent_result_mutable_defaults() -> None:
    """Verifies that default factory prevents shared mutable states."""
    result1 = IntentResult(
        primary_intent=Intent.UNKNOWN,
        confidence=0.0,
        analysis_engine="engine",
    )
    result2 = IntentResult(
        primary_intent=Intent.UNKNOWN,
        confidence=0.0,
        analysis_engine="engine",
    )

    result1.entities["application"] = ["vscode"]
    result1.alternatives.append(Intent.OPEN_FILE)
    result1.metadata["test"] = True

    # Mutated instance should not affect the second instance
    assert result2.entities == {}
    assert result2.alternatives == []
    assert result2.metadata == {}


# =====================================================================
# RuleEngine Tests
# =====================================================================


def test_rule_engine_classification() -> None:
    """Verifies RuleEngine maps clean text queries to primary intents."""
    engine = RuleEngine()

    def get_request(text: str) -> ParsedRequest:
        return ParsedRequest(
            normalized_text=text.lower(),
            tokens=text.lower().split(" "),
            source="cli",
            timestamp=datetime.now(),
        )

    # OPEN_APPLICATION
    primary, _ = engine.classify(get_request("open chrome"))
    assert primary == Intent.OPEN_APPLICATION

    # SEARCH_WEB
    primary, _ = engine.classify(get_request("search python guides on google"))
    assert primary == Intent.SEARCH_WEB

    # CREATE_FILE
    primary, _ = engine.classify(get_request("create a new file data.csv"))
    assert primary == Intent.CREATE_FILE

    # UNKNOWN
    primary, alts = engine.classify(get_request("just some random text"))
    assert primary == Intent.UNKNOWN
    assert alts == []


def test_rule_engine_alternatives() -> None:
    """Verifies RuleEngine returns multiple matching rules as alternatives."""
    engine = RuleEngine()
    request = ParsedRequest(
        normalized_text="open file details and run command terminal",
        tokens=[
            "open",
            "file",
            "details",
            "and",
            "run",
            "command",
            "terminal",
        ],
        source="cli",
        timestamp=datetime.now(),
    )
    primary, alts = engine.classify(request)

    # Specific rule matched first
    assert primary == Intent.RUN_COMMAND
    assert Intent.OPEN_FILE in alts
    assert len(alts) >= 1


def test_rule_engine_invalid_input() -> None:
    """Verifies RuleEngine validates request types."""
    engine = RuleEngine()
    with pytest.raises(ValidationError):
        engine.classify("not a ParsedRequest")  # type: ignore


# =====================================================================
# EntityExtractor Tests
# =====================================================================


def test_entity_extractor_success() -> None:
    """Verifies extraction patterns of various entity types."""
    extractor = EntityExtractor()

    def get_request(text: str) -> ParsedRequest:
        return ParsedRequest(
            normalized_text=text.lower(),
            tokens=text.lower().split(" "),
            source="cli",
            timestamp=datetime.now(),
        )

    # Multiple entity extraction: website, url, file, folder, application
    request = get_request(
        "open chrome and go to www.github.com/argos "
        "and edit notes.txt in folder documents and target /usr/bin/workspace"
    )
    entities = extractor.extract(request)

    assert "application" in entities
    assert "vscode" not in entities.get("application", [])
    assert "chrome" in entities["application"]

    assert "url" in entities
    assert "www.github.com/argos" in entities["url"]

    assert "file" in entities
    assert "notes.txt" in entities["file"]

    assert "folder" in entities
    assert "documents" in entities["folder"]
    assert "usr/bin/workspace" in entities["folder"]

    # Person, date, time, and command extraction
    request2 = get_request(
        "remind arjun to run git status tomorrow on june 28 at 2:30 pm"
    )
    entities2 = extractor.extract(request2)

    assert "person" in entities2
    assert "arjun" in entities2["person"]

    assert "command" in entities2
    assert "git status" in entities2["command"]

    assert "date" in entities2
    assert "tomorrow" in entities2["date"]
    assert "june 28" in entities2["date"]

    assert "time" in entities2
    assert "2:30 pm" in entities2["time"]


def test_entity_extractor_empty() -> None:
    """Verifies that no found entities returns an empty dictionary."""
    extractor = EntityExtractor()
    request = ParsedRequest(
        normalized_text="just some normal words without targets",
        tokens=["just", "some", "normal", "words", "without", "targets"],
        source="cli",
        timestamp=datetime.now(),
    )
    assert extractor.extract(request) == {}


def test_entity_extractor_invalid_input() -> None:
    """Verifies EntityExtractor validates request types."""
    extractor = EntityExtractor()
    with pytest.raises(ValidationError):
        extractor.extract("not a ParsedRequest")  # type: ignore


# =====================================================================
# ConfidenceEvaluator Tests
# =====================================================================


def test_confidence_evaluator_scoring() -> None:
    """Verifies confidence evaluator scoring heuristics and boundaries."""
    evaluator = ConfidenceEvaluator()

    # UNKNOWN intent always returns 0.0
    assert (
        evaluator.evaluate(Intent.UNKNOWN, [Intent.OPEN_FILE], {"file": ["a"]})
        == 0.0
    )

    # Standard baseline
    base = evaluator.evaluate(Intent.OPEN_APPLICATION, [], {})
    assert base == 0.85

    # Ambiguity penalty (each alternative subtracts 0.05)
    with_alt = evaluator.evaluate(
        Intent.OPEN_APPLICATION,
        [Intent.OPEN_FILE],
        {},
    )
    assert with_alt == 0.80

    # Entity bonus (each category adds 0.05, max 0.15)
    with_entities = evaluator.evaluate(
        Intent.OPEN_APPLICATION,
        [],
        {"application": ["chrome"], "file": ["notes.txt"]},
    )
    assert with_entities == 0.95


def test_confidence_evaluator_clamping() -> None:
    """Verifies that evaluated scores are strictly clamped between 0.0 and 1.0."""
    evaluator = ConfidenceEvaluator()

    # Max entities bonus should push score to 1.0 (clamped)
    score_max = evaluator.evaluate(
        Intent.OPEN_APPLICATION,
        [],
        {"file": ["a"], "folder": ["b"], "application": ["c"], "url": ["d"]},
    )
    assert score_max == 1.0

    # High alternatives penalty should not go below 0.0
    score_min = evaluator.evaluate(
        Intent.OPEN_APPLICATION,
        [Intent.UNKNOWN] * 20,
        {},
    )
    assert score_min == 0.0


def test_confidence_evaluator_validation() -> None:
    """Verifies input argument validation checks."""
    evaluator = ConfidenceEvaluator()

    with pytest.raises(ValidationError) as excinfo:
        evaluator.evaluate("not an Intent", [], {})  # type: ignore
    assert "primary_intent must be" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        evaluator.evaluate(Intent.UNKNOWN, "not a list", {})  # type: ignore
    assert "alternatives must be a list" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        evaluator.evaluate(Intent.UNKNOWN, ["not an enum"], {})  # type: ignore
    assert "instances of Intent" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        evaluator.evaluate(Intent.UNKNOWN, [], "not a dict")  # type: ignore
    assert "entities must be a dictionary" in str(excinfo.value)


def test_confidence_evaluator_invalid_bounds_error() -> None:
    """Verifies that an InvalidConfidenceError is raised if bounds are violated."""
    from unittest.mock import patch
    evaluator = ConfidenceEvaluator()
    # Mock built-in max inside confidence_evaluator module to return a value > 1.0
    with patch("argos.intent.confidence_evaluator.max", return_value=1.5):
        with pytest.raises(InvalidConfidenceError) as excinfo:
            evaluator.evaluate(Intent.OPEN_APPLICATION, [], {})
        assert "out of boundaries" in str(excinfo.value)


# =====================================================================
# IntentAnalyzer Orchestrator Tests
# =====================================================================


def test_analyzer_integration_success() -> None:
    """Verifies end-to-end integration and mapping via IntentAnalyzer."""
    analyzer = IntentAnalyzer()
    timestamp = datetime.now()
    request = ParsedRequest(
        normalized_text="open notes.txt in vscode",
        tokens=["open", "notes.txt", "in", "vscode"],
        source="voice",
        timestamp=timestamp,
    )

    result = analyzer.analyze(request)
    assert isinstance(result, IntentResult)
    assert result.primary_intent == Intent.OPEN_FILE
    assert result.analysis_engine == "rule_engine"
    assert "file" in result.entities
    assert "notes.txt" in result.entities["file"]
    assert "vscode" in result.entities["application"]
    assert result.confidence == 0.90  # 0.85 base - 0.05 alt + 0.10 entities
    assert result.metadata["source"] == "voice"
    assert result.metadata["request_timestamp"] == timestamp.isoformat()


def test_analyzer_type_safety() -> None:
    """Verifies that non-ParsedRequest parameters raise InvalidRequestError."""
    analyzer = IntentAnalyzer()
    with pytest.raises(InvalidRequestError) as excinfo:
        analyzer.analyze("invalid raw request")  # type: ignore
    assert "must be an instance of ParsedRequest" in str(excinfo.value)


def test_analyzer_dependency_injection() -> None:
    """Verifies that dependency injection parameters are called correctly."""
    mock_rules = Mock(spec=RuleEngine)
    mock_extractor = Mock(spec=EntityExtractor)
    mock_evaluator = Mock(spec=ConfidenceEvaluator)

    mock_rules.classify.return_value = (Intent.OPEN_APPLICATION, [])
    mock_extractor.extract.return_value = {"application": ["chrome"]}
    mock_evaluator.evaluate.return_value = 0.9

    analyzer = IntentAnalyzer(
        rule_engine=mock_rules,
        entity_extractor=mock_extractor,
        confidence_evaluator=mock_evaluator,
    )

    request = ParsedRequest(
        normalized_text="open chrome",
        tokens=["open", "chrome"],
        source="cli",
        timestamp=datetime.now(),
    )

    result = analyzer.analyze(request)

    mock_rules.classify.assert_called_once_with(request)
    mock_extractor.extract.assert_called_once_with(request)
    mock_evaluator.evaluate.assert_called_once_with(
        primary_intent=Intent.OPEN_APPLICATION,
        alternatives=[],
        entities={"application": ["chrome"]},
    )

    assert result.primary_intent == Intent.OPEN_APPLICATION
    assert result.confidence == 0.9
    assert result.entities == {"application": ["chrome"]}


def test_analyzer_unexpected_crashes() -> None:
    """Verifies that internal runtime errors are wrapped in a ProcessingError."""
    mock_rules = Mock(spec=RuleEngine)
    mock_rules.classify.side_effect = RuntimeError("Hardware database failure")

    analyzer = IntentAnalyzer(rule_engine=mock_rules)
    request = ParsedRequest(
        normalized_text="help",
        tokens=["help"],
        source="cli",
        timestamp=datetime.now(),
    )

    with pytest.raises(ProcessingError) as excinfo:
        analyzer.analyze(request)
    assert "An unexpected error occurred" in str(excinfo.value)
    assert "Hardware database" in str(excinfo.value)


def test_analyzer_logging_behavior(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies logs are emitted correctly and hide sensitive text from INFO."""
    analyzer = IntentAnalyzer()
    request = ParsedRequest(
        normalized_text="open secrets.xlsx containing credential keys",
        tokens=[
            "open",
            "secrets.xlsx",
            "containing",
            "credential",
            "keys",
        ],
        source="cli",
        timestamp=datetime.now(),
    )

    with caplog.at_level(logging.INFO):
        analyzer.analyze(request)

    log_messages = [record.message for record in caplog.records]
    assert any("Intent analysis started" in msg for msg in log_messages)
    assert any("Intent classification completed" in msg for msg in log_messages)
    assert any("Entity extraction completed" in msg for msg in log_messages)
    assert any("Confidence evaluation completed" in msg for msg in log_messages)

    # Privacy verification: Raw secret text should not leak at INFO level
    assert not any("secrets.xlsx" in msg for msg in log_messages)

    # Verify failure logs
    caplog.clear()
    mock_rules = Mock(spec=RuleEngine)
    mock_rules.classify.side_effect = ValidationError("Custom failure")
    err_analyzer = IntentAnalyzer(rule_engine=mock_rules)

    with pytest.raises(ValidationError):
        err_analyzer.analyze(request)

    error_logs = [record.message for record in caplog.records]
    assert any("Intent analysis exception occurred" in msg for msg in error_logs)


# =====================================================================
# Public API & Encapsulation Boundary Tests
# =====================================================================


def test_public_api_exports() -> None:
    """Verifies all public subsystem exports are importable from argos.intent."""
    import argos.intent as intent_package

    # Verify expected components
    assert hasattr(intent_package, "IntentAnalyzer")
    assert hasattr(intent_package, "Intent")
    assert hasattr(intent_package, "IntentResult")
    assert hasattr(intent_package, "IntentAnalysisError")
    assert hasattr(intent_package, "ValidationError")

    # Verify that internal components are NOT exported at the package root
    assert not hasattr(intent_package, "RuleEngine")
    assert not hasattr(intent_package, "EntityExtractor")
    assert not hasattr(intent_package, "ConfidenceEvaluator")
