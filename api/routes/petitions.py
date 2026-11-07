
from fastapi import APIRouter, Depends, status

from api.dependencies import get_petition_service
from api.schemas.petition import (
    PetitionAccepted,
    PetitionCreate,
)

router = APIRouter(
    prefix="/petitions",
    tags=["Petitions"],
)


@router.post(
    "",
    response_model=PetitionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a student petition",
    description=(
        "Validates and submits a synthetic student petition "
        "for asynchronous processing."
    ),
)
def submit_petition(
    petition: PetitionCreate,
    service=Depends(get_petition_service),
):
    """
    Submit a petition.

    The service is responsible for:
    - Domain validation
    - Quarantining rejected records
    - Persisting valid petitions
    - Enqueuing asynchronous processing
    """

    return service.submit_petition(
        petition.model_dump(mode="json")
    )
