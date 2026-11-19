
import re
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader


def _clean_text(text: str) -> str:
    """Normalize whitespace without removing meaningful paragraph content."""
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_pdf(path: Path) -> list[dict[str, Any]]:
    """Extract text page by page from a PDF."""
    path = Path(path)
    reader = PdfReader(str(path))
    parsed_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = _clean_text(page.extract_text() or "")

        if not text:
            continue

        parsed_pages.append({
            "text": text,
            "metadata": {
                "filename": path.name,
                "source_path": str(path.resolve()),
                "file_type": "pdf",
                "page_number": page_number,
            },
        })

    return parsed_pages


def parse_docx(path: Path) -> list[dict[str, Any]]:
    """Extract paragraphs and tables from a DOCX document."""
    path = Path(path)
    document = DocxDocument(str(path))

    sections = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            sections.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [
                cell.text.strip().replace("\n", " ")
                for cell in row.cells
            ]

            if any(cells):
                sections.append(" | ".join(cells))

    text = "\n".join(sections)

    if not text:
        return []

    return [{
        "text": text,
        "metadata": {
            "filename": path.name,
            "source_path": str(path.resolve()),
            "file_type": "docx",
            "page_number": None,
        },
    }]


def parse_text_file(path: Path) -> list[dict[str, Any]]:
    """
    Extract text from TXT or Markdown documents.

    If the file contains OCR page markers such as
    ===== PAGE 1 =====, preserve each page separately
    with its corresponding page number.
    """
    path = Path(path)
    raw_text = path.read_text(encoding="utf-8")

    page_pattern = re.compile(
        r"(?m)^[ \t]*={3,}[ \t]*PAGE[ \t]+(\d+)[ \t]*={3,}[ \t]*$"
    )

    matches = list(page_pattern.finditer(raw_text))
    sections = []

    # Handle OCR-generated text containing page markers.
    if matches:
        for index, match in enumerate(matches):
            start = match.end()

            if index + 1 < len(matches):
                end = matches[index + 1].start()
            else:
                end = len(raw_text)

            text = _clean_text(raw_text[start:end])

            if not text:
                continue

            sections.append({
                "text": text,
                "metadata": {
                    "filename": path.name,
                    "source_path": str(path.resolve()),
                    "file_type": path.suffix.lower().lstrip("."),
                    "page_number": int(match.group(1)),
                },
            })

    # Handle ordinary TXT or Markdown files without page markers.
    else:
        text = _clean_text(raw_text)

        if text:
            sections.append({
                "text": text,
                "metadata": {
                    "filename": path.name,
                    "source_path": str(path.resolve()),
                    "file_type": path.suffix.lower().lstrip("."),
                    "page_number": None,
                },
            })

    return sections


def parse_document(file_path: str | Path) -> list[dict[str, Any]]:
    """
    Parse a supported document into text sections
    with source and page metadata.
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Document not found: {path}")

    extension = path.suffix.lower()

    if extension == ".pdf":
        return parse_pdf(path)

    if extension == ".docx":
        return parse_docx(path)

    if extension in {".txt", ".md"}:
        return parse_text_file(path)

    raise ValueError(
        f"Unsupported document format: {extension}"
    )
