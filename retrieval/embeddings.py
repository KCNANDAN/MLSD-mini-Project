
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config.settings import get_settings


settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the configured sentence-transformer model once.

    The model is cached to avoid repeatedly loading it into memory.
    """
    return SentenceTransformer(settings.embedding_model)


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """Generate normalized embeddings for a list of texts."""

    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()


def generate_single_embedding(text: str) -> list[float]:
    """Generate an embedding for a single text."""

    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    return generate_embeddings([text])[0]
