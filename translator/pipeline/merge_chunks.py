"""Merge translated wave2 chunks into final translated.md."""

import json
import re
from pathlib import Path


def merge_chunks(project_dir: Path) -> Path:
    """Merge all wave2 translated chunks in order into translated.md.

    Reads manifest, loads all wave2 chunks in order, concatenates them,
    strips YAML frontmatter and block IDs, writes final translated.md.

    Returns:
        Path to the output file
    """
    manifest_path = project_dir / "chunks" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found at {manifest_path}")

    with open(manifest_path) as f:
        manifest = json.load(f)

    wave2_dir = project_dir / "chunks" / "translated" / "wave2"
    if not wave2_dir.exists():
        raise FileNotFoundError(f"wave2 directory not found at {wave2_dir}")

    # Sort chunks by ID (chunk_001, chunk_002, ...)
    sorted_chunks = sorted(
        manifest["chunks"],
        key=lambda c: int(c["id"].replace("chunk_", ""))
    )

    merged_lines = []
    block_ids_stripped = 0

    for chunk_meta in sorted_chunks:
        chunk_id = chunk_meta["id"]
        wave2_path = wave2_dir / f"{chunk_id}.md"

        if not wave2_path.exists():
            raise FileNotFoundError(f"wave2 chunk missing: {chunk_id} at {wave2_path}")

        content = wave2_path.read_text(encoding='utf-8')

        # Strip YAML frontmatter
        content = re.sub(r'^---\n.*?\n---\n', '', content, count=1, flags=re.DOTALL)

        # Strip block ID markers <!--BLOCK_ID: xxx-->
        before = content
        content = re.sub(r'<!--BLOCK_ID:\s*\w+\s*-->', '', content)
        if content != before:
            block_ids_stripped += 1

        # Strip reflow markers
        content = content.replace('\n<!-- refined -->\n', '\n')
        content = content.replace('\n<!-- reflow -->\n', '\n')
        content = content.strip()

        merged_lines.append(content)

    # Join chunks with double newlines
    merged = '\n\n'.join(merged_lines)

    # Normalize spacing
    merged = re.sub(r'\n{3,}', '\n\n', merged)
    merged = merged.strip()

    # Write final output
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "translated.md"

    # Add YAML frontmatter with metadata
    frontmatter = f"---\nproject: {project_dir.name}\nstage: merged\nword_count: {len(merged.split())}\n---\n\n"

    output_path.write_text(frontmatter + merged, encoding='utf-8')

    # Also write debug version (with block IDs for reference)
    debug_path = output_dir / "translated.debug.md"
    debug_path.write_text(frontmatter + merged + '\n\n<!-- DEBUG: block IDs stripped during merge -->', encoding='utf-8')

    print(f"  merged {len(sorted_chunks)} chunks, {block_ids_stripped} block IDs stripped")

    return output_path