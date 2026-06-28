"""Definition of the EntityExtractor class for semantic entity parsing.

This module provides deterministic rule-based and token-based extraction
rules to parse files, applications, sites, dates, and names from normalized text.
"""

import re

from argos.input.parsed_request import ParsedRequest
from argos.intent.exceptions import ValidationError


class EntityExtractor:
    """Extracts key semantic parameters (entities) from user requests.

    This class is stateless and handles token-based scanning and regular
    expression matching to isolate targets such as file paths, application names,
    dates, times, and system commands.
    """

    # Pre-compiled regular expressions using non-capturing groups for whole matches
    _URL_PATTERN = re.compile(r"\bhttps?://[^\s]+|www\.[^\s]+\b", re.IGNORECASE)

    _FILE_PATTERN = re.compile(
        r"\b[\w\-]+\.(?:txt|pdf|csv|py|doc|docx|json|yaml|yml|md|html|png|jpg|exe)\b",
        re.IGNORECASE,
    )

    _FOLDER_PATTERN = re.compile(
        r"\b(?:[\w\-]+/)+[\w\-]*|\\(?:[\w\-]+\\)+[\w\-]*|/(?:home|user|tmp|var)/[\w\-]+\b",
        re.IGNORECASE,
    )

    _DATE_PATTERN = re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b|\b\d{1,2}(?:st|nd|rd|th)\b",
        re.IGNORECASE,
    )

    _TIME_PATTERN = re.compile(
        r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b|\b\d{1,2}(?:am|pm)\b|\b(?:noon|midnight)\b",
        re.IGNORECASE,
    )

    _COMMAND_PATTERN = re.compile(
        r"\b(?:git\s+[\w\-]+|pip\s+[\w\-]+|npm\s+run\s+[\w\-]+|pytest)\b",
        re.IGNORECASE,
    )

    # Capturing group to capture the name after trigger verbs
    _PERSON_PATTERN = re.compile(
        r"\b(?:email|message|tell|call|remind|contact|ask)\s+([a-zA-Z]+)\b",
        re.IGNORECASE,
    )

    # Keywords dictionaries
    _WEBSITES = {
        "google",
        "wikipedia",
        "github",
        "youtube",
        "reddit",
        "facebook",
        "twitter",
        "linkedin",
    }

    _APPLICATIONS = {
        "chrome",
        "firefox",
        "vscode",
        "slack",
        "spotify",
        "terminal",
        "notepad",
        "calculator",
        "excel",
        "word",
    }

    _DATES = {
        "today",
        "tomorrow",
        "yesterday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }

    def extract(self, request: ParsedRequest) -> dict[str, list[str]]:
        """Parses the ParsedRequest to identify and group semantic entities.

        Args:
            request: The parsed request to scan.

        Returns:
            A dictionary mapping entity category strings to sorted lists
            of unique extracted values.

        Raises:
            ValidationError: If the request is not an instance of ParsedRequest.
        """
        if not isinstance(request, ParsedRequest):
            raise ValidationError(
                "The provided request must be an instance of ParsedRequest."
            )

        text = request.normalized_text
        tokens = request.tokens
        entities: dict[str, list[str]] = {}

        # 1. URL Extraction
        urls = self._URL_PATTERN.findall(text)
        if urls:
            entities["url"] = sorted(list(set(urls)))

        # 2. File Extraction
        files = self._FILE_PATTERN.findall(text)
        if files:
            entities["file"] = sorted(list(set(files)))

        # 3. Folder Extraction
        folders = [match.group(0) for match in self._FOLDER_PATTERN.finditer(text)]
        folder_ind_pattern = re.compile(
            r"\b(?:folder|directory)\s+([\w\-]+)\b", re.IGNORECASE
        )
        for match in folder_ind_pattern.finditer(text):
            folders.append(match.group(1))
        if folders:
            entities["folder"] = sorted(list(set(folders)))

        # 4. Website Extraction
        matched_websites = [t for t in tokens if t in self._WEBSITES]
        web_ext_pattern = re.compile(
            r"\b[\w\-]+\.(?:com|org|net|io|edu|gov|co)\b", re.IGNORECASE
        )
        for match in web_ext_pattern.finditer(text):
            matched_websites.append(match.group(0))
        if matched_websites:
            entities["website"] = sorted(list(set(matched_websites)))

        # 5. Application Extraction
        matched_apps = []
        if "vs code" in text or "vscode" in text:
            matched_apps.append("vscode")
        for t in tokens:
            if t in self._APPLICATIONS and t != "code":
                matched_apps.append(t)
        if matched_apps:
            entities["application"] = sorted(list(set(matched_apps)))

        # 6. Person Extraction
        people = self._PERSON_PATTERN.findall(text)
        if people:
            entities["person"] = sorted(list(set(people)))

        # 7. Date Extraction
        matched_dates = [t for t in tokens if t in self._DATES]
        for match in self._DATE_PATTERN.finditer(text):
            matched_dates.append(match.group(0))
        if matched_dates:
            entities["date"] = sorted(list(set(matched_dates)))

        # 8. Time Extraction
        times = [match.group(0) for match in self._TIME_PATTERN.finditer(text)]
        if times:
            entities["time"] = sorted(list(set(times)))

        # 9. Command Extraction
        commands = [match.group(0) for match in self._COMMAND_PATTERN.finditer(text)]
        if commands:
            entities["command"] = sorted(list(set(commands)))

        return entities
