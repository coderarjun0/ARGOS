"""Built-in inspectable safety predicates for ARGOS Policy Engine."""

import re
from typing import Any

# Hardcoded dangerous system directory path patterns
SYSTEM_DIR_PATTERNS: list[str] = [
    r"^[a-zA-Z]:\\Windows(\\.*)?$",
    r"^[a-zA-Z]:\\Program Files(\\.*)?$",
    r"^[a-zA-Z]:\\Program Files \(x86\)(\\.*)?$",
    r"^/etc(/.*)?$",
    r"^/usr(/.*)?$",
    r"^/var(/.*)?$",
    r"^/bin(/.*)?$",
    r"^/sbin(/.*)?$",
    r"^/boot(/.*)?$",
    r"^/sys(/.*)?$",
]

DESTRUCTIVE_COMMAND_PATTERNS: list[str] = [
    r"\brm\s+-rf\s+/",
    r"\bformat\s+[a-zA-Z]:",
    r"\bmkfs\b",
    r"\bdd\s+if=",
]


def is_system_directory_path(path: str) -> bool:
    """Checks if a target path targets a protected system directory."""
    if not path or not isinstance(path, str):
        return False
    normalized = path.strip().replace("/", "\\") if "\\" in path else path.strip()
    for pattern in SYSTEM_DIR_PATTERNS:
        if (
            re.search(pattern, normalized, re.IGNORECASE)
            or re.search(pattern, path.strip(), re.IGNORECASE)
        ):
            return True
    return False


def is_destructive_system_command(command: str) -> bool:
    """Checks if a command contains destructive disk format operations."""
    if not command or not isinstance(command, str):
        return False
    for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def is_arbitrary_code_payload(val: Any) -> bool:
    """Checks if a parameter value attempts dynamic code injection."""
    if not isinstance(val, str):
        return False
    lowered = val.lower()
    dangerous_keywords = [
        "eval(",
        "exec(",
        "__import__",
        "importlib",
        "subprocess.call",
        "os.system",
    ]
    return any(kw in lowered for kw in dangerous_keywords)
