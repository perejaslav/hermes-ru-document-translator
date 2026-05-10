"""Chunk index — tracks all chunks and their translation status."""
import json
from pathlib import Path
from enum import Enum
from datetime import datetime


class ChunkStatus(str, Enum):
    PENDING = "pending"
    TRANSLATED = "translated"
    FAILED = "failed"
    REVIEWED = "reviewed"


class ChunkIndex:
    """Tracks all chunks and their processing status."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.chunks = []  # List of chunk dicts

    def add_chunk(self, chunk_id: str, file_path: Path, block_ids: list, char_count: int):
        """Add a chunk to the index."""
        self.chunks.append({
            "chunk_id": chunk_id,
            "source_path": str(file_path),
            "block_ids": block_ids,
            "char_count": char_count,
            "token_estimate": char_count // 4,  # Rough estimate
            "status": "pending",
            "translated_path": None,
            "added_at": datetime.now().isoformat()
        })

    def mark_translated(self, chunk_id: str, translated_path: Path):
        """Mark chunk as translated."""
        for chunk in self.chunks:
            if chunk["chunk_id"] == chunk_id:
                chunk["status"] = "translated"
                chunk["translated_path"] = str(translated_path)
                chunk["translated_at"] = datetime.now().isoformat()
                break

    def mark_failed(self, chunk_id: str, error: str = None):
        """Mark chunk as failed."""
        for chunk in self.chunks:
            if chunk["chunk_id"] == chunk_id:
                chunk["status"] = "failed"
                chunk["error"] = error
                break

    def mark_reviewed(self, chunk_id: str):
        """Mark chunk as reviewed (QA passed)."""
        for chunk in self.chunks:
            if chunk["chunk_id"] == chunk_id:
                chunk["status"] = "reviewed"
                break

    def get_pending(self) -> list:
        """Get list of pending chunk IDs."""
        return [c["chunk_id"] for c in self.chunks if c["status"] == "pending"]

    def get_translated(self) -> list:
        """Get list of translated chunk IDs."""
        return [c["chunk_id"] for c in self.chunks if c["status"] == "translated"]

    def get_failed(self) -> list:
        """Get list of failed chunk IDs."""
        return [c["chunk_id"] for c in self.chunks if c["status"] == "failed"]

    def stats(self) -> dict:
        """Get statistics about chunks."""
        total = len(self.chunks)
        translated = len(self.get_translated())
        failed = len(self.get_failed())
        pending = len(self.get_pending())
        return {
            "total": total,
            "translated": translated,
            "failed": failed,
            "pending": pending,
            "completion_rate": translated / total if total > 0 else 0
        }

    def save(self):
        path = self.workspace / "state" / "chunk_index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "chunks": self.chunks,
                "stats": self.stats()
            }, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, workspace: Path) -> "ChunkIndex":
        path = workspace / "state" / "chunk_index.json"
        if not path.exists():
            return cls(workspace)

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        instance = cls(workspace)
        instance.chunks = data.get("chunks", [])
        return instance