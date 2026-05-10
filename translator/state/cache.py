"""Translation cache — STUB (NOT IMPLEMENTED IN v0.1).

Full implementation deferred. v0.1 does not include translation caching.
"""

from pathlib import Path


class TranslationCache:
    """
    Translation cache for storing and reusing translations.

    NOT IMPLEMENTED IN v0.1 — stub only.
    """

    def __init__(self, workspace: Path = None):
        self.workspace = workspace
        self.enabled = False

    def get(self, key: str) -> str | None:
        """Get cached translation."""
        raise NotImplementedError("Translation cache not implemented in v0.1")

    def set(self, key: str, value: str):
        """Store translation in cache."""
        raise NotImplementedError("Translation cache not implemented in v0.1")

    def clear(self):
        """Clear cache."""
        raise NotImplementedError("Translation cache not implemented in v0.1")

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "enabled": False,
            "note": "Translation cache not implemented in v0.1"
        }