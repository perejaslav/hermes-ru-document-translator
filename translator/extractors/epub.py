"""EPUB extractor — STUB (NOT IMPLEMENTED IN v0.1).

Full implementation deferred to v0.2+.

v0.2 will use python-epub or ebooklib for EPUB parsing.
"""

from pathlib import Path


def extract(epub_path: Path) -> str:
    """
    Extract text from EPUB file.

    Raises NotImplementedError in v0.1.
    """
    raise NotImplementedError(
        "EPUB extraction not implemented in v0.1. "
        "Supported formats: .txt, .md, .docx, .html, text-based .pdf"
    )


def get_language(epub_path: Path) -> str:
    """Stub — raises NotImplementedError."""
    raise NotImplementedError("EPUB extraction not implemented in v0.1")


def run(workspace: Path, **kwargs) -> dict:
    """Stub compatible with pipeline stage interface."""
    return {
        "status": "stub",
        "stage": "extract_epub",
        "error": "EPUB not supported in v0.1"
    }