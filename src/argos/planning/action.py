"""Definition of the Action StrEnum catalog.

This module declares the approved atomic actions that ARGOS downstream executors
are capable of performing.
"""

from enum import StrEnum


class Action(StrEnum):
    """Enumeration of canonical atomic actions.

    This catalog maps planning output actions to standardized lowercase
    snake_case strings.
    """

    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    SEARCH_WEB = "search_web"
    RUN_COMMAND = "run_command"
    ASK_CLARIFICATION = "ask_clarification"
