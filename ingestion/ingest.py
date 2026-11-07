import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from retrieval.document_loader import discover_documents
from retrieval.parser import parse_document
from retrieval.chunker import chunk_document
from retrieval.embeddings import generate_embeddings
from retrieval.vector_store import get_collection, upsert_chunks

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path("storage/ingestion_manifest.json")


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
    """Save the manifest atomically to avoid partially written files."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = MANIFEST_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    temporary_path.replace(MANIFEST_PATH)


def remove_stale_chunks(source_path: str, valid_ids: set[str]) -> int:
    """Remove old chunks belonging to a document that no longer exist."""
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
    """Parse, chunk, embed, and index one document."""
    source_path = str(Path(document["source_path"]).resolve())
    file_path = Path(source_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {source_path}")

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
    parsed_sections = parse_document(source_path)

    # Split the parsed content into retrieval chunks.
    chunks = chunk_document(parsed_sections)

    if not chunks:
        return {
            "source": source_path,
            "status": "failed",
            "reason": "No text chunks were generated",
            "chunks": 0,
        }

    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings for all chunks.
    embeddings = generate_embeddings(texts)

    if len(embeddings) != len(chunks):
        raise ValueError("Embedding count does not match chunk count")

    # Store the chunks and their embeddings in ChromaDB.
    indexed_count = upsert_chunks(chunks, embeddings)

    # Keep the collection free of obsolete chunks after a document changes.
    valid_ids = {
        f"{chunk['metadata']['source_path']}::chunk::{chunk['metadata']['chunk_index']}"
        for chunk in chunks
    }

    removed_count = remove_stale_chunks(source_path, valid_ids)

    # Update the manifest only after successful indexing.
    manifest[source_path] = {
        "sha256": file_hash,
        "filename": file_path.name,
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
    """Discover and ingest all supported documents in the corpus."""
    documents = discover_documents()
    manifest = load_manifest()

    results = []

    for document in documents:
        try:
            result = ingest_document(document, manifest, force=force)
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
        "ingested": sum(r["status"] == "ingested" for r in results),
        "skipped": sum(r["status"] == "skipped" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
        "total_chunks": sum(r.get("chunks", 0) for r in results),
        "results": results,
    }


if __name__ == "__main__":
    summary = ingest_corpus()

    print(json.dumps(summary, indent=2))