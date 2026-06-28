"""Definition of the Intent StrEnum catalog.

This module declares the approved user intent categories that the ARGOS
semantic analysis pipeline can output.
"""

from enum import StrEnum


class Intent(StrEnum):
    """Enumeration of canonical user intents.

    This catalog maps user semantic request categories to standardized lowercase
    snake_case strings. It serves as the vocabulary contract between the
    intent subsystem and downstream planners.
    """

    UNKNOWN = "unknown"
    OPEN_APPLICATION = "open_application"
    CLOSE_APPLICATION = "close_application"
    OPEN_FILE = "open_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    SEARCH_WEB = "search_web"
    RUN_COMMAND = "run_command"
    GET_INFORMATION = "get_information"
    SET_REMINDER = "set_reminder"
    CONTROL_SYSTEM = "control_system"
