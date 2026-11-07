
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_run_service
from api.schemas.response import RunResponse

router = APIRouter(
    prefix="/runs",
    tags=["Runs"],
)


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get petition processing status",
)
def get_run(
    run_id: str,
    service=Depends(get_run_service),
):
    """
    Retrieve the status and result of a petition run.
    """

    run = service.get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested run was not found.",
        )

    return run
