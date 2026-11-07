from typing import Any

from database.connection import SessionLocal
from database.repository import PetitionRepository


class FeedbackService:
    """Handles feedback submitted for petition-processing runs."""

    def submit_feedback(
        self,
        feedback_data: dict[str, Any],
    ) -> dict[str, str]:
        """Validate the referenced run and persist user feedback."""

        with SessionLocal() as db:
            repository = PetitionRepository(db)

            run = repository.get_run(feedback_data["run_id"])

            if run is None:
                raise ValueError("The specified processing run does not exist.")

            feedback = repository.create_feedback(feedback_data)

            return {
                "feedback_id": feedback.feedback_id,
                "run_id": feedback.run_id,
                "message": "Feedback recorded successfully.",
            }