
import json
from pathlib import Path
from typing import Any
from observability.tracing import observe_agent
import yaml

from config.settings import get_settings
from services.llm_service import get_llm_service


settings = get_settings()
PROMPT_PATH = Path("config/prompts.yaml")


def load_verification_prompts() -> dict[str, str]:
    """Load and validate the Verification Agent prompts."""

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt configuration not found: {PROMPT_PATH}"
        )

    with PROMPT_PATH.open("r", encoding="utf-8") as file:
        prompts = yaml.safe_load(file)

    verification = prompts.get("verification_agent", {})

    if not verification.get("system") or not verification.get("task"):
        raise ValueError(
            "Verification Agent prompts are missing or incomplete."
        )

    return verification


def _normalise_text(value: Any) -> str:
    """Normalise text for citation and evidence comparisons."""

    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def verify_citations(
    citations: list[dict[str, Any]],
    retrieved_provisions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Check whether each citation can be matched to retrieved evidence.

    This is a deterministic existence check. The LLM performs the
    separate semantic check of whether the evidence supports a claim.
    """

    verified = []
    issues = []

    for citation in citations:
        reference = _normalise_text(
            citation.get("clause_reference")
            or citation.get("reference")
        )

        document_id = _normalise_text(
            citation.get("document_id")
        )

        citation_text = _normalise_text(
            citation.get("text")
        )

        if not reference and not citation_text:
            issues.append("A citation contains neither a clause reference nor text.")
            continue

        matching_provision = None

        for provision in retrieved_provisions:
            provision_reference = _normalise_text(
                provision.get("clause_reference")
            )

            provision_document = _normalise_text(
                provision.get("document_id")
                or provision.get("doc_id")
            )

            provision_text = _normalise_text(
                provision.get("text")
            )

            reference_matches = (
                bool(reference)
                and reference == provision_reference
            )

            text_matches = (
                bool(citation_text)
                and citation_text in provision_text
            )

            document_matches = (
                not document_id
                or document_id == provision_document
            )

            if (
                (reference_matches or text_matches)
                and document_matches
            ):
                matching_provision = provision
                break

        if matching_provision:
            verified.append({
                "clause_reference": (
                    matching_provision.get("clause_reference")
                    or reference
                ),
                "document_id": (
                    matching_provision.get("document_id")
                    or matching_provision.get("doc_id")
                ),
                "text": matching_provision.get("text", ""),
                "source": matching_provision.get("source", ""),
                "page_number": matching_provision.get("page_number"),
                "verified": True,
            })
        else:
            issues.append(
                f"Citation could not be matched to retrieved evidence: "
                f"{reference or citation_text[:100]}"
            )

    return verified, issues


def _extract_json(content: str) -> dict[str, Any]:
    """Safely parse the Verification Agent's JSON response."""

    if not content:
        return {}

    content = content.strip()

    try:
        result = json.loads(content)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # Handle JSON enclosed in Markdown code fences.
    if "```" in content:
        parts = content.split("```")

        for part in parts:
            candidate = part.strip()

            if candidate.startswith("json"):
                candidate = candidate[4:].strip()

            try:
                result = json.loads(candidate)

                if isinstance(result, dict):
                    return result

            except json.JSONDecodeError:
                continue

    return {}


@observe_agent("verification_agent")
async def verification_agent(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Independently verify the Research Agent's findings and evidence.

    Returns updates to the shared LangGraph state.
    """

    retrieved_provisions = state.get(
        "retrieved_provisions", []
    )

    research_findings = state.get(
        "research_findings", ""
    )

    errors = list(state.get("errors", []))

    # Do not ask the LLM to verify evidence that does not exist.
    if not retrieved_provisions:
        return {
            "current_agent": "verification_agent",
            "verification_passed": False,
            "verified_recommendation": "refer-to-committee",
            "verification_findings": (
                "Verification could not proceed because no "
                "regulatory provisions were retrieved."
            ),
            "verified_citations": [],
            "verification_complete": True,
            "requires_escalation": True,
            "errors": errors + [
                "Verification failed: retrieved evidence is empty."
            ],
            "agent_steps": state.get("agent_steps", 0) + 1,
        }

    prompts = load_verification_prompts()

    # First perform deterministic citation-existence checks.
    research_data = _extract_json(research_findings)

    citations = research_data.get("citations", [])

    proposed_recommendation = research_data.get(
        "proposed_recommendation",
        "refer-to-committee",
    )

    if not isinstance(citations, list):
        citations = []

    verified_citations, citation_issues = verify_citations(
        citations,
        retrieved_provisions,
    )

    # Prepare independent semantic verification.
    task_prompt = prompts["task"].format(
        research_findings=json.dumps(
            research_findings,
            ensure_ascii=False,
            default=str,
        ),
        retrieved_evidence=json.dumps(
            retrieved_provisions,
            ensure_ascii=False,
            default=str,
        ),
    )

    task_prompt += """

    Return ONLY a valid JSON object with these fields:

    {
    "verification_passed": false,
    "claims_supported": false,
    "missing_provisions": [],
    "conflicts_detected": false,
    "committee_discretion": false,
    "unsupported_claims": [],
    "reasoning": "Detailed verification explanation"
    }

    Rules:
    - Do not invent citations or provisions.
    - Treat citation existence and claim support as separate checks.
    - A citation that exists does not automatically prove a claim.
    - Identify whether modifying, exception or condonation provisions
    are missing from the retrieved evidence.
    - If evidence is insufficient, verification_passed must be false.
    - If provisions conflict or committee discretion is reserved,
    require human examination officer review.
    """

    task_prompt += f"""

    The Research Agent proposed this routing recommendation:
    {proposed_recommendation}

    Independently verify whether this recommendation is supported
    by the retrieved regulatory evidence.

    Include these additional fields in your JSON response:
    - "recommendation_supported": true or false
    - "verified_recommendation": one of:
    grant-under-provision, refer-to-committee, reject

    If the evidence does not support the proposed recommendation,
    set recommendation_supported to false and verified_recommendation
    to refer-to-committee.
    """

    llm = get_llm_service()

    try:
        response = await llm.generate(
            messages=[
                {
                    "role": "system",
                    "content": prompts["system"],
                },
                {
                    "role": "user",
                    "content": task_prompt,
                },
            ],
            max_tokens=2048,
        )

        verification_data = _extract_json(response)

        if not verification_data:
            raise ValueError(
                "Verification Agent returned invalid JSON."
            )

    except Exception as exc:
        errors.append(
            f"Verification Agent execution failed: {str(exc)}"
        )

        return {
            "current_agent": "verification_agent",
            "verification_passed": False,
            "verification_findings": (
                "Verification could not be completed reliably."
            ),
            "verified_citations": verified_citations,
            "verification_complete": True,
            "requires_escalation": True,
            "errors": errors,
            "agent_steps": state.get("agent_steps", 0) + 1,
        }

    # Combine deterministic and semantic verification.
    semantic_passed = (
        verification_data.get("verification_passed") is True
        and verification_data.get("claims_supported") is True
        and verification_data.get("recommendation_supported") is True
    )   

    no_citation_issues = (
        len(citations) > 0
        and len(verified_citations) == len(citations)
        and len(citation_issues) == 0
    )

    no_missing_provisions = not verification_data.get(
        "missing_provisions", []
    )

    no_unsupported_claims = not verification_data.get(
        "unsupported_claims", []
    )

    no_conflicts = not verification_data.get(
        "conflicts_detected", False
    )

    no_reserved_discretion = not verification_data.get(
        "committee_discretion", False
    )

    verification_passed = (
        semantic_passed
        and no_citation_issues
        and no_missing_provisions
        and no_unsupported_claims
        and no_conflicts
        and no_reserved_discretion
    )

    requires_escalation = (
        state.get("requires_escalation", False)
        or not verification_passed
        or not no_conflicts
        or not no_reserved_discretion
    )

    all_issues = (
        citation_issues
        + verification_data.get("unsupported_claims", [])
        + verification_data.get("missing_provisions", [])
    )

    reasoning = verification_data.get(
        "reasoning",
        "No verification explanation was returned.",
    )

    verification_summary = {
        "reasoning": reasoning,
        "citation_issues": citation_issues,
        "unsupported_claims": verification_data.get(
            "unsupported_claims", []
        ),
        "missing_provisions": verification_data.get(
            "missing_provisions", []
        ),
        "conflicts_detected": not no_conflicts,
        "committee_discretion": not no_reserved_discretion,
        "all_issues": all_issues,
    }

    return {
        "current_agent": "verification_agent",
        "verification_passed": verification_passed,
        "verification_findings": json.dumps(
            verification_summary,
            ensure_ascii=False,
        ),
        "verified_citations": verified_citations,
        "verification_complete": True,
        "requires_escalation": requires_escalation,
        "agent_steps": state.get("agent_steps", 0) + 1,
        "errors": errors,
        "verified_recommendation": (
        verification_data.get(
            "verified_recommendation",
            "refer-to-committee",
        )
        if verification_passed
            else "refer-to-committee"
        ),
    }
