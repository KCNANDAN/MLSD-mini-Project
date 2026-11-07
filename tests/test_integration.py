import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from database.connection import Base
from database.models import ProcessingRun, AuditEvent


@pytest.fixture
def isolated_database(tmp_path):
    """Create a temporary SQLite database for integration tests."""

    database_path = tmp_path / "integration_test.db"

    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    yield TestSessionLocal

    test_engine.dispose()


@pytest.fixture
def valid_petition():
    return {
        "student_reference": "INTEGRATION-TEST-001",
        "petition_type": "attendance",
        "admission_batch": "2024",
        "semester": 5,
        "description": (
            "Request for attendance condonation due to "
            "documented medical circumstances."
        ),
        "additional_details": {
            "attendance_percentage": 72,
            "medical_grounds": True,
        },
    }


def test_petition_submission_and_worker_processing(
    monkeypatch,
    isolated_database,
    valid_petition,
):
    """Test submission, persistence, worker execution and public result."""

    import services.petition_service as petition_module
    import worker.tasks as worker_module
    import services.run_service as run_module

    # Use the temporary database in all three components.
    monkeypatch.setattr(
        petition_module,
        "SessionLocal",
        isolated_database,
    )

    monkeypatch.setattr(
        worker_module,
        "SessionLocal",
        isolated_database,
    )

    monkeypatch.setattr(
        run_module,
        "SessionLocal",
        isolated_database,
    )

    # Replace Redis enqueue with a controlled mock.
    enqueued_jobs = []

    def mock_enqueue(run_id, petition_id):
        enqueued_jobs.append((run_id, petition_id))
        return "mock-rq-job-001"

    monkeypatch.setattr(
        petition_module,
        "enqueue_petition",
        mock_enqueue,
    )

    # Submit the petition through the actual service.
    service = petition_module.PetitionService()

    submission = service.submit_petition(valid_petition)

    assert submission["status"] == "queued"
    assert len(enqueued_jobs) == 1

    run_id, petition_id = enqueued_jobs[0]

    assert submission["run_id"] == run_id

    # Simulate the Research and Verification Agents.
    async def mock_agent_graph(initial_state):
        assert initial_state["run_id"] == run_id
        assert initial_state["petition_id"] == petition_id

        return {
            "run_id": run_id,
            "petition_id": petition_id,
            "petition_category": "attendance",
            "classification_confidence": 0.95,
            "proposed_recommendation": "refer-to-committee",
            "verified_recommendation": "refer-to-committee",
            "routing_recommendation": "refer-to-committee",
            "routing_reason": "No verified regulatory evidence is available.",
            "verification_passed": False,
            "requires_escalation": True,
            "retrieved_provisions": [],
            "verified_citations": [],
            "research_findings": (
                "Official university regulation evidence is unavailable."
            ),
            "verification_findings": (
                "Verification could not proceed because evidence is empty."
            ),
            "agent_steps": 3,
            "tool_calls": 2,
            "errors": ["No regulatory evidence retrieved."],
        }

    monkeypatch.setattr(
        worker_module,
        "run_agent_graph",
        mock_agent_graph,
    )

    # Execute the actual worker processing implementation.
    worker_result = asyncio.run(
        worker_module._process_petition_async_impl(
            run_id=run_id,
            petition_id=petition_id,
        )
    )

    assert worker_result["routing_recommendation"] == "refer-to-committee"
    assert worker_result["verification_passed"] is False
    assert worker_result["requires_escalation"] is True

    # Retrieve the result through the actual public RunService.
    public_run = run_module.RunService().get_run(run_id)

    assert public_run["status"] == "completed"
    assert public_run["result"]["recommendation"] == "refer-to-committee"
    assert public_run["result"]["citations"] == []
    assert public_run["result"]["human_decision_required"] is True

    # Verify the persisted database state.
    with isolated_database() as db:
        run = db.query(ProcessingRun).filter_by(
            run_id=run_id
        ).first()

        assert run is not None
        assert run.status == "completed"
        assert run.error is None

        audit = db.query(AuditEvent).filter_by(
            run_id=run_id,
            event_type="petition_processing_completed",
        ).first()

        assert audit is not None


def test_queue_failure_marks_run_failed(
    monkeypatch,
    isolated_database,
    valid_petition,
):
    """Ensure a failed queue submission never leaves a queued run."""

    import services.petition_service as petition_module

    monkeypatch.setattr(
        petition_module,
        "SessionLocal",
        isolated_database,
    )

    def failing_enqueue(run_id, petition_id):
        raise ConnectionError("Simulated Redis connection failure")

    monkeypatch.setattr(
        petition_module,
        "enqueue_petition",
        failing_enqueue,
    )

    service = petition_module.PetitionService()

    with pytest.raises(RuntimeError, match="could not be queued"):
        service.submit_petition(valid_petition)

    # Confirm the failed status was persisted.
    with isolated_database() as db:
        runs = db.query(ProcessingRun).all()

        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert "Queue submission failed" in runs[0].error
