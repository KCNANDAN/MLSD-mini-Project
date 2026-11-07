import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import (
    get_petition_service,
    get_run_service,
    get_feedback_service,
)


class MockPetitionService:
    def submit_petition(self, petition_data):
        return {
            "run_id": "test-run-001",
            "status": "queued",
            "message": "Petition accepted for asynchronous processing.",
        }


class MockRunService:
    def get_run(self, run_id):
        if run_id != "test-run-001":
            return None

        return {
            "run_id": run_id,
            "status": "completed",
            "result": None,
            "error": None,
        }


class MockFeedbackService:
    def submit_feedback(self, feedback_data):
        return {
            "feedback_id": "feedback-001",
            "run_id": feedback_data["run_id"],
            "message": "Feedback recorded successfully.",
        }


@pytest.fixture
def client():
    app.dependency_overrides[get_petition_service] = (
        lambda: MockPetitionService()
    )
    app.dependency_overrides[get_run_service] = (
        lambda: MockRunService()
    )
    app.dependency_overrides[get_feedback_service] = (
        lambda: MockFeedbackService()
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def valid_petition_payload():
    return {
        "student_reference": "TEST-STUDENT-001",
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


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["documentation"] == "/docs"


def test_submit_petition(client, valid_petition_payload):
    response = client.post(
        "/api/v1/petitions",
        json=valid_petition_payload,
    )

    assert response.status_code == 202
    assert response.json()["run_id"] == "test-run-001"
    assert response.json()["status"] == "queued"


def test_invalid_petition_returns_422(client, valid_petition_payload):
    valid_petition_payload["semester"] = 15

    response = client.post(
        "/api/v1/petitions",
        json=valid_petition_payload,
    )

    assert response.status_code == 422


def test_get_existing_run(client):
    response = client.get("/api/v1/runs/test-run-001")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_get_nonexistent_run_returns_404(client):
    response = client.get("/api/v1/runs/unknown-run")

    assert response.status_code == 404


def test_submit_feedback(client):
    payload = {
        "run_id": "test-run-001",
        "satisfactory": True,
        "reason": "The recommendation was clearly explained.",
    }

    response = client.post(
        "/api/v1/feedback",
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["feedback_id"] == "feedback-001"


def test_invalid_feedback_returns_422(client):
    payload = {
        "run_id": "",
        "satisfactory": True,
        "reason": "OK",
    }

    response = client.post(
        "/api/v1/feedback",
        json=payload,
    )

    assert response.status_code == 422
