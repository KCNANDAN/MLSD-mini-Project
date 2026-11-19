
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from retrieval.document_loader import load_document_paths
from retrieval.parser import parse_document
from retrieval.chunker import chunk_document
from retrieval.embeddings import generate_embeddings
from retrieval.vector_store import get_collection, upsert_chunks


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "storage" / "ingestion_manifest.json"


# Explicit allow-list: only these approved documents are indexed.
APPROVED_DOCUMENTS = {
    "corpus/regulations/PES_University_Act_Official.txt": {
        "source_class": "official_university_act",
        "temporal_status": "foundational_legal_text_2013",
        "authority_scope": "University governance framework; not detailed BTech examination rules.",
        "indexing_note": "OCR text from the official PES University Act.",
    },
    "corpus/regulations/PES_University_Profroma.pdf": {
        "source_class": "official_ugc_proforma",
        "temporal_status": "historical_2013_2014_context",
        "authority_scope": "Historical institutional and academic assessment information.",
        "indexing_note": "Do not treat historical examination procedures as current rules without confirmation.",
    },
    "corpus/regulations/PESU_Calendar_of_Events_Aug_Dec_2026.pdf": {
        "source_class": "official_academic_calendar",
        "temporal_status": "2026_august_december",
        "authority_scope": "Academic calendar for the stated 2026 semester period.",
        "indexing_note": "Use only for dates and events within the specified calendar period.",
    },
    "corpus/examination_bylaws/PESU_Learning_and_Assessment_Process.txt": {
        "source_class": "supplementary_assessment_information",
        "temporal_status": "date_unverified",
        "authority_scope": "General learning and assessment process information.",
        "indexing_note": "Supplementary reference, not a complete examination rulebook.",
    },
    "corpus/examination_bylaws/PESU_Current_Official_FAQ.txt": {
        "source_class": "official_website_faq",
        "temporal_status": "accessed_2026_11_08",
        "authority_scope": "Limited general attendance and grading FAQ information.",
        "indexing_note": "Supplementary FAQ extract, not a complete academic regulation.",
    },
}


def relative_project_path(file_path: str | Path) -> str:
    """Return a document path relative to the project root."""
    return Path(file_path).resolve().relative_to(PROJECT_ROOT).as_posix()


def calculate_file_hash(file_path: str | Path) -> str:
    """Return the SHA-256 hash of a document."""
    digest = hashlib.sha256()

    with Path(file_path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    """Load the ingestion manifest, or return an empty manifest."""
    if not MANIFEST_PATH.exists():
        return {}

    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read ingestion manifest: %s", exc)
        return {}


def save_manifest(manifest: dict[str, Any]) -> None:
    """Save the manifest atomically."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = MANIFEST_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, ensure_ascii=False)

    temporary_path.replace(MANIFEST_PATH)


def remove_stale_chunks(
    source_path: str,
    valid_ids: set[str],
) -> int:
    """Remove obsolete chunks belonging to an updated document."""
    collection = get_collection()

    existing = collection.get(
        where={"source_path": source_path},
        include=["metadatas"],
    )

    existing_ids = set(existing.get("ids", []))
    stale_ids = existing_ids - valid_ids

    if stale_ids:
        collection.delete(ids=list(stale_ids))

    return len(stale_ids)


def ingest_document(
    document: dict[str, Any],
    manifest: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    """Parse, chunk, embed and index one approved document."""

    source_path = str(Path(document["source_path"]).resolve())
    file_path = Path(source_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {source_path}")

    relative_path = relative_project_path(file_path)

    source_profile = APPROVED_DOCUMENTS.get(relative_path)

    # Safety check: reject documents outside the approved corpus.
    if source_profile is None:
        return {
            "source": source_path,
            "status": "excluded",
            "reason": "Document is not in the approved document list.",
            "chunks": 0,
        }

    file_hash = calculate_file_hash(file_path)
    previous_record = manifest.get(source_path, {})

    if not force and previous_record.get("sha256") == file_hash:
        return {
            "source": source_path,
            "status": "skipped",
            "reason": "Document has not changed",
            "chunks": previous_record.get("chunks", 0),
        }

    # Parse the source document.
    parsed_sections = parse_document(file_path)

    if not parsed_sections:
        return {
            "source": source_path,
            "status": "failed",
            "reason": "No readable text was extracted.",
            "chunks": 0,
        }

    # Attach provenance and source classification to every page.
    for section in parsed_sections:
        metadata = section.setdefault("metadata", {})
        metadata.update(source_profile)
        metadata["source_relative_path"] = relative_path

    # Split document sections into metadata-rich chunks.
    chunks = chunk_document(parsed_sections)

    if not chunks:
        return {
            "source": source_path,
            "status": "failed",
            "reason": "No text chunks were generated.",
            "chunks": 0,
        }

    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings.
    embeddings = generate_embeddings(texts)

    if len(embeddings) != len(chunks):
        raise ValueError(
            "Embedding count does not match chunk count."
        )

    # Store the chunks in ChromaDB.
    indexed_count = upsert_chunks(chunks, embeddings)

    # Calculate valid deterministic chunk IDs.
    valid_ids = {
        f"{chunk['metadata']['source_path']}::chunk::{chunk['metadata']['chunk_index']}"
        for chunk in chunks
    }

    # Remove old chunks that no longer exist.
    removed_count = remove_stale_chunks(
        source_path,
        valid_ids,
    )

    # Update the manifest only after successful indexing.
    manifest[source_path] = {
        "sha256": file_hash,
        "filename": file_path.name,
        "source_relative_path": relative_path,
        "source_class": source_profile["source_class"],
        "temporal_status": source_profile["temporal_status"],
        "chunks": indexed_count,
        "last_ingested_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
    }

    return {
        "source": source_path,
        "status": "ingested",
        "chunks": indexed_count,
        "stale_chunks_removed": removed_count,
    }


def ingest_corpus(force: bool = False) -> dict[str, Any]:
    """Discover documents and ingest only approved sources."""

    documents = load_document_paths()
    manifest = load_manifest()

    results = []

    for document in documents:
        try:
            result = ingest_document(
                document,
                manifest,
                force=force,
            )
            results.append(result)

        except Exception as exc:
            logger.exception(
                "Document ingestion failed: %s",
                document.get("source_path", "unknown"),
            )

            results.append({
                "source": document.get("source_path", "unknown"),
                "status": "failed",
                "reason": str(exc),
                "chunks": 0,
            })

    save_manifest(manifest)

    return {
        "total_documents": len(documents),
        "approved_documents": len(APPROVED_DOCUMENTS),
        "ingested": sum(
            result["status"] == "ingested" for result in results
        ),
        "skipped": sum(
            result["status"] == "skipped" for result in results
        ),
        "excluded": sum(
            result["status"] == "excluded" for result in results
        ),
        "failed": sum(
            result["status"] == "failed" for result in results
        ),
        "total_chunks": sum(
            result.get("chunks", 0) for result in results
        ),
        "results": results,
    }


if __name__ == "__main__":
    summary = ingest_corpus()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
