
"""Locust load tests for the Academic Petition Triage API."""

import time
from uuid import uuid4

from locust import HttpUser, between, task


class PetitionUser(HttpUser):
    """Simulate a student submitting and tracking a petition."""

    wait_time = between(1, 3)

    @task
    def submit_and_track_petition(self):
        student_reference = f"LOAD-{uuid4().hex[:12]}"

        payload = {
            "student_reference": student_reference,
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
                "load_test": True,
            },
        }

        with self.client.post(
            "/api/v1/petitions",
            json=payload,
            name="POST /api/v1/petitions",
            catch_response=True,
        ) as response:

            if response.status_code != 202:
                response.failure(
                    f"Petition submission failed: HTTP "
                    f"{response.status_code}"
                )
                return

            try:
                run_id = response.json()["run_id"]
            except (ValueError, KeyError):
                response.failure("Response did not contain a run_id")
                return

            response.success()

        # Track the asynchronous processing run.
        for _ in range(60):
            with self.client.get(
                f"/api/v1/runs/{run_id}",
                name="GET /api/v1/runs/[run_id]",
                catch_response=True,
            ) as status_response:

                if status_response.status_code != 200:
                    status_response.failure(
                        f"Run lookup failed: HTTP "
                        f"{status_response.status_code}"
                    )
                    return

                try:
                    run_status = status_response.json()["status"]
                except (ValueError, KeyError):
                    status_response.failure(
                        "Invalid run-status response"
                    )
                    return

                if run_status == "completed":
                    status_response.success()
                    return

                if run_status == "failed":
                    status_response.failure(
                        "Petition processing failed"
                    )
                    return

                status_response.success()

            time.sleep(1)

        # Report runs that did not finish within 60 seconds.
        self.environment.events.request.fire(
            request_type="PROCESSING",
            name="Petition processing timeout",
            response_time=60000,
            response_length=0,
            exception=TimeoutError(
                "Petition did not complete within 60 seconds"
            ),
        )
