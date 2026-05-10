"""Completeness QA check."""
import re
from pathlib import Path


BLOCK_ID_PATTERN = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')


def check_completeness(workspace: Path) -> dict:
    """Check that all source BLOCK_IDs are present in translation."""
    # Load block index
    block_index_path = workspace / "state" / "block_index.json"
    if not block_index_path.exists():
        return {"status": "skipped", "reason": "No block_index.json"}

    with open(block_index_path, 'r', encoding='utf-8') as f:
        block_data = json.load(f)

    source_ids = set(block_data.get("blocks", {}).keys())

    # Load translated.md
    translated_path = workspace / "output" / "translated.md"
    if not translated_path.exists():
        return {"status": "skipped", "reason": "No translated.md yet"}

    with open(translated_path, 'r', encoding='utf-8') as f:
        translated = f.read()

    translated_ids = set(BLOCK_ID_PATTERN.findall(translated))

    missing = list(source_ids - translated_ids)
    extra = list(translated_ids - source_ids)

    return {
        "status": "completed",
        "source_count": len(source_ids),
        "translated_count": len(translated_ids),
        "missing": missing,
        "extra": extra,
        "complete": len(missing) == 0 and len(extra) == 0
    }


if __name__ == "__main__":
    import json, sys
    from pathlib import Path
    result = check_completeness(Path(sys.argv[1] if len(sys.argv) > 1 else '.'))
    print(json.dumps(result, indent=2))