"""Extract stage — extract content from source format to canonical Markdown."""
import json
from pathlib import Path


def run(workspace: Path, **kwargs) -> dict:
    """
    Extract content from source file into canonical Markdown.

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with extraction results
    """
    from translator.state.manifest import Manifest

    manifest = Manifest.load(workspace)
    input_file = Path(manifest.input_path)
    ext = input_file.suffix.lower()

    # Select extractor
    if ext == '.txt':
        from translator.extractors.txt import extract
    elif ext in ('.md', '.markdown'):
        from translator.extractors.markdown import extract
    elif ext == '.docx':
        from translator.extractors.docx import extract
    elif ext in ('.html', '.htm'):
        from translator.extractors.html import extract
    elif ext == '.pdf':
        from translator.extractors.pdf import extract
    elif ext == '.epub':
        from translator.extractors.epub import extract
    else:
        return {"status": "failed", "error": f"No extractor for: {ext}"}

    # Extract
    try:
        content = extract(input_file)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    # Save to canonical.md
    output_path = workspace / "chunks" / "source" / "canonical.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        "status": "completed",
        "extracted_chars": len(content),
        "output_path": str(output_path)
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)