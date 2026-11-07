from types import SimpleNamespace

import pytest

from retrieval.chunker import chunk_document
from retrieval.retriever import (
    retrieve_relevant_provisions,
    retrieve_with_context,
)
from retrieval.clause_lookup import lookup_clause, lookup_clauses
from retrieval.vector_store import upsert_chunks, query_collection


# --------------------------------------------------
# Document chunking tests
# --------------------------------------------------

def test_chunk_document_extracts_clause_metadata():
    sections = [
        {
            "text": (
                "Clause 4.2 applies to attendance requests "
                "under the academic regulation."
            ),
            "metadata": {
                "filename": "synthetic_regulation.pdf",
                "page_number": 3,
            },
        }
    ]

    chunks = chunk_document(sections)

    assert len(chunks) >= 1
    assert chunks[0]["metadata"]["clause_reference"] == "Clause 4.2"
    assert chunks[0]["metadata"]["filename"] == "synthetic_regulation.pdf"
    assert chunks[0]["metadata"]["page_number"] == 3
    assert chunks[0]["metadata"]["chunk_index"] == 0


def test_chunk_document_handles_empty_input():
    assert chunk_document([]) == []


def test_chunk_document_splits_large_paragraphs(monkeypatch):
    import retrieval.chunker as chunker

    monkeypatch.setattr(
        chunker,
        "settings",
        SimpleNamespace(
            chunk_size=5,
            chunk_overlap=1,
        ),
    )

    sections = [
        {
            "text": "one two three four five six seven eight nine ten",
            "metadata": {"filename": "synthetic.txt"},
        }
    ]

    chunks = chunk_document(sections)

    assert len(chunks) == 3
    assert chunks[0]["metadata"]["word_count"] == 5
    assert chunks[1]["text"].split()[0] == "five"


def test_chunk_document_rejects_invalid_overlap(monkeypatch):
    import retrieval.chunker as chunker

    monkeypatch.setattr(
        chunker,
        "settings",
        SimpleNamespace(
            chunk_size=5,
            chunk_overlap=5,
        ),
    )

    with pytest.raises(ValueError):
        chunk_document([{"text": "Test text", "metadata": {}}])


# --------------------------------------------------
# Semantic retrieval tests
# --------------------------------------------------

def test_retrieval_rejects_empty_query():
    with pytest.raises(ValueError):
        retrieve_relevant_provisions("   ")


def test_retrieval_rejects_invalid_top_k():
    with pytest.raises(ValueError):
        retrieve_relevant_provisions("attendance rules", top_k=0)


def test_retrieval_filters_low_similarity_results(monkeypatch):
    import retrieval.retriever as retriever

    monkeypatch.setattr(
        retriever,
        "settings",
        SimpleNamespace(
            retrieval_top_k=3,
            retrieval_score_threshold=0.7,
        ),
    )

    monkeypatch.setattr(
        retriever,
        "generate_single_embedding",
        lambda query: [0.1, 0.2, 0.3],
    )

    monkeypatch.setattr(
        retriever,
        "query_collection",
        lambda query_embedding, n_results: {
            "ids": [["chunk-1", "chunk-2"]],
            "documents": [["Relevant provision", "Weak provision"]],
            "metadatas": [
                [
                    {"filename": "regulation.pdf", "clause_reference": "4.2"},
                    {"filename": "regulation.pdf", "clause_reference": "5.1"},
                ]
            ],
            "distances": [[0.1, 0.5]],
        },
    )

    results = retriever.retrieve_relevant_provisions(
        "attendance condonation"
    )

    assert len(results) == 1
    assert results[0]["document_id"] == "chunk-1"
    assert results[0]["similarity_score"] == pytest.approx(0.9)


def test_empty_retrieval_requires_escalation(monkeypatch):
    import retrieval.retriever as retriever

    monkeypatch.setattr(
        retriever,
        "generate_single_embedding",
        lambda query: [0.1, 0.2],
    )

    monkeypatch.setattr(
        retriever,
        "query_collection",
        lambda query_embedding, n_results: {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        },
    )

    result = retrieve_with_context("attendance condonation")

    assert result["result_count"] == 0
    assert result["evidence_found"] is False
    assert result["requires_escalation"] is True


# --------------------------------------------------
# Exact clause lookup tests
# --------------------------------------------------

def test_clause_lookup_rejects_empty_reference():
    with pytest.raises(ValueError):
        lookup_clause("   ")


def test_clause_lookup_returns_matching_metadata(monkeypatch):
    import retrieval.clause_lookup as clause_lookup

    class FakeCollection:
        def count(self):
            return 1

        def get(self, where, include):
            assert where == {"clause_reference": "Clause 4.2"}

            return {
                "ids": ["chunk-1"],
                "documents": ["Synthetic clause text."],
                "metadatas": [
                    {
                        "clause_reference": "Clause 4.2",
                        "filename": "regulation.pdf",
                        "page_number": 3,
                    }
                ],
            }

    monkeypatch.setattr(
        clause_lookup,
        "get_collection",
        lambda: FakeCollection(),
    )

    results = lookup_clause("Clause 4.2")

    assert len(results) == 1
    assert results[0]["document_id"] == "chunk-1"
    assert results[0]["source"] == "regulation.pdf"
    assert results[0]["page_number"] == 3


def test_clause_lookup_returns_empty_for_empty_collection(monkeypatch):
    import retrieval.clause_lookup as clause_lookup

    class EmptyCollection:
        def count(self):
            return 0

    monkeypatch.setattr(
        clause_lookup,
        "get_collection",
        lambda: EmptyCollection(),
    )

    assert lookup_clause("Clause 4.2") == []


def test_lookup_multiple_clauses_handles_empty_input():
    assert lookup_clauses([]) == [] or lookup_clauses([]) == {}


# --------------------------------------------------
# Vector store tests
# --------------------------------------------------

def test_upsert_empty_chunks_returns_zero():
    assert upsert_chunks([], []) == 0


def test_upsert_rejects_mismatched_embeddings():
    chunks = [
        {
            "text": "Synthetic provision.",
            "metadata": {"source_path": "test.pdf", "chunk_index": 0},
        }
    ]

    with pytest.raises(ValueError):
        upsert_chunks(chunks, [])


def test_query_empty_collection_returns_empty_results(monkeypatch):
    import retrieval.vector_store as vector_store

    class EmptyCollection:
        def count(self):
            return 0

    monkeypatch.setattr(
        vector_store,
        "get_collection",
        lambda: EmptyCollection(),
    )

    result = query_collection([0.1, 0.2, 0.3])

    assert result["ids"] == [[]]
    assert result["documents"] == [[]]
    assert result["metadatas"] == [[]]
    assert result["distances"] == [[]]
