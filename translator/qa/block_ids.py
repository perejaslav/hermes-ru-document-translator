"""Block ID integrity check."""
import re
import json
from pathlib import Path


BLOCK_ID_PATTERN = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')


def check_block_ids(workspace: Path) -> dict:
    """Verify BLOCK_ID integrity in translated document."""
    # Load block index
    block_index_path = workspace / "state" / "block_index.json"
    if not block_index_path.exists():
        return {"status": "skipped", "reason": "No block_index.json"}

    with open(block_index_path, 'r', encoding='utf-8') as f:
        block_data = json.load(f)

    source_blocks = set(block_data.get("blocks", {}).keys())

    # Load translated content
    translated_path = workspace / "output" / "translated.md"
    if not translated_path.exists():
        return {"status": "skipped", "reason": "No translated.md yet"}

    with open(translated_path, 'r', encoding='utf-8') as f:
        content = f.read()

    found_ids = set(BLOCK_ID_PATTERN.findall(content))

    # Check for duplicates
    all_ids = BLOCK_ID_PATTERN.findall(content)
    duplicates = [id for id in set(all_ids) if all_ids.count(id) > 1]

    missing = source_blocks - found_ids
    extra = found_ids - source_blocks

    return {
        "status": "completed",
        "source_count": len(source_blocks),
        "found_count": len(found_ids),
        "duplicate_ids": duplicates,
        "missing": list(missing),
        "extra": list(extra),
        "valid": len(missing) == 0 and len(extra) == 0 and len(duplicates) == 0
    }


if __name__ == "__main__":
    import sys
    result = check_block_ids(Path(sys.argv[1] if len(sys.argv) > 1 else '.'))
    print(json.dumps(result, indent=2))