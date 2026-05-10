"""Hermes delegate backend — parallel subagent translation via delegate_task."""

import json
import re
import threading
from pathlib import Path
from typing import Optional

from .base import TranslationBackend, BackendResult
from .sanitizer import sanitize_subagent_output


class HermesDelegateBackend(TranslationBackend):
    """Backend using Hermes Agent's delegate_task for parallel subagent translation."""

    name = "hermes_delegate"

    def __init__(
        self,
        max_workers: int = 3,
        retry_count: int = 1,
        preserve_markdown: bool = True,
        preserve_code_blocks: bool = True,
    ):
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.preserve_markdown = preserve_markdown
        self.preserve_code_blocks = preserve_code_blocks
        self._semaphore = threading.Semaphore(max_workers)

    def healthcheck(self) -> bool:
        """Check if delegate_task is available."""
        try:
            from hermes_tools import delegate_task
            return True
        except ImportError:
            return False

    def translate(self, prompt: str, *, metadata: dict | None = None) -> BackendResult:
        """Not used directly — use translate_chunk()."""
        return self.translate_chunk(
            chunk_text=prompt,
            chunk_id=(metadata or {}).get("chunk_id", "unknown"),
            wave=(metadata or {}).get("wave", 1),
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
    ) -> BackendResult:
        """Translate a single chunk via delegate_task subagent.

        This method is designed to be called from a thread pool for parallelism.
        """
        from hermes_tools import delegate_task

        prompt = self._build_prompt(
            chunk_text=chunk_text,
            chunk_id=chunk_id,
            wave=wave,
            glossary=glossary,
            style=style,
            entities=entities,
            previous_context=previous_context,
            next_context=next_context,
        )

        # Delegate to subagent
        result = delegate_task(
            context={
                "chunk_id": chunk_id,
                "wave": wave,
                "project_dir": str(Path.cwd()),
            },
            goal=prompt,
            role="leaf",
        )

        # Sanitize output
        cleaned_text, sanitize_warnings = sanitize_subagent_output(result, chunk_id)

        return BackendResult(
            text=cleaned_text,
            backend_name=self.name,
            model="hermes-subagent",
            warnings=sanitize_warnings,
        )

    def _build_prompt(
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
    ) -> str:
        """Build translation prompt for subagent."""
        if wave == 1:
            instruction = self._wave1_instruction()
        else:
            instruction = self._wave2_instruction()

        parts = [
            f"# Translation Task — {chunk_id} (Wave {wave})",
            "",
            "## Source Chunk",
            chunk_text,
            "",
        ]

        if previous_context:
            parts.extend(["## Previous Context (last 2 sentences)", previous_context, ""])
        if next_context:
            parts.extend(["## Next Context (first 2 sentences)", next_context, ""])
        if glossary:
            parts.extend(["## Glossary", glossary, ""])
        if style:
            parts.extend(["## Style Guide", style, ""])
        if entities:
            parts.extend(["## Entity Register", entities, ""])

        parts.extend([
            "## Your Task",
            instruction,
            "",
            f"Output ONLY the Russian translation of the Source Chunk. Do not include explanations, notes, or wrappers.",
            f"Chunk ID: {chunk_id}",
        ])

        return "\n".join(parts)

    def _wave1_instruction(self) -> str:
        return """Translate the source chunk into natural Russian.
Preserve Markdown structure: headings, lists, tables, code blocks, links, references.
Follow the glossary, style guide and entity register.
Do not translate code blocks unless they contain natural language comments that clearly require translation.
Flag uncertain terms with [?] only when necessary.
Do NOT include previous/next context in the output translation."""

    def _wave2_instruction(self) -> str:
        return """Refine the draft Russian translation.
Compare it against the source chunk.
Fix: terminology inconsistencies, omissions, awkward Russian, broken formatting, inconsistent entity rendering.
Do not re-translate from scratch unless the draft is completely unusable.
Preserve Markdown structure.
Do NOT include previous/next context in the final output."""