
from fastapi import APIRouter, Depends, status

from api.dependencies import get_feedback_service
from api.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
)

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback for a petition run",
)
def submit_feedback(
    feedback: FeedbackCreate,
    service=Depends(get_feedback_service),
):
    """
    Persist feedback associated with a completed petition run.
    """

    return service.submit_feedback(
        feedback.model_dump()
    )
