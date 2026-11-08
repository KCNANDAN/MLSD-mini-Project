
import pytest

from agents.verification_agent import (
    _extract_json,
    verify_citations,
)


@pytest.fixture
def retrieved_evidence():
    return [
        {
            "document_id": "chunk-1",
            "clause_reference": "Clause 4.2",
            "text": "Attendance shall be at least 80 percent.",
            "source": "PES_University_FAQ.txt",
            "page_number": 2,
        }
    ]


def test_valid_citation_is_verified(retrieved_evidence):
    citations = [
        {
            "clause_reference": "Clause 4.2",
            "document_id": "chunk-1",
            "text": "Attendance shall be at least 80 percent.",
        }
    ]

    verified, issues = verify_citations(
        citations,
        retrieved_evidence,
    )

    assert len(verified) == 1
    assert verified[0]["verified"] is True
    assert issues == []


def test_wrong_quotation_is_rejected(retrieved_evidence):
    citations = [
        {
            "clause_reference": "Clause 4.2",
            "document_id": "chunk-1",
            "text": "Attendance is optional.",
        }
    ]

    verified, issues = verify_citations(
        citations,
        retrieved_evidence,
    )

    assert verified == []
    assert len(issues) == 1


def test_wrong_document_id_is_rejected(retrieved_evidence):
    citations = [
        {
            "clause_reference": "Clause 4.2",
            "document_id": "wrong-document",
        }
    ]

    verified, issues = verify_citations(
        citations,
        retrieved_evidence,
    )

    assert verified == []
    assert len(issues) == 1


def test_reference_only_citation_is_accepted(retrieved_evidence):
    citations = [
        {
            "clause_reference": "Clause 4.2",
            "document_id": "chunk-1",
        }
    ]

    verified, issues = verify_citations(
        citations,
        retrieved_evidence,
    )

    assert len(verified) == 1
    assert issues == []


def test_text_only_citation_is_accepted(retrieved_evidence):
    citations = [
        {
            "text": "Attendance shall be at least 80 percent."
        }
    ]

    verified, issues = verify_citations(
        citations,
        retrieved_evidence,
    )

    assert len(verified) == 1
    assert issues == []


def test_empty_citation_is_rejected(retrieved_evidence):
    verified, issues = verify_citations(
        [{}],
        retrieved_evidence,
    )

    assert verified == []
    assert len(issues) == 1


def test_invalid_citation_type_is_rejected(retrieved_evidence):
    verified, issues = verify_citations(
        ["invalid"],
        retrieved_evidence,
    )

    assert verified == []
    assert len(issues) == 1


def test_extract_json_from_valid_response():
    result = _extract_json(
        '{"verification_passed": true}'
    )

    assert result == {"verification_passed": True}


def test_extract_json_from_markdown_fence():
    result = _extract_json(
        '```json\n{"verification_passed": true}\n```'
    )

    assert result == {"verification_passed": True}


def test_extract_json_rejects_invalid_response():
    assert _extract_json("not valid json") == {}


def test_extract_json_handles_empty_response():
    assert _extract_json("") == {}
