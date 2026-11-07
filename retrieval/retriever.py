
from typing import Any

from config.settings import get_settings
from retrieval.embeddings import generate_single_embedding
from retrieval.vector_store import query_collection


settings = get_settings()


def retrieve_relevant_provisions(
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant regulation chunks for a natural-language query.

    Results below the configured similarity threshold are excluded.

    ChromaDB uses cosine distance:
        similarity = 1 - cosine_distance
    """

    if not query or not query.strip():
        raise ValueError("Retrieval query cannot be empty")

    result_count = (
        settings.retrieval_top_k
        if top_k is None
        else top_k
    )

    if result_count < 1:
        raise ValueError("top_k must be at least 1")

    query_embedding = generate_single_embedding(query)

    results = query_collection(
        query_embedding=query_embedding,
        n_results=result_count,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    retrieved_provisions = []

    for document_id, document, metadata, distance in zip(
        ids,
        documents,
        metadatas,
        distances,
    ):
        similarity_score = 1.0 - float(distance)

        if similarity_score < settings.retrieval_score_threshold:
            continue

        retrieved_provisions.append({
            "document_id": document_id,
            "text": document,
            "similarity_score": similarity_score,
            "metadata": metadata,
            "source": metadata.get("filename"),
            "page_number": metadata.get("page_number"),
            "clause_reference": metadata.get("clause_reference"),
        })

    return retrieved_provisions


def retrieve_with_context(
    query: str,
    top_k: int | None = None,
) -> dict[str, Any]:
    """
    Retrieve provisions and return a structured evidence response.

    The caller must not treat an empty result as evidence of eligibility
    or ineligibility.
    """

    provisions = retrieve_relevant_provisions(
        query=query,
        top_k=top_k,
    )

    return {
        "query": query,
        "results": provisions,
        "result_count": len(provisions),
        "evidence_found": len(provisions) > 0,
        "requires_escalation": len(provisions) == 0,
    }
