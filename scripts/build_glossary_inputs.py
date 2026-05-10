"""Build glossary inputs stage — prepare glossary generation data."""
import json
from pathlib import Path


def run(workspace: Path, **kwargs) -> dict:
    """
    Prepare inputs for glossary and style guide generation.

    This prepares a combined text from all chunks for LLM to analyze
    and build glossary from.

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with glossary input preparation results
    """
    # Load chunk index
    index_path = workspace / "state" / "chunk_index.json"
    if not index_path.exists():  # BUGFIX: was .exists (no call)
        return {"status": "failed", "error": "chunk_index.json not found"}

    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    chunks = index_data.get("chunks", [])
    if not chunks:
        return {"status": "failed", "error": "No chunks found"}

    # Combine first few chunks (or all if small) for glossary input
    # We don't want to send the entire book — just enough for terminology
    sample_size = min(5, len(chunks))

    combined_text = []
    for chunk_data in chunks[:sample_size]:
        chunk_path = Path(chunk_data["file"])
        if chunk_path.exists():
            with open(chunk_path, 'r', encoding='utf-8') as f:
                combined_text.append(f.read())

    # Save combined text for glossary generation
    glossary_input_path = workspace / "chunks" / "glossary_input.md"
    glossary_input_path.parent.mkdir(parents=True, exist_ok=True)
    with open(glossary_input_path, 'w', encoding='utf-8') as f:
        f.write('\n\n---\n\n'.join(combined_text))

    return {
        "status": "completed",
        "input_path": str(glossary_input_path),
        "chunks_combined": sample_size,
        "note": "Glossary generation requires Hermes agent LLM call"
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python build_glossary_inputs.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)