"""Hermes runtime subagent backend — production backend for Hermes Agent.

Relies on ``hermes_tools.delegate_task`` which is ONLY available inside
Hermes Agent runtime (via execute_code or during agent tool execution).
DO NOT use this backend via ``python scripts/run_pipeline.py`` — it will fail
with a clear error message.

Architecture:
- Runtime detection at import/healthcheck time
- Prompt templates loaded from ``translator/prompts/``
- Subagent output sanitized via ``sanitize_subagent_output()``
- Guaranteed ``BackendResult(backend_name="hermes_delegate", model="subagent")``
"""

import os
import threading
from pathlib import Path
from typing import Optional


def is_hermes_runtime_available() -> bool:
    """Check if Hermes Agent runtime (hermes_tools) is importable.

    Returns:
        True if ``from hermes_tools import delegate_task`` succeeds.
        False if ImportError (running outside Hermes runtime).
    """
    try:
        from hermes_tools import delegate_task  # noqa: F401
        return True
    except ImportError:
        return False


# ── Prompt loading ────────────────────────────────────────────────────────

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from ``translator/prompts/``.

    Args:
        name: Filename stem (e.g. ``wave1_translation``).

    Returns:
        Prompt template string.
    """
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _build_prompt(
    template_name: str,
    **kwargs,
) -> str:
    """Load a prompt template and render it with context variables.

    Renders ``{{variable}}`` placeholders from kwargs.
    Unused placeholders are left as-is.
    """
    template = _load_prompt(template_name)
    for key, value in kwargs.items():
        if value is not None:
            template = template.replace("{{" + key + "}}", str(value))
    return template


# ── Backend class ─────────────────────────────────────────────────────────

from ..backends.base import TranslationBackend, BackendResult
from ..backends.sanitizer import sanitize_subagent_output


class HermesDelegateBackend(TranslationBackend):
    """Backend using Hermes Agent's ``delegate_task`` for subagent translation.

    Runtime-only: requires ``hermes_tools`` (Hermes Agent runtime).
    Falls early with clear error if runtime unavailable.

    Attributes:
        name: ``"hermes_delegate"``
        max_workers: Max concurrent subagents (default 3).
        preserve_markdown: Whether to enforce Markdown preservation (default True).
    """

    name = "hermes_delegate"

    def __init__(
        self,
        max_workers: int = 3,
        preserve_markdown: bool = True,
    ):
        self.max_workers = max_workers
        self.preserve_markdown = preserve_markdown
        self._semaphore = threading.Semaphore(max_workers)

    def healthcheck(self) -> bool:
        """Check if Hermes runtime is available.

        Returns:
            True if ``delegate_task`` is importable.
        """
        return is_hermes_runtime_available()

    def translate(self, prompt: str, *, metadata: dict | None = None) -> BackendResult:
        """Not used directly — use ``translate_chunk()``."""
        chunk_id = (metadata or {}).get("chunk_id", "unknown")
        wave = (metadata or {}).get("wave", 1)
        return self.translate_chunk(
            chunk_text=prompt,
            chunk_id=chunk_id,
            wave=wave,
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
        remediation_notes: str | None = None,
    ) -> BackendResult:
        """Translate a single chunk via Hermes subagent.

        Args:
            chunk_text: Source chunk text.
            chunk_id: Stable chunk identifier.
            wave: 1 (translation) or 2 (refinement).
            glossary: Glossary content.
            style: Style guide content.
            entities: Entity register content.
            previous_context: Last 2 sentences of previous chunk.
            next_context: First 2 sentences of next chunk.
            remediation_notes: For repair — issues to fix.

        Returns:
            BackendResult with cleaned translation and metadata.

        Raises:
            RuntimeError: If Hermes runtime is unavailable.
        """
        if not is_hermes_runtime_available():
            raise RuntimeError(
                "Hermes runtime backend unavailable.\n\n"
                "This backend only works inside Hermes Agent runtime\n"
                "(where hermes_tools.delegate_task is available).\n\n"
                "Do not use:\n"
                "  python scripts/run_pipeline.py ... --backend hermes_delegate\n\n"
                "outside Hermes runtime."
            )

        from hermes_tools import delegate_task

        # ── Select prompt template ──────────────────────────────────────
        if wave == 1:
            template_name = "wave1_translation"
        elif remediation_notes:
            template_name = "repair"
        else:
            template_name = "wave2_refinement"

        draft_translation = None
        if wave == 2 and not remediation_notes:
            draft_translation = ""

        prompt = _build_prompt(
            template_name,
            source_chunk=chunk_text,
            draft_translation=draft_translation or "",
            glossary=glossary or "(none provided)",
            style=style or "(none provided)",
            entities=entities or "(none provided)",
            previous_context=previous_context or "(none)",
            next_context=next_context or "(none)",
            remediation_notes=remediation_notes or "",
        )

        # ── Delegate to subagent ────────────────────────────────────────
        result = delegate_task(
            context={
                "chunk_id": chunk_id,
                "wave": wave,
                "backend": "hermes_delegate",
            },
            goal=prompt,
            role="leaf",
        )

        # ── Sanitize output ─────────────────────────────────────────────
        cleaned_text, sanitize_warnings = sanitize_subagent_output(
            result, chunk_id
        )

        return BackendResult(
            text=cleaned_text,
            backend_name="hermes_delegate",
            model="subagent",
            warnings=sanitize_warnings,
        )
