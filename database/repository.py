from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    AuditEvent,
    FeedbackRecord,
    PetitionRecord,
    ProcessingRun,
)


class PetitionRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_petition_and_run(
        self,
        petition_data: dict[str, Any],
    ) -> ProcessingRun:
        """Create a petition and its initial queued processing run."""

        petition = PetitionRecord(
            student_reference=str(petition_data["student_reference"]),
            petition_type=str(petition_data["petition_type"]),
            admission_batch=str(petition_data["admission_batch"]),
            semester=int(petition_data["semester"]),
            description=str(petition_data["description"]),
            additional_details=petition_data.get("additional_details", {}),
        )

        run = ProcessingRun(
            run_id=str(uuid4()),
            petition=petition,
            status="queued",
        )

        try:
            self.db.add(petition)
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            return run

        except Exception:
            self.db.rollback()
            raise

    def get_run(self, run_id: str) -> ProcessingRun | None:
        statement = select(ProcessingRun).where(
            ProcessingRun.run_id == run_id
        )
        return self.db.scalar(statement)

    def update_run(
        self,
        run_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> ProcessingRun | None:
        run = self.get_run(run_id)

        if run is None:
            return None

        run.status = status
        run.result = result
        run.error = error

        try:
            self.db.commit()
            self.db.refresh(run)
            return run

        except Exception:
            self.db.rollback()
            raise

    def create_feedback(
        self,
        feedback_data: dict[str, Any],
    ) -> FeedbackRecord:
        feedback = FeedbackRecord(
            feedback_id=str(uuid4()),
            run_id=feedback_data["run_id"],
            satisfactory=feedback_data["satisfactory"],
            reason=feedback_data["reason"],
        )

        try:
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            return feedback

        except Exception:
            self.db.rollback()
            raise

    def create_audit_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
        run_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            run_id=run_id,
            event_type=event_type,
            event_data=event_data,
        )

        try:
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            return event

        except Exception:
            self.db.rollback()
            raise