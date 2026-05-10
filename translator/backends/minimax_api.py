"""MiniMax API fallback backend."""

import os
from typing import Optional

from .base import TranslationBackend, BackendResult


class MiniMaxBackend(TranslationBackend):
    """Direct MiniMax API backend for sequential fallback translation."""

    name = "minimax_api"

    def __init__(self, api_key: str | None = None, model: str = "minimax-4o-flash"):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.model = model

    def healthcheck(self) -> bool:
        return bool(self.api_key)

    def translate(self, prompt: str, *, metadata: dict | None = None) -> BackendResult:
        if not self.api_key:
            return BackendResult(
                text="[translation unavailable: MINIMAX_API_KEY not set]",
                backend_name=self.name,
                warnings=["API key not configured"],
            )
        # TODO: implement actual API call
        return BackendResult(
            text=f"[MiniMax API not implemented yet — use mock backend for v1.0]",
            backend_name=self.name,
            model=self.model,
        )

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
        # TODO: implement actual API call
        return self.translate(chunk_text, metadata={"chunk_id": chunk_id, "wave": wave})