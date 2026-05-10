"""Assign block IDs stage — add stable BLOCK_ID markers for QA."""
import re
import json
from pathlib import Path


BLOCK_ID_PATTERN = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')


def run(workspace: Path, **kwargs) -> dict:
    """
    Assign BLOCK_ID markers to all meaningful content blocks.

    BLOCK_IDs are used for QA completeness checks.

    Format: <!--BLOCK_ID: ch1_intro_001-->

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with block assignment results
    """
    source_path = workspace / "chunks" / "source" / "canonical.md"
    if not source_path.exists():
        return {"status": "failed", "error": "canonical.md not found"}

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove existing BLOCK_IDs for clean reassignment
    content = re.sub(BLOCK_ID_PATTERN, '', content)

    lines = content.split('\n')
    result_lines = []
    block_counter = 0
    current_section = "intro"
    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        # Inside code blocks — don't add BLOCK_IDs
        if in_code_block:
            result_lines.append(line)
            continue

        # Check for headers to derive section
        header_match = re.match(r'^(#{1,3})\s+(.+)', line)
        if header_match:
            # Derive section from header text
            header_text = header_match.group(2).lower()
            header_text = re.sub(r'[^a-z0-9]', '_', header_text)[:20]
            current_section = header_text
            block_counter = 0

        # Add BLOCK_ID to non-empty lines (paragraphs)
        stripped = line.strip()
        if stripped and not stripped.startswith('<!--'):
            block_counter += 1
            block_id = f"{current_section}_{block_counter:03d}"
            # Insert before content (after leading whitespace)
            indent = len(line) - len(line.lstrip())
            result_lines.append(' ' * indent + f"<!--BLOCK_ID: {block_id}--> {stripped}")
        else:
            result_lines.append(line)

    result = '\n'.join(result_lines)

    # Save
    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(result)

    # Create block index
    block_index_path = workspace / "state" / "block_index.json"
    block_index_path.parent.mkdir(parents=True, exist_ok=True)

    blocks = []
    for match in BLOCK_ID_PATTERN.finditer(result):
        blocks.append({
            "block_id": match.group(1),
            "position": match.start()
        })

    with open(block_index_path, 'w', encoding='utf-8') as f:
        json.dump({
            "blocks": {b["block_id"]: {"position": b["position"]} for b in blocks},
            "total_blocks": len(blocks)
        }, f, indent=2)

    return {
        "status": "completed",
        "blocks_assigned": len(blocks),
        "sections": list(set(re.findall(r'<!--BLOCK_ID: ([a-zA-Z0-9_]+)-->', result)))
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python assign_block_ids.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)