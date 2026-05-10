"""Segment stage — split document into chunks for LLM translation."""
import json
import re
from pathlib import Path


TARGET_TOKENS = 1500  # rough target per chunk
MAX_TOKENS = 2500
MIN_SENTENCES = 3


def run(workspace: Path, **kwargs) -> dict:
    """
    Segment canonical.md into chunks of ~1500 tokens each.

    Rules:
    - Respect header boundaries (prefer H1, H2 as chunk breaks)
    - Respect paragraph boundaries
    - Never split mid-sentence if avoidable
    - Each chunk gets CHUNK_ID and list of BLOCK_IDs

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with segmentation results
    """
    source_path = workspace / "chunks" / "source" / "canonical.md"
    if not source_path.exists():
        return {"status": "failed", "error": "canonical.md not found"}

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract BLOCK_IDs for each chunk
    block_id_pattern = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')

    # Split into blocks (lines with BLOCK_IDs)
    lines = content.split('\n')
    chunks = []
    current_chunk = []
    current_block_ids = []
    current_chars = 0

    def finish_chunk():
        nonlocal current_chunk, current_block_ids, current_chars
        if current_chunk:
            chunks.append({
                "lines": current_chunk,
                "block_ids": list(current_block_ids),
                "char_count": current_chars
            })
            current_chunk = []
            current_block_ids = []
            current_chars = 0

    for line in lines:
        # Check for BLOCK_ID
        block_match = block_id_pattern.search(line)
        if block_match:
            current_block_ids.append(block_match.group(1))

        stripped = line.strip()

        # Header lines force chunk break
        if re.match(r'^#{1,3}\s+', stripped) and current_chunk:
            finish_chunk()

        current_chunk.append(line)
        current_chars += len(line) + 1

        # Rough token estimate: chars / 4
        tokens = current_chars // 4

        # If we've hit the limit
        if tokens >= TARGET_TOKENS:
            # Try to break at paragraph boundary
            if len(current_chunk) > MIN_SENTENCES * 2:
                finish_chunk()

    # Final chunk
    finish_chunk()

    # Save chunks to files
    chunks_dir = workspace / "chunks" / "source"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    chunk_index = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"chunk_{i+1:03d}"
        chunk_path = chunks_dir / f"{chunk_id}.md"

        # Write chunk content (lines as-is)
        chunk_text = '\n'.join(chunk["lines"])
        with open(chunk_path, 'w', encoding='utf-8') as f:
            f.write(chunk_text)

        chunk_index.append({
            "chunk_id": chunk_id,
            "file": str(chunk_path),
            "block_ids": chunk["block_ids"],
            "char_count": chunk["char_count"],
            "token_estimate": chunk["char_count"] // 4
        })

    # Save chunk index
    index_path = workspace / "state" / "chunk_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({"chunks": chunk_index, "total": len(chunks)}, f, indent=2)

    return {
        "status": "completed",
        "total_chunks": len(chunks),
        "total_chars": sum(c["char_count"] for c in chunks),
        "chunk_index": str(index_path)
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python segment.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)