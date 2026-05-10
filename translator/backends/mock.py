"""Mock translation backend for offline testing."""

import re
import hashlib
from pathlib import Path
from typing import Optional

from .base import TranslationBackend, BackendResult


# Stable glossary substitutions for mock mode
MOCK_GLOSSARY = {
    "hello": "привет",
    "world": "мир",
    "function": "функция",
    "variable": "переменная",
    "algorithm": "алгоритм",
    "data": "данные",
    "system": "система",
    "process": "процесс",
    "example": "пример",
    "result": "результат",
    "error": "ошибка",
    "method": "метод",
    "class": "класс",
    "object": "объект",
}


class MockBackend(TranslationBackend):
    """Offline test backend. Returns deterministic pseudo-translation.

    Wave 1: adds [RU] prefix to headings, replaces known glossary terms
    Wave 2: reads wave1 output, normalizes punctuation/spacing, appends <!-- refined -->
    """

    name = "mock"

    def __init__(self, *, seed: int = 42):
        self.seed = seed

    def healthcheck(self) -> bool:
        return True

    def translate(self, prompt: str, *, metadata: dict | None = None) -> BackendResult:
        chunk_text = prompt
        wave = (metadata or {}).get("wave", 1)
        return self._mock_translate(chunk_text, wave)

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
        return self._mock_translate(chunk_text, wave)

    def _mock_translate(self, text: str, wave: int) -> BackendResult:
        if wave == 1:
            return self._wave1(text)
        else:
            return self._wave2(text)

    def _wave1(self, text: str) -> BackendResult:
        """Wave 1 mock translation."""
        result = text

        # Add [RU] prefix to headings
        result = re.sub(r'^(#{1,6}\s+)(.*)$', r'\1[RU] \2', result, flags=re.MULTILINE)

        # Replace known glossary terms (case-insensitive)
        for en, ru in MOCK_GLOSSARY.items():
            pattern = re.compile(r'\b' + re.escape(en) + r'\b', re.IGNORECASE)
            result = pattern.sub(ru, result)

        # Normalize whitespace
        result = re.sub(r'[ \t]+', ' ', result)
        result = re.sub(r'\n{3,}', '\n\n', result)

        return BackendResult(
            text=result,
            backend_name=self.name,
            model="mock-v1",
        )

    def _wave2(self, text: str) -> BackendResult:
        """Wave 2 mock refinement."""
        result = text

        # Normalize punctuation spacing (Russian typography)
        result = re.sub(r'\s+([.,;:!?])', r'\1', result)
        result = re.sub(r'([.,;:!?])(?=[^\s\d])', r'\1 ', result)

        # Fix multiple spaces
        result = re.sub(r' {2,}', ' ', result)

        # Ensure proper sentence spacing
        result = re.sub(r'([.!?])\s*', r'\1\n', result)
        result = re.sub(r'\n{2,}', '\n\n', result)

        # Apply glossary substitutions again (consistency)
        for en, ru in MOCK_GLOSSARY.items():
            pattern = re.compile(r'\b' + re.escape(en) + r'\b', re.IGNORECASE)
            result = pattern.sub(ru, result)

        # Append refinement marker
        result = result.rstrip() + '\n\n<!-- refined -->'

        return BackendResult(
            text=result,
            backend_name=self.name,
            model="mock-v2",
        )