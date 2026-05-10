"""PDF exporter — STUB (best-effort in v0.1).

Full implementation uses pandoc + xelatex.
If dependencies are missing, reports warning instead of failing.
"""
from pathlib import Path


def export(md_content: str, output_path: Path) -> dict:
    """
    Export Markdown content to PDF via pandoc + xelatex.

    Returns dict with status. If xelatex missing, returns warning not error.

    Args:
        md_content: Markdown content string
        output_path: Target file path

    Returns:
        Result dict with status and info
    """
    import subprocess
    import shutil

    # Check pandoc
    pandoc_path = shutil.which('pandoc')
    if not pandoc_path:
        return {
            "format": "pdf",
            "status": "unavailable",
            "error": "pandoc not found. Install with: sudo apt install pandoc"
        }

    # Check xelatex
    xelatex_path = shutil.which('xelatex')
    if not xelatex_path:
        return {
            "format": "pdf",
            "status": "unavailable",
            "error": "xelatex not found. Install with: sudo apt install texlive-xetex"
        }

    # Create temp markdown file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(md_content)
        temp_md = f.name

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Use pandoc with xelatex to create PDF
        result = subprocess.run(
            [
                pandoc_path,
                temp_md,
                "-o", str(output_path),
                "--pdf-engine=xelatex",
                "-V", "mainfont=Noto Serif",
                "-V", "geometry=margin=1in",
                "-V", "lang=russian"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and output_path.exists():
            return {
                "format": "pdf",
                "status": "success",
                "path": str(output_path),
                "size": output_path.stat().st_size
            }
        else:
            return {
                "format": "pdf",
                "status": "failed",
                "error": result.stderr or "Unknown error",
                "stdout": result.stdout
            }
    except subprocess.TimeoutExpired:
        return {
            "format": "pdf",
            "status": "failed",
            "error": "PDF export timed out (120s)"
        }
    except Exception as e:
        return {
            "format": "pdf",
            "status": "failed",
            "error": str(e)
        }
    finally:
        import os
        os.unlink(temp_md)


# For pipeline compatibility
def run(workspace: Path, **kwargs) -> dict:
    """Stub compatible with pipeline stage interface."""
    return {"status": "stub", "stage": "export_pdf"}