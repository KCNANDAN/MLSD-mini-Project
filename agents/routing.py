
from typing import Any

from config.settings import get_settings


settings = get_settings()

VALID_RECOMMENDATIONS = {
    "grant-under-provision",
    "refer-to-committee",
    "reject",
}


def route_petition(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Determine the petition's routing recommendation.

    The routing layer does not independently decide academic
    eligibility. It permits a recommendation only when the
    evidence and Verification Agent findings support it.
    """

    errors = list(state.get("errors", []))

    # Missing or incomplete verification must never produce
    # an automatic grant or rejection.
    if not state.get("verification_complete", False):
        recommendation = "refer-to-committee"
        reason = (
            "Verification has not been completed. "
            "Human examination officer review is required."
        )

    elif not state.get("verification_passed", False):
        recommendation = "refer-to-committee"
        reason = (
            "The retrieved provisions or research findings "
            "could not be fully verified."
        )

    elif state.get("requires_escalation", False):
        recommendation = "refer-to-committee"
        reason = (
            "The case has been flagged for escalation and "
            "requires human examination officer review."
        )

    elif not state.get("verified_citations", []):
        recommendation = "refer-to-committee"
        reason = (
            "No verified regulatory citations are available "
            "to support an automated recommendation."
        )

    else:
        # The Research Agent must supply an explicit proposed
        # recommendation in its structured findings.
        proposed = state.get("verified_recommendation")

        if proposed not in VALID_RECOMMENDATIONS:
            recommendation = "refer-to-committee"
            reason = (
                "No valid evidence-backed routing recommendation "
                "was supplied by the research workflow."
            )

        elif proposed == "refer-to-committee":
            recommendation = "refer-to-committee"
            reason = (
                "The case requires examination officer or "
                "committee review under the applicable provisions."
            )

        else:
            recommendation = proposed
            reason = (
                "The recommendation passed the evidence and "
                "verification gates. The examination officer "
                "retains final decision-making authority."
            )

    # Fail-safe: never return an unsupported routing category.
    if recommendation not in VALID_RECOMMENDATIONS:
        recommendation = "refer-to-committee"
        reason = "Invalid routing output; escalated for human review."

    return {
        "current_agent": "routing",
        "routing_recommendation": recommendation,
        "routing_reason": reason,
        "requires_escalation": (
            recommendation == "refer-to-committee"
        ),
        "final_result": {
            "routing_recommendation": recommendation,
            "routing_reason": reason,
            "verified_citations": state.get(
                "verified_citations", []
            ),
            "verification_passed": state.get(
                "verification_passed", False
            ),
            "requires_escalation": (
                recommendation == "refer-to-committee"
            ),
        },
        "errors": errors,
    }
