"""Sequential fallback backend — single-threaded translation without subagents."""

from pathlib import Path
from typing import Optional

from .base import TranslationBackend, BackendResult


class SequentialBackend(TranslationBackend):
    """Fallback backend for environments without subagent support.

    Uses direct API calls but processes chunks sequentially (no parallelism).
    This is the fallback when hermes_delegate is unavailable.
    """

    name = "sequential"

    def __init__(self, api_backend: TranslationBackend | None = None):
        """Initialize sequential backend.

        Args:
            api_backend: The actual API backend to use (e.g., MiniMax API).
                       If None, falls back to mock.
        """
        self.api_backend = api_backend

    def healthcheck(self) -> bool:
        if self.api_backend is None:
            return True  # mock mode
        return self.api_backend.healthcheck()

    def translate(self, prompt: str, *, metadata: dict | None = None) -> BackendResult:
        if self.api_backend is None:
            from .mock import MockBackend
            mock = MockBackend()
            return mock.translate(prompt, metadata=metadata)
        return self.api_backend.translate(prompt, metadata=metadata)

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
    ) -> BackendResult:
        if self.api_backend is None:
            from .mock import MockBackend
            mock = MockBackend()
            return mock.translate_chunk(
                chunk_text, chunk_id, wave,
                glossary=glossary, style=style, entities=entities,
                previous_context=previous_context, next_context=next_context,
            )
        return self.api_backend.translate_chunk(
            chunk_text, chunk_id, wave,
            glossary=glossary, style=style, entities=entities,
            previous_context=previous_context, next_context=next_context,
        )