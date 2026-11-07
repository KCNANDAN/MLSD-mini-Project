
from typing import Any

from retrieval.vector_store import get_collection


def lookup_clause(
    clause_reference: str,
) -> list[dict[str, Any]]:
    """
    Find stored regulation chunks matching an exact clause reference.

    Matching is case-insensitive. The function searches metadata
    rather than relying on semantic similarity.
    """

    if not clause_reference or not clause_reference.strip():
        raise ValueError("Clause reference cannot be empty")

    collection = get_collection()

    if collection.count() == 0:
        return []

    results = collection.get(
        where={
            "clause_reference": clause_reference.strip()
        },
        include=["documents", "metadatas"],
    )

    matches = []

    for document_id, document, metadata in zip(
        results["ids"],
        results["documents"],
        results["metadatas"],
    ):
        matches.append({
            "document_id": document_id,
            "text": document,
            "clause_reference": metadata.get("clause_reference"),
            "source": metadata.get("filename"),
            "page_number": metadata.get("page_number"),
            "metadata": metadata,
        })

    return matches


def lookup_clauses(
    clause_references: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Look up multiple exact clause references."""

    if not clause_references:
        return {}

    return {
        reference: lookup_clause(reference)
        for reference in clause_references
    }
