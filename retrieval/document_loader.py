
from pathlib import Path

from config.settings import get_settings

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def discover_documents(
    directories: list[str | Path] | None = None,
) -> list[Path]:
    """
    Discover supported regulation documents recursively.

    By default, searches:
      - corpus/regulations/
      - corpus/examination_bylaws/
    """
    if directories is None:
        directories = [
            Path("corpus/regulations"),
            Path("corpus/examination_bylaws"),
        ]

    documents: list[Path] = []

    for directory in directories:
        root = Path(directory)

        if not root.exists():
            continue

        if not root.is_dir():
            continue

        for path in root.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ):
                documents.append(path)

    return sorted(documents)


def load_document_paths(
    directories: list[str | Path] | None = None,
) -> list[dict[str, str]]:
    """
    Return discovered document paths with basic source metadata.

    This function does not extract document text.
    """
    paths = discover_documents(directories)

    return [
        {
            "source_path": str(path.resolve()),
            "filename": path.name,
            "file_type": path.suffix.lower().lstrip("."),
        }
        for path in paths
    ]
