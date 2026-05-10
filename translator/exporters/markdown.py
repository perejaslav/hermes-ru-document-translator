"""Markdown exporter."""
from pathlib import Path


def export(md_content: str, output_path: Path) -> dict:
    """
    Export Markdown content to file.

    Args:
        md_content: Markdown content string
        output_path: Target file path

    Returns:
        Result dict with status and info
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return {
        "format": "md",
        "status": "success",
        "path": str(output_path),
        "size": len(md_content)
    }