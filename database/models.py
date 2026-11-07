from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


def utc_now():
    return datetime.now(timezone.utc)


class PetitionRecord(Base):
    __tablename__ = "petitions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    student_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    petition_type: Mapped[str] = mapped_column(String(50), nullable=False)
    admission_batch: Mapped[str] = mapped_column(String(20), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    additional_details: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    runs: Mapped[list["ProcessingRun"]] = relationship(
        back_populates="petition",
        cascade="all, delete-orphan",
    )


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    petition_id: Mapped[str] = mapped_column(
        ForeignKey("petitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now,
        onupdate=utc_now, nullable=False
    )

    petition: Mapped["PetitionRecord"] = relationship(
        back_populates="runs"
    )

    feedback: Mapped[list["FeedbackRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class FeedbackRecord(Base):
    __tablename__ = "feedback"

    feedback_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("processing_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    satisfactory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    run: Mapped["ProcessingRun"] = relationship(
        back_populates="feedback"
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )