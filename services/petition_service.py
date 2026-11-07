from typing import Any

from database.connection import SessionLocal
from database.repository import PetitionRepository
from services.queue_service import enqueue_petition
from validation.validators import validate_petition


class PetitionService:
    """Handles petition submission and asynchronous processing."""

    def submit_petition(self, petition_data: dict[str, Any]) -> dict[str, str]:
        """
        Validate and persist a petition, then enqueue its processing job.
        """

        # 1. Validate incoming petition data.
        is_valid, validated_data = validate_petition(petition_data)

        if not is_valid:
            raise ValueError(
                f"Invalid petition data: {validated_data}"
            )

        # 2. Create the petition and processing run.
        with SessionLocal() as db:
            repository = PetitionRepository(db)

            run = repository.create_petition_and_run(
                validated_data
            )

            run_id = run.run_id
            petition_id = run.petition_id

            # 3. Submit the processing job to Redis.
            try:
                enqueue_petition(
                    run_id=run_id,
                    petition_id=petition_id,
                )

            except Exception as exc:
                # Do not leave an unqueued run marked as queued.
                repository.update_run(
                    run_id=run_id,
                    status="failed",
                    error=f"Queue submission failed: {str(exc)}",
                )
                raise RuntimeError(
                    "Petition was saved but could not be queued."
                ) from exc

        # 4. Return the immediate API response.
        return {
            "run_id": run_id,
            "status": "queued",
            "message": "Petition accepted for asynchronous processing.",
        }