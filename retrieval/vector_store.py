
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from config.settings import get_settings


settings = get_settings()

VECTOR_STORE_PATH = Path("storage/chroma")


@lru_cache(maxsize=1)
def get_chroma_client():
    """Create and cache the persistent ChromaDB client."""

    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(VECTOR_STORE_PATH.resolve())
    )


def get_collection():
    """Get or create the regulation collection."""

    client = get_chroma_client()

    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={
            "description": "University regulations and examination bylaws",
            "hnsw:space": "cosine",
        },
    )


def upsert_chunks(
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> int:
    """
    Insert or update document chunks in ChromaDB.

    Chunk IDs are deterministic based on source path and chunk index.
    """
    if not chunks:
        return 0

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks must match number of embeddings"
        )

    collection = get_collection()

    ids = []
    documents = []
    metadatas = []

    for chunk, embedding in zip(chunks, embeddings):
        metadata = chunk["metadata"]

        source_path = metadata.get("source_path", "unknown")
        chunk_index = metadata.get("chunk_index", len(ids))

        chunk_id = f"{source_path}::chunk::{chunk_index}"

        # Chroma metadata supports scalar values, not None or dictionaries.
        clean_metadata = {
            key: value
            for key, value in metadata.items()
            if value is not None
            and isinstance(value, (str, int, float, bool))
        }

        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append(clean_metadata)

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(ids)


def query_collection(
    query_embedding: list[float],
    n_results: int | None = None,
) -> dict[str, Any]:
    """Search the vector collection using a query embedding."""

    collection = get_collection()

    result_count = n_results or settings.retrieval_top_k

    if collection.count() == 0:
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=min(result_count, collection.count()),
        include=["documents", "metadatas", "distances"],
    )


def delete_collection() -> None:
    """Delete the regulation collection."""

    client = get_chroma_client()

    try:
        client.delete_collection(settings.chroma_collection_name)
    except Exception:
        pass
