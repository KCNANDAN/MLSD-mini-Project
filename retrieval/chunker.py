
import re
from typing import Any

from config.settings import get_settings


settings = get_settings()


def _extract_clause_reference(text: str) -> str | None:
    """Identify a likely regulation clause or section reference."""

    patterns = [
        r"\b(?:clause|section|regulation|rule|article)\s+\d+(?:\.\d+)*",
        r"\b\d+(?:\.\d+)+(?:\([a-zA-Z0-9]+\))*",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)

    return None


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text while retaining meaningful paragraph boundaries."""

    paragraphs = re.split(r"\n\s*\n|\n", text)

    return [
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    ]


def chunk_document(
    parsed_sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert parsed document sections into metadata-rich chunks.

    Paragraph boundaries are preserved where possible. Oversized
    paragraphs are split into smaller word-based segments.
    """

    chunk_size = settings.chunk_size
    chunk_overlap = settings.chunk_overlap

    if chunk_overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    chunks = []

    for section in parsed_sections:
        text = section["text"]
        source_metadata = section.get("metadata", {})

        paragraphs = _split_into_paragraphs(text)

        current_parts = []
        current_word_count = 0

        def save_chunk(parts: list[str]) -> None:
            if not parts:
                return

            chunk_text = "\n\n".join(parts).strip()

            if not chunk_text:
                return

            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **source_metadata,
                    "clause_reference": _extract_clause_reference(
                        chunk_text
                    ),
                    "chunk_index": len(chunks),
                    "word_count": len(chunk_text.split()),
                },
            })

        for paragraph in paragraphs:
            words = paragraph.split()

            if len(words) > chunk_size:
                if current_parts:
                    save_chunk(current_parts)
                    current_parts = []
                    current_word_count = 0

                start = 0

                while start < len(words):
                    end = min(start + chunk_size, len(words))

                    save_chunk([" ".join(words[start:end])])

                    if end == len(words):
                        break

                    start = end - chunk_overlap

                continue

            if (
                current_word_count + len(words) > chunk_size
                and current_parts
            ):
                save_chunk(current_parts)

                overlap_words = []

                if chunk_overlap:
                    previous_words = " ".join(current_parts).split()
                    overlap_words = previous_words[-chunk_overlap:]

                current_parts = (
                    [" ".join(overlap_words)] if overlap_words else []
                )

                current_word_count = len(overlap_words)

            current_parts.append(paragraph)
            current_word_count += len(words)

        if current_parts:
            save_chunk(current_parts)

    return chunks
