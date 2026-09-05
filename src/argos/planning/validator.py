"""SchemaValidator for the ARGOS planning subsystem.

Validates intent entity parameters against authoritative ParameterSpec contracts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from argos.capabilities.models import ActionSchemaDescriptor
from argos.planning.exceptions import (
    InvalidParameterError,
    MissingParameterError,
    ReservedParameterError,
)


class SchemaValidator:
    """Validates entity parameters against canonical ParameterSpec contracts."""

    @staticmethod
    def validate_and_coerce(
        schema: ActionSchemaDescriptor,
        raw_parameters: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Validates and coerces parameters against an ActionSchemaDescriptor.

        Args:
            schema: The ActionSchemaDescriptor containing parameter specs.
            raw_parameters: The raw parameters/entities passed from intent analysis.

        Returns:
            A tuple of (validated_parameters, unmapped_entities).

        Raises:
            ReservedParameterError: If any parameter key starts with '_'.
            MissingParameterError: If a required parameter is missing.
            InvalidParameterError: If parameter type or constraint validation fails.
        """
        # 1. Reserved parameter check
        for key in raw_parameters:
            if key.startswith("_"):
                raise ReservedParameterError(
                    f"Parameter '{key}' starts with reserved prefix '_'."
                )

        schema_param_names = {spec.name for spec in schema.parameters}
        validated: dict[str, Any] = {}
        unmapped: dict[str, Any] = {}

        # 2. Validate declared parameter specs
        for spec in schema.parameters:
            name = spec.name
            if name not in raw_parameters:
                if spec.required and spec.default is None:
                    raise MissingParameterError(
                        f"Required parameter '{name}' is missing."
                    )
                if spec.default is not None:
                    validated[name] = spec.default
                continue

            val = raw_parameters[name]

            # Handle None value explicitly
            if val is None:
                if spec.param_type is not type(None) and not isinstance(
                    val, spec.param_type
                ):
                    if spec.required and spec.default is None:
                        raise MissingParameterError(
                            f"Required parameter '{name}' is missing or None."
                        )
                    raise InvalidParameterError(
                        f"Parameter '{name}' cannot be None for type "
                        f"'{spec.param_type.__name__}'."
                    )
                validated[name] = val
                continue

            # Type checking and coercion
            coerced_val = val
            if not isinstance(val, spec.param_type):
                coerced = False
                if spec.param_type is str:
                    coerced_val = str(val)
                    coerced = True
                elif spec.param_type is int and isinstance(val, (float, str)):
                    try:
                        coerced_val = int(val)
                        coerced = True
                    except (ValueError, TypeError):
                        pass
                elif spec.param_type is float and isinstance(val, (int, str)):
                    try:
                        coerced_val = float(val)
                        coerced = True
                    except (ValueError, TypeError):
                        pass
                elif spec.param_type is bool and isinstance(val, str):
                    if val.lower() in ("true", "1"):
                        coerced_val = True
                        coerced = True
                    elif val.lower() in ("false", "0"):
                        coerced_val = False
                        coerced = True

                if not coerced:
                    raise InvalidParameterError(
                        f"Parameter '{name}' must be of type "
                        f"'{spec.param_type.__name__}', got '{type(val).__name__}'."
                    )

            # Allowed values check
            if spec.allowed_values is not None:
                if coerced_val not in spec.allowed_values:
                    raise InvalidParameterError(
                        f"Parameter '{name}' value '{coerced_val}' is not in "
                        f"allowed values {spec.allowed_values}."
                    )

            validated[name] = coerced_val

        # 3. Collect unmapped extra entities
        for key, val in raw_parameters.items():
            if key not in schema_param_names:
                unmapped[key] = val

        return validated, unmapped
