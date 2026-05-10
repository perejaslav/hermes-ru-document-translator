"""Block index — tracks all content blocks and their integrity."""
import json
import re
from pathlib import Path
from datetime import datetime


class BlockIndex:
    """Tracks all BLOCK_IDs in the document for QA."""

    BLOCK_ID_PATTERN = re.compile(r'<!--BLOCK_ID:\s*([a-zA-Z0-9_-]+)\s*-->')

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.blocks = {}  # block_id -> block_info

    def add_block(self, block_id: str, chunk_id: str, char_count: int, block_type: str = "text"):
        """Add a block to the index."""
        self.blocks[block_id] = {
            "block_id": block_id,
            "chunk_id": chunk_id,
            "char_count": char_count,
            "type": block_type,
            "added_at": datetime.now().isoformat()
        }

    def extract_from_text(self, text: str, chunk_id: str):
        """Extract BLOCK_IDs from text and add to index."""
        for match in self.BLOCK_ID_PATTERN.finditer(text):
            block_id = match.group(1)
            self.add_block(block_id, chunk_id, len(match.group(0)), "marker")

    def get_chunk_blocks(self, chunk_id: str) -> list:
        """Get all block IDs belonging to a chunk."""
        return [b["block_id"] for b in self.blocks.values() if b["chunk_id"] == chunk_id]

    def check_completeness(self, translated_text: str) -> dict:
        """
        Check that all source blocks are present in translation.

        Returns dict with:
        - missing: list of block IDs in source but not in translation
        - extra: list of block IDs in translation but not in source
        - present: list of block IDs found in both
        """
        source_ids = set(self.blocks.keys())
        translated_ids = set(self.BLOCK_ID_PATTERN.findall(translated_text))

        return {
            "missing": list(source_ids - translated_ids),
            "extra": list(translated_ids - source_ids),
            "present": list(source_ids & translated_ids),
            "source_count": len(source_ids),
            "translated_count": len(translated_ids)
        }

    def save(self):
        path = self.workspace / "state" / "block_index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "blocks": self.blocks,
                "total_blocks": len(self.blocks)
            }, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, workspace: Path) -> "BlockIndex":
        path = workspace / "state" / "block_index.json"
        if not path.exists():
            return cls(workspace)

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        instance = cls(workspace)
        instance.blocks = data.get("blocks", {})
        return instance