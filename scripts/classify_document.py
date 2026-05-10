"""Classify document stage — determine format and language."""
import json
from pathlib import Path


def run(workspace: Path, **kwargs) -> dict:
    """
    Classify input document: format, language, size.

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with classification results
    """
    from translator.state.manifest import Manifest

    manifest = Manifest.load(workspace)
    input_file = Path(manifest.input_path)
    ext = input_file.suffix.lower()

    # Import extractors to detect language
    if ext == '.txt':
        from translator.extractors.txt import get_language
        lang = get_language
    elif ext in ('.md', '.markdown'):
        from translator.extractors.markdown import detect_language
        lang = detect_language
    elif ext == '.docx':
        from translator.extractors.docx import get_language
        lang = get_language
    elif ext in ('.html', '.htm'):
        from translator.extractors.html import get_language
        lang = get_language
    elif ext == '.pdf':
        from translator.extractors.pdf import get_language
        lang = get_language
    else:
        return {"status": "failed", "error": f"Unsupported format: {ext}"}

    # Detect language
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        file_content = f.read()
    detected_lang = lang(file_content)

    result = {
        "status": "completed",
        "format": ext,
        "detected_language": detected_lang,
        "source_lang": manifest.source_lang,
        "size": input_file.stat().st_size
    }

    # Save classification
    state_dir = workspace / "state"
    state_dir.mkdir(exist_ok=True)
    with open(state_dir / "classification.json", 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python classify_document.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)