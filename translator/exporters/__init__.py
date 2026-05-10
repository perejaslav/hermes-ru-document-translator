"""Exporters — unified export registry and dispatcher."""

import json
from pathlib import Path

from . import markdown, txt, docx, html, pdf


def get_exporters():
    """Return list of (format_name, exporter_function) tuples."""
    return [
        ("md", export_md),
        ("txt", export_txt),
        ("docx", export_docx),
        ("html", export_html),
        ("pdf", export_pdf),
    ]


def export_md(project_dir: Path) -> Path:
    """Export translated.md (copy from output/ to output/ as-is."""
    src = project_dir / "output" / "translated.md"
    if not src.exists():
        raise FileNotFoundError(f"translated.md not found at {src}")
    return src


def export_txt(project_dir: Path) -> Path:
    """Export translated content as plain text."""
    src = project_dir / "output" / "translated.md"
    if not src.exists():
        raise FileNotFoundError(f"translated.md not found")

    md_content = src.read_text(encoding='utf-8')
    # Strip YAML frontmatter
    import re
    md_content = re.sub(r'^---\n.*?\n---\n', '', md_content, count=1, flags=re.DOTALL)

    # Convert markdown to plain text
    output_path = project_dir / "output" / "translated.txt"
    result = txt.export(md_content, output_path)
    return Path(result["path"])


def export_docx(project_dir: Path) -> Path:
    """Export translated content as DOCX."""
    src = project_dir / "output" / "translated.md"
    if not src.exists():
        raise FileNotFoundError(f"translated.md not found")

    md_content = src.read_text(encoding='utf-8')
    import re
    md_content = re.sub(r'^---\n.*?\n---\n', '', md_content, count=1, flags=re.DOTALL)

    output_path = project_dir / "output" / "translated.docx"
    result = docx.export(md_content, output_path)
    return Path(result["path"])


def export_html(project_dir: Path) -> Path:
    """Export translated content as HTML."""
    src = project_dir / "output" / "translated.md"
    if not src.exists():
        raise FileNotFoundError(f"translated.md not found")

    md_content = src.read_text(encoding='utf-8')
    import re
    md_content = re.sub(r'^---\n.*?\n---\n', '', md_content, count=1, flags=re.DOTALL)

    output_path = project_dir / "output" / "translated.html"
    result = html.export(md_content, output_path)
    return Path(result["path"])


def export_pdf(project_dir: Path) -> Path:
    """Export translated content as PDF via pandoc/xelatex."""
    src = project_dir / "output" / "translated.md"
    if not src.exists():
        raise FileNotFoundError(f"translated.md not found")

    md_content = src.read_text(encoding='utf-8')
    import re
    md_content = re.sub(r'^---\n.*?\n---\n', '', md_content, count=1, flags=re.DOTALL)

    output_path = project_dir / "output" / "translated.pdf"

    # Check pandoc availability
    import shutil
    if not shutil.which("pandoc"):
        raise RuntimeError("pandoc not found — PDF export unavailable")

    try:
        result = pdf.export(md_content, output_path)
        return Path(result["path"])
    except Exception as e:
        raise RuntimeError(f"PDF export failed: {e}")


# Alias for backward compatibility
exporters = list(map(lambda x: (x[0], x[1]), get_exporters()))


def run_all_exports(project_dir: Path) -> list[dict]:
    """Run all exporters and return results."""
    results = []
    for fmt, fn in get_exporters():
        try:
            output_path = fn(project_dir)
            results.append({
                "format": fmt,
                "status": "success",
                "path": str(output_path),
                "size": output_path.stat().st_size,
            })
        except Exception as e:
            results.append({
                "format": fmt,
                "status": "failed",
                "error": str(e),
            })
    return results