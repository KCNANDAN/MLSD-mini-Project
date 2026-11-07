
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from services.feedback_service import FeedbackService
    from services.petition_service import PetitionService
    from services.run_service import RunService


def get_petition_service() -> "PetitionService":
    """
    Dependency provider for petition operations.
    """

    try:
        from services.petition_service import PetitionService

        return PetitionService()

    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Petition service is not available.",
        ) from exc


def get_run_service() -> "RunService":
    """
    Dependency provider for run-status operations.
    """

    try:
        from services.run_service import RunService

        return RunService()

    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Run service is not available.",
        ) from exc


def get_feedback_service() -> "FeedbackService":
    """
    Dependency provider for feedback operations.
    """

    try:
        from services.feedback_service import FeedbackService

        return FeedbackService()

    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback service is not available.",
        ) from exc
