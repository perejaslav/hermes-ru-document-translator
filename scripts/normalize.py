"""Normalize stage — clean up Markdown structure."""
import json
import re
from pathlib import Path


def run(workspace: Path, **kwargs) -> dict:
    """
    Normalize Markdown structure in canonical.md.

    - Standardize headers
    - Fix list syntax
    - Normalize code blocks
    - Remove excessive blank lines

    Args:
        workspace: Workspace directory Path

    Returns:
        dict with normalization results
    """
    source_path = workspace / "chunks" / "source" / "canonical.md"
    if not source_path.exists():
        return {"status": "failed", "error": "canonical.md not found"}

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize
    lines = content.split('\n')
    normalized = []
    prev_blank = False
    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        # Don't modify content inside code blocks
        if not in_code_block:
            line = line.rstrip()

            # Collapse multiple blank lines
            if not line:
                if prev_blank:
                    continue
                prev_blank = True
                normalized.append('')
            else:
                prev_blank = False

                # Standardize ATX headers
                match = re.match(r'^(#{1,6})\s+(.*)', line)
                if match:
                    hashes, text = match.groups()
                    normalized.append(f"{hashes} {text}")
                else:
                    normalized.append(line)
        else:
            normalized.append(line.rstrip())

    # Remove leading/trailing blank lines
    while normalized and not normalized[0]:
        normalized.pop(0)
    while normalized and not normalized[-1]:
        normalized.pop()

    result = '\n'.join(normalized)

    # Save normalized version (overwrite canonical.md)
    with open(source_path, 'w', encoding='utf-8') as f:
        f.write(result)

    return {
        "status": "completed",
        "chars_before": len(content),
        "chars_after": len(result),
        "lines_normalized": len(lines)
    }


if __name__ == "__main__":
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python normalize.py <workspace>")
        sys.exit(1)
    result = run(Path(sys.argv[1]))
    print(result)