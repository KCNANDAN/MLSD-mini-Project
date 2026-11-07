
import json
from typing import Any

from database.connection import SessionLocal
from database.repository import PetitionRepository


class RunService:
    """Handles retrieval of asynchronous petition-processing runs."""

    @staticmethod
    def _build_public_result(raw_result: dict[str, Any]) -> dict[str, Any]:
        """Transform internal agent output into the public API schema."""

        allowed_recommendations = {
            "grant-under-provision",
            "refer-to-committee",
            "reject",
        }

        recommendation = raw_result.get("routing_recommendation")

        # Never expose an unverified recommendation as a final position.
        if (
            not raw_result.get("verification_passed", False)
            or raw_result.get("requires_escalation", True)
        ):
            recommendation = "refer-to-committee"

        if recommendation not in allowed_recommendations:
            recommendation = "refer-to-committee"

        routing_reason = raw_result.get("routing_reason") or (
            "The petition requires human examination."
        )

        retrieved_provisions = raw_result.get("retrieved_provisions") or []
        verified_citations = raw_result.get("verified_citations") or []

        # Only expose citations that contain all required citation fields.
        citations = []

        for citation in verified_citations:
            if not isinstance(citation, dict):
                continue

            required_fields = (
                "document_name",
                "chapter",
                "clause",
                "excerpt",
            )

            if not all(citation.get(field) for field in required_fields):
                continue

            citations.append({
                "document_name": citation["document_name"],
                "chapter": citation["chapter"],
                "clause": citation["clause"],
                "page": citation.get("page"),
                "excerpt": citation["excerpt"],
            })

        # Extract the research findings from the internal agent response.
        research_findings = raw_result.get("research_findings", "")

        if isinstance(research_findings, str):
            try:
                parsed_findings = json.loads(research_findings)
                if isinstance(parsed_findings, dict):
                    research_findings = parsed_findings.get(
                        "findings",
                        research_findings,
                    )
            except (json.JSONDecodeError, TypeError):
                pass

        if not retrieved_provisions or not raw_result.get(
            "verification_passed", False
        ):
            eligibility_position = (
                "Eligibility could not be established because sufficient "
                "regulatory evidence was not retrieved and verified. "
                "The petition must be referred for human examination."
            )
        else:
            eligibility_position = str(
                research_findings
                or "The retrieved regulatory evidence requires human review."
            )

        return {
            "recommendation": recommendation,
            "basis": routing_reason,
            "eligibility_position": eligibility_position,
            "citations": citations,
            "escalation_path": (
                "Human examination committee"
                if recommendation == "refer-to-committee"
                else None
            ),
            "human_decision_required": True,
        }

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve a run and transform its result for the API."""

        with SessionLocal() as db:
            repository = PetitionRepository(db)
            run = repository.get_run(run_id)

            if run is None:
                return None

            raw_result = run.result

            public_result = None

            if isinstance(raw_result, dict):
                public_result = self._build_public_result(raw_result)

            return {
                "run_id": run.run_id,
                "status": run.status,
                "result": public_result,
                "error": run.error,
            }
