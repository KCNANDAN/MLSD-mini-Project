from typing import Any

from pydantic import ValidationError

from api.schemas.petition import PetitionCreate


def validate_petition(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """
    Validate a petition against the API schema.

    Returns:
        (True, validated_data) when valid.
        (False, error_details) when invalid.
    """
    try:
        petition = PetitionCreate.model_validate(payload)

        return True, petition.model_dump(mode="json")

    except ValidationError as exc:
        return False, {
            "error": "petition_validation_failed",
            "details": exc.errors(include_input=False),
        }