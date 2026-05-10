"""Translation backend abstraction layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BackendResult:
    """Result of a translation operation."""
    text: str
    backend_name: str
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class TranslationBackend(ABC):
    """Abstract base class for translation backends."""

    name: str = "base"

    @abstractmethod
    def translate(self, prompt: str, *, metadata: dict | None = None) -> BackendResult:
        """Translate text using the backend.

        Args:
            prompt: The translation prompt (includes chunk text + instructions)
            metadata: Optional metadata (chunk_id, wave, project_slug, etc.)

        Returns:
            BackendResult with translated text and metadata
        """
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> bool:
        """Check if backend is available and functional."""
        raise NotImplementedError

    @abstractmethod
    def translate_chunk(
        self,
        chunk_text: str,
        chunk_id: str,
        wave: int,
        *,
        glossary: str | None = None,
        style: str | None = None,
        entities: str | None = None,
        previous_context: str | None = None,
        next_context: str | None = None,
        draft_translation: str | None = None,
    ) -> BackendResult:
        """Convenience wrapper for chunk translation.

        Args:
            chunk_text: Source chunk text
            chunk_id: Stable chunk ID
            wave: 1 or 2
            glossary: Glossary content
            style: Style guide content
            entities: Entity register content
            previous_context: Last 2 sentences of previous chunk
            next_context: First 2 sentences of next chunk
            draft_translation: Wave 1 result (required for wave 2)

        Returns:
            BackendResult with translated text
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} backend='{self.name}'>"