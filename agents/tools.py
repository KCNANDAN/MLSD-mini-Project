from typing import Any

from langchain_core.tools import tool

from retrieval.retriever import retrieve_with_context
from retrieval.clause_lookup import lookup_clause


def _format_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert retrieval results into serializable evidence records."""

    formatted = []

    for item in results:
        metadata = item.get("metadata", {})

        formatted.append({
            "document_id": item.get("document_id"),
            "text": item.get("text"),
            "similarity_score": item.get("similarity_score"),
            "source": item.get("source"),
            "page_number": item.get("page_number"),
            "clause_reference": item.get("clause_reference"),
            "metadata": metadata,
        })

    return formatted


@tool
def search_regulation_provisions(query: str) -> dict:
    """
    Search university regulations for provisions relevant to a student petition.

    Use this tool to find base rules, eligibility requirements, restrictions,
    and applicable academic regulation clauses.
    """

    if not query.strip():
        return {
            "evidence_found": False,
            "results": [],
            "requires_escalation": True,
        }

    response = retrieve_with_context(query)

    results = _format_results(response.get("results", []))

    return {
        "query": query,
        "evidence_found": bool(results),
        "result_count": len(results),
        "results": results,
        "requires_escalation": not bool(results),
    }


@tool
def lookup_exact_clause(clause_reference: str) -> dict:
    """
    Retrieve a specific regulation clause using its exact clause reference.

    Use this when a petition or another retrieved provision refers to a
    particular clause, such as Clause 4.2.
    """

    if not clause_reference.strip():
        return {
            "clause_reference": clause_reference,
            "evidence_found": False,
            "results": [],
        }

    matches = lookup_clause(clause_reference)

    results = []

    for item in matches:
        results.append({
            "document_id": item.get("document_id"),
            "text": item.get("text"),
            "source": item.get("source"),
            "page_number": item.get("page_number"),
            "clause_reference": item.get("clause_reference"),
            "metadata": item.get("metadata", {}),
        })

    return {
        "clause_reference": clause_reference,
        "evidence_found": bool(results),
        "result_count": len(results),
        "results": results,
    }


@tool
def search_condonation_provisions(topic: str) -> dict:
    """
    Search specifically for condonation, exceptions, relaxation,
    medical grounds, and modifying provisions related to a petition.

    Use this alongside the base-rule search when a petition requests
    an exception or relaxation of an academic requirement.
    """

    if not topic.strip():
        return {
            "evidence_found": False,
            "results": [],
            "requires_escalation": True,
        }

    targeted_query = (
        f"{topic}. Search for condonation provisions, exceptions, "
        "relaxation rules, medical grounds, discretionary powers, "
        "and modifying academic regulations."
    )

    response = retrieve_with_context(targeted_query)

    results = _format_results(response.get("results", []))

    return {
        "query": targeted_query,
        "evidence_found": bool(results),
        "result_count": len(results),
        "results": results,
        "requires_escalation": not bool(results),
    }


RESEARCH_TOOLS = [
    search_regulation_provisions,
    lookup_exact_clause,
    search_condonation_provisions,
]