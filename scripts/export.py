"""Export stage — export translated.md to all available formats."""
import json
from pathlib import Path


def run(workspace: Path, **kwargs) -> dict:
    """
    Export translated.md to all configured formats.

    Guaranteed: .md
    Best-effort: .docx, .html, .txt, .pdf

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with export results
    """
    from translator.state.manifest import Manifest

    manifest = Manifest.load(workspace)

    translated_md_path = workspace / "output" / "translated.md"
    if not translated_md_path.exists():
        return {"status": "failed", "error": "translated.md not found"}

    with open(translated_md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    results = []

    # Export to Markdown (already done, just reference)
    results.append({
        "format": "md",
        "status": "success",
        "path": str(translated_md_path),
        "note": "primary output"
    })

    # Export to TXT
    try:
        from translator.exporters.txt import export
        output_path = workspace / "output" / "translated.txt"
        result = export(md_content, output_path)
        results.append(result)
    except Exception as e:
        results.append({"format": "txt", "status": "failed", "error": str(e)})

    # Export to DOCX
    try:
        from translator.exporters.docx import export
        output_path = workspace / "output" / "translated.docx"
        result = export(md_content, output_path)
        results.append(result)
    except Exception as e:
        results.append({"format": "docx", "status": "failed", "error": str(e)})

    # Export to HTML
    try:
        from translator.exporters.html import export
        output_path = workspace / "output" / "translated.html"
        result = export(md_content, output_path)
        results.append(result)
    except Exception as e:
        results.append({"format": "html", "status": "failed", "error": str(e)})

    # Export to PDF (best-effort)
    try:
        from translator.exporters.pdf import export
        output_path = workspace / "output" / "translated.pdf"
        result = export(md_content, output_path)
        results.append(result)
    except Exception as e:
        results.append({"format": "pdf", "status": "unavailable", "error": str(e)})

    # Save export results
    export_report_path = workspace / "state" / "export_results.json"
    export_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(export_report_path, 'w', encoding='utf-8') as f:
        json.dump({"exports": results}, f, indent=2)

    successful = [r for r in results if r["status"] == "success"]
    return {
        "status": "completed",
        "total_formats": len(results),
        "successful": len(successful),
        "results": results
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python export.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)