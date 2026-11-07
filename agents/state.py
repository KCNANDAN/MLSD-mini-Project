from typing import Any, TypedDict


class PetitionAgentState(TypedDict, total=False):
    """Shared state passed between petition-processing agents."""

    # Input
    run_id: str
    petition_id: str
    petition: dict[str, Any]

    # Research agent output
    petition_category: str
    classification_confidence: float
    research_query: str
    retrieved_provisions: list[dict[str, Any]]
    research_findings: str
    research_complete: bool
    proposed_recommendation: str
    verified_recommendation: str
    evidence_found: bool

    # Verification agent output
    verification_passed: bool
    verification_findings: str
    verified_citations: list[dict[str, Any]]
    verification_complete: bool

    # Routing
    routing_recommendation: str
    routing_reason: str
    requires_escalation: bool

    # Execution control
    current_agent: str
    agent_steps: int
    tool_calls: int
    retry_count: int

    # Error handling
    errors: list[str]
    final_result: dict[str, Any] | None