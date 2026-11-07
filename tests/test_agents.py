import asyncio

import pytest

from agents.routing import route_petition
from agents.graph import build_agent_graph


def test_incomplete_verification_routes_to_committee():
    state = {
        "verification_complete": False,
        "verification_passed": False,
        "verified_citations": [],
    }

    result = route_petition(state)

    assert result["routing_recommendation"] == "refer-to-committee"
    assert result["requires_escalation"] is True


def test_failed_verification_routes_to_committee():
    state = {
        "verification_complete": True,
        "verification_passed": False,
        "verified_citations": [],
    }

    result = route_petition(state)

    assert result["routing_recommendation"] == "refer-to-committee"
    assert result["requires_escalation"] is True


def test_missing_citations_routes_to_committee():
    state = {
        "verification_complete": True,
        "verification_passed": True,
        "requires_escalation": False,
        "verified_citations": [],
        "verified_recommendation": "grant-under-provision",
    }

    result = route_petition(state)

    assert result["routing_recommendation"] == "refer-to-committee"


def test_valid_verified_recommendation_is_preserved():
    state = {
        "verification_complete": True,
        "verification_passed": True,
        "requires_escalation": False,
        "verified_citations": [
            {
                "document_name": "Synthetic Regulation",
                "chapter": "Chapter 1",
                "clause": "1.1",
                "excerpt": "Synthetic test provision.",
            }
        ],
        "verified_recommendation": "grant-under-provision",
    }

    result = route_petition(state)

    assert result["routing_recommendation"] == "grant-under-provision"
    assert result["requires_escalation"] is False


def test_invalid_recommendation_routes_to_committee():
    state = {
        "verification_complete": True,
        "verification_passed": True,
        "requires_escalation": False,
        "verified_citations": [{"clause": "1.1"}],
        "verified_recommendation": "automatic-approval",
    }

    result = route_petition(state)

    assert result["routing_recommendation"] == "refer-to-committee"


def test_langgraph_research_verification_handoff(monkeypatch):
    import agents.graph as graph_module

    execution_order = []

    async def mock_research(state):
        execution_order.append("research_agent")

        return {
            "current_agent": "research_agent",
            "research_complete": True,
            "retrieved_provisions": [
                {
                    "document_name": "Synthetic Regulation",
                    "chapter": "Chapter 1",
                    "clause": "1.1",
                    "excerpt": "Synthetic test provision.",
                }
            ],
            "proposed_recommendation": "grant-under-provision",
            "requires_escalation": False,
        }

    async def mock_verification(state):
        execution_order.append("verification_agent")

        assert len(state["retrieved_provisions"]) == 1

        return {
            "current_agent": "verification_agent",
            "verification_complete": True,
            "verification_passed": True,
            "verified_recommendation": "grant-under-provision",
            "verified_citations": state["retrieved_provisions"],
            "requires_escalation": False,
        }

    monkeypatch.setattr(
        graph_module,
        "safe_research_node",
        mock_research,
    )

    monkeypatch.setattr(
        graph_module,
        "safe_verification_node",
        mock_verification,
    )

    test_graph = build_agent_graph()

    result = asyncio.run(
        test_graph.ainvoke(
            {
                "petition": {
                    "petition_type": "attendance",
                    "description": "Synthetic test petition.",
                },
                "errors": [],
                "agent_steps": 0,
                "tool_calls": 0,
                "requires_escalation": False,
            }
        )
    )

    assert execution_order == [
        "research_agent",
        "verification_agent",
    ]

    assert result["verification_passed"] is True
    assert result["routing_recommendation"] == "grant-under-provision"


def test_graph_rejects_missing_petition():
    from agents.graph import run_agent_graph

    with pytest.raises(ValueError):
        asyncio.run(run_agent_graph({}))


def test_graph_rejects_non_dictionary_input():
    from agents.graph import run_agent_graph

    with pytest.raises(TypeError):
        asyncio.run(run_agent_graph("invalid"))
