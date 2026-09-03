"""Constants and configuration limits for the ARGOS Memory subsystem (ADS-006)."""

from pathlib import Path

# Session Memory capacity limits
DEFAULT_MAX_SESSION_TURNS: int = 50
DEFAULT_SESSION_ID: str = "default"

# Semantic Memory limits & validation rules
MAX_KEY_LENGTH: int = 128
MAX_CATEGORY_LENGTH: int = 64
MAX_VALUE_BYTES: int = 65536  # 64 KB

KEY_PATTERN: str = r"^[a-zA-Z0-9_.-]+$"
CATEGORY_PATTERN: str = r"^[a-zA-Z0-9_.-]+$"

# SQLite configuration & defaults
DEFAULT_DB_PATH: Path = Path.home() / ".argos" / "memory.db"
DEFAULT_TIMEOUT_SECONDS: float = 5.0
SCHEMA_VERSION: int = 1
