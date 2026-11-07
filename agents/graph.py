
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.state import PetitionAgentState
from agents.research_agent import research_petition
from agents.verification_agent import verification_agent
from agents.routing import route_petition
from config.settings import get_settings


settings = get_settings()


async def safe_research_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Execute research with fail-safe error handling."""

    try:
        return await research_petition(state)

    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(
            f"Research Agent failed: {str(exc)}"
        )

        return {
            "current_agent": "research_agent",
            "research_complete": True,
            "research_findings": "",
            "retrieved_provisions": [],
            "requires_escalation": True,
            "errors": errors,
            "agent_steps": state.get("agent_steps", 0) + 1,
        }


async def safe_verification_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Execute verification with fail-safe error handling."""

    try:
        return await verification_agent(state)

    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(
            f"Verification Agent failed: {str(exc)}"
        )

        return {
            "current_agent": "verification_agent",
            "verification_passed": False,
            "verification_findings": (
                "Verification failed unexpectedly."
            ),
            "verified_citations": [],
            "verification_complete": True,
            "requires_escalation": True,
            "errors": errors,
            "agent_steps": state.get("agent_steps", 0) + 1,
        }


def build_agent_graph():
    """
    Build the Academic Petition Triage LangGraph.

    Workflow:
        START
          -> Research Agent
          -> Verification Agent
          -> Routing
          -> END
    """

    workflow = StateGraph(PetitionAgentState)

    # Register the workflow nodes.
    workflow.add_node(
        "research_agent",
        safe_research_node,
    )

    workflow.add_node(
        "verification_agent",
        safe_verification_node,
    )

    workflow.add_node(
        "routing",
        route_petition,
    )

    # Define the execution order.
    workflow.add_edge(
        START,
        "research_agent",
    )

    workflow.add_edge(
        "research_agent",
        "verification_agent",
    )

    workflow.add_edge(
        "verification_agent",
        "routing",
    )

    workflow.add_edge(
        "routing",
        END,
    )

    return workflow.compile()


# Compile the graph once and reuse it.
agent_graph = build_agent_graph()


async def run_agent_graph(
    initial_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the complete multi-agent petition workflow.

    Returns the final LangGraph state.
    """

    if not isinstance(initial_state, dict):
        raise TypeError(
            "initial_state must be a dictionary."
        )

    if not initial_state.get("petition"):
        raise ValueError(
            "Initial state must contain petition data."
        )

    # Initialise shared state fields.
    prepared_state = {
        **initial_state,
        "retrieved_provisions": initial_state.get(
            "retrieved_provisions", []
        ),
        "verified_citations": initial_state.get(
            "verified_citations", []
        ),
        "errors": initial_state.get("errors", []),
        "agent_steps": initial_state.get(
            "agent_steps", 0
        ),
        "tool_calls": initial_state.get(
            "tool_calls", 0
        ),
        "retry_count": initial_state.get(
            "retry_count", 0
        ),
        "requires_escalation": initial_state.get(
            "requires_escalation", False
        ),
    }

    # The research agent enforces its own step and tool-call
    # limits. This graph-level limit protects orchestration.
    recursion_limit = max(
        settings.max_agent_steps + 10,
        20,
    )

    result = await agent_graph.ainvoke(
        prepared_state,
        config={
            "recursion_limit": recursion_limit,
        },
    )

    return result
