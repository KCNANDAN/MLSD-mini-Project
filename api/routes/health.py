
from fastapi import APIRouter

from api.schemas.response import HealthResponse

router = APIRouter(
    tags=["Health"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
)
def health_check():
    """
    Basic application liveness check.
    """

    return HealthResponse(
        status="ok",
        service="academic-petition-triage",
    )
