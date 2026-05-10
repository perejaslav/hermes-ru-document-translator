"""EPUB exporter — STUB (NOT IMPLEMENTED IN v0.1).

Full implementation deferred to v0.2+ using python-epub or similar.
"""

from pathlib import Path


def export(md_content: str, output_path: Path) -> dict:
    """
    Export Markdown content to EPUB.

    Raises NotImplementedError in v0.1.
    """
    raise NotImplementedError(
        "EPUB export not implemented in v0.1. "
        "Supported exports: .md, .txt, .docx, .html, .pdf (best-effort)"
    )


def run(workspace: Path, **kwargs) -> dict:
    """Stub compatible with pipeline stage interface."""
    return {
        "status": "stub",
        "stage": "export_epub",
        "error": "EPUB not supported in v0.1"
    }