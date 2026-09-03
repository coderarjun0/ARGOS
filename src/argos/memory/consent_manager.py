"""Consent Manager for the ARGOS Memory subsystem (ADS-006 Milestone 4).

Provides deterministic consent creation, provenance capture, and authorization
validation for persistent semantic memory mutations adhering to EDR-024 and ADS-006.
"""

from datetime import UTC, datetime

from argos.memory.exceptions import MemoryAuthorizationError
from argos.memory.models import AuthorizationRecord, AuthorizationType


class ConsentManager:
    """Manages memory authorization and consent provenance validation for V1."""

    def grant_explicit_consent(
        self, details: str | None = None
    ) -> AuthorizationRecord:
        """Creates an AuthorizationRecord representing explicit user consent.

        Args:
            details: Optional audit provenance message.

        Returns:
            AuthorizationRecord with granted=True and auth_type=EXPLICIT_USER_CONSENT.

        Raises:
            MemoryAuthorizationError: If details is not a string or None.
        """
        if details is not None and not isinstance(details, str):
            msg = (
                "Consent details must be a string or None, "
                f"got {type(details).__name__}."
            )
            raise MemoryAuthorizationError(msg)

        return AuthorizationRecord(
            granted=True,
            auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
            granted_at=datetime.now(UTC),
            details=details,
        )

    def deny_consent(self, details: str | None = None) -> AuthorizationRecord:
        """Creates an AuthorizationRecord representing explicit user consent denial.

        Args:
            details: Optional denial audit message.

        Returns:
            AuthorizationRecord with granted=False and auth_type=EXPLICIT_USER_CONSENT.

        Raises:
            MemoryAuthorizationError: If details is not a string or None.
        """
        if details is not None and not isinstance(details, str):
            msg = (
                "Consent details must be a string or None, "
                f"got {type(details).__name__}."
            )
            raise MemoryAuthorizationError(msg)

        return AuthorizationRecord(
            granted=False,
            auth_type=AuthorizationType.EXPLICIT_USER_CONSENT,
            granted_at=datetime.now(UTC),
            details=details,
        )

    def validate_authorization(self, authorization: AuthorizationRecord) -> None:
        """Validates that an AuthorizationRecord permits persistent mutation in V1.

        In V1, persistent mutation is authorized ONLY when:
        - authorization is an instance of AuthorizationRecord
        - authorization.granted is True
        - authorization.auth_type is AuthorizationType.EXPLICIT_USER_CONSENT
        - authorization.granted_at is a valid datetime
        - authorization.details is a string or None

        Args:
            authorization: The AuthorizationRecord to validate.

        Raises:
            MemoryAuthorizationError: If record is invalid, denied, or unauthorized.
        """
        if not isinstance(authorization, AuthorizationRecord):
            raise MemoryAuthorizationError(
                "Expected AuthorizationRecord instance, "
                f"got {type(authorization).__name__}."
            )

        if not isinstance(authorization.granted, bool) or not authorization.granted:
            raise MemoryAuthorizationError(
                "Persistent memory mutation denied: authorization.granted is False."
            )

        if authorization.auth_type != AuthorizationType.EXPLICIT_USER_CONSENT:
            msg = (
                "Persistent mutation requires EXPLICIT_USER_CONSENT, "
                f"got '{authorization.auth_type}'."
            )
            raise MemoryAuthorizationError(msg)

        if not isinstance(authorization.granted_at, datetime):
            msg = (
                "Authorization granted_at must be a datetime, "
                f"got {type(authorization.granted_at).__name__}."
            )
            raise MemoryAuthorizationError(msg)

        if authorization.details is not None and not isinstance(
            authorization.details, str
        ):
            msg = (
                "Authorization details must be a string or None, "
                f"got {type(authorization.details).__name__}."
            )
            raise MemoryAuthorizationError(msg)

    def is_authorized(self, authorization: AuthorizationRecord) -> bool:
        """Checks whether an AuthorizationRecord permits persistent mutation in V1.

        Args:
            authorization: The AuthorizationRecord to evaluate.

        Returns:
            True if authorized for persistent mutation, False otherwise.
        """
        try:
            self.validate_authorization(authorization)
            return True
        except MemoryAuthorizationError:
            return False
