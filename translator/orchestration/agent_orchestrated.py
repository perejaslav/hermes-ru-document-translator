"""Hermes Agent runtime orchestration — agent-orchestrated translation mode.

NOT a CLI backend. This module is designed to run exclusively inside
Hermes Agent runtime (via execute_code, embedded orchestration, or
Hermes-native workflow).

Architecture::

    Hermes Agent (orchestration runtime)
        │
        ├── reads/writes project files (chunks, manifest, state)
        ├── calls delegate_task() for each chunk/wave
        │
        └── Pipeline (deterministic infrastructure):
            prepare → translate → qa → merge → export → report

Design decisions:
- delegate_task is NOT a Python-importable library function.
  It is a Hermes Agent runtime capability.
- This module cannot be invoked from a standalone Python process.
- All subagent calls go through delegate_task — no local model inference.
- All outputs are sanitized (assert reasoning blocks, CJK contamination).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Runtime detection
# ═══════════════════════════════════════════════════════════════════════════

def require_delegate_task():
    """Verify ``delegate_task`` is available and return a callable reference.

    Returns:
        The ``delegate_task`` callable from Hermes runtime.

    Raises:
        RuntimeError: If ``delegate_task`` is not importable.
    """
    try:
        from hermes_tools import delegate_task  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "Hermes runtime subagent backend requires Hermes Agent runtime.\n\n"
            "delegate_task is only available inside Hermes Agent via execute_code()\n"
            "or during agent tool execution. It is NOT a standard Python library.\n\n"
            "Run this code from within Hermes Agent, not from a standalone\n"
            "Python process (terminal, python script, etc.)."
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"delegate_task import failed unexpectedly: {exc}\n"
            "The Hermes runtime environment may be corrupted or incomplete."
        ) from exc

    # Verify the imported object is actually callable
    if not callable(delegate_task):
        raise RuntimeError(
            f"delegate_task imported but is not callable (type: {type(delegate_task)}). "
            "Hermes runtime environment may be corrupted."
        )

    return delegate_task


def is_runtime_available() -> bool:
    """Check if delegate_task is available without raising.

    Returns:
        True if and only if Hermes Agent runtime is accessible.
    """
    try:
        require_delegate_task()
        return True
    except RuntimeError:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Timestamp helper
# ═══════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ═══════════════════════════════════════════════════════════════════════════
# Project path helpers
# ═══════════════════════════════════════════════════════════════════════════

_CHUNK_SOURCE_DIR = "chunks/source"
_CHUNK_CONTEXT_DIR = "chunks/context"
_CHUNK_WAVE1_DIR = "chunks/translated/wave1"
_CHUNK_WAVE2_DIR = "chunks/translated/wave2"
_FOUNDATION_DIR = "foundation"
_QA_DIR = "qa"
_MANIFEST_PATH = "chunks/manifest.json"


def _resolve(project_dir: str | Path) -> Path:
    return Path(project_dir).expanduser().resolve()


def _read_text(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════
# Foundation loading
# ═══════════════════════════════════════════════════════════════════════════

def _load_foundation(project_dir: Path) -> dict[str, str]:
    """Load glossary, style, and entity files from project foundation.

    Returns:
        Dict with keys ``glossary``, ``style``, ``entities``.
        Missing files yield empty strings.
    """
    out: dict[str, str] = {}
    for name in ("glossary", "style", "entities"):
        path = project_dir / _FOUNDATION_DIR / f"{name}.md"
        if path.exists():
            out[name] = path.read_text(encoding="utf-8")
        else:
            out[name] = ""
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Prompt building
# ═══════════════════════════════════════════════════════════════════════════

_PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "translator" / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from ``translator/prompts/``.

    Args:
        name: Filename stem (e.g. ``wave1_translation``).

    Returns:
        Prompt template string.

    Raises:
        FileNotFoundError: If the prompt file is missing.
    """
    path = _PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {path}\n"
            "Ensure translator/prompts/ directory is intact."
        )
    return path.read_text(encoding="utf-8")


def _build_prompt(template_name: str, **kwargs: Any) -> str:
    """Load and render a prompt template with context variables.

    Renders ``{{variable}}`` placeholders from kwargs.
    Unused placeholders are left as-is (warning-level concern).
    """
    template = _load_prompt(template_name)
    for key, value in kwargs.items():
        if value is not None:
            template = template.replace("{{" + key + "}}", str(value))
    return template


# ═══════════════════════════════════════════════════════════════════════════
# Sanitizer integration
# ═══════════════════════════════════════════════════════════════════════════

try:
    from translator.backends.sanitizer import sanitize_subagent_output
except ImportError:
    # Minimal fallback if running in non-standard context (tests)
    def sanitize_subagent_output(output: str, chunk_id: str = "?") -> tuple[str, list[str]]:  # type: ignore[misc]
        return output.strip(), []


# ═══════════════════════════════════════════════════════════════════════════
# Frontmatter stripping
# ═══════════════════════════════════════════════════════════════════════════

_YAML_FM_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL | re.MULTILINE)


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter delimited by ``---`` lines.

    Handles both normal and empty (```---\\n---``) frontmatter.
    """
    # Try with content first
    result = _YAML_FM_RE.sub("", text, count=1)
    if result != text:
        return result.strip()
    # Try empty frontmatter: ---\n--- (no content between delimiters)
    empty_fm = re.compile(r"^---\s*\n---\s*\n?", re.MULTILINE)
    result = empty_fm.sub("", text, count=1)
    return result.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════════════════

class AgentOrchestratedTranslator:
    """Translate a prepared project via Hermes Agent subagent delegation.

    This class must be instantiated and used ONLY inside Hermes Agent runtime
    (i.e., where ``delegate_task`` is available).
    """

    def __init__(self, project_dir: str | Path):
        self.project_dir = _resolve(project_dir)
        self._delegate = require_delegate_task()

        if not self.project_dir.exists():
            raise FileNotFoundError(
                f"Project directory not found: {self.project_dir}\n"
                "Run 'hermes-translator prepare <file>' first."
            )

    # ── Public API ─────────────────────────────────────────────────────

    def translate_project(
        self,
        *,
        waves: tuple[int, ...] = (1, 2),
    ) -> dict[str, Any]:
        """Translate all pending/failed chunks for the specified waves.

        Args:
            waves: Which waves to run (default: wave 1 then wave 2).

        Returns:
            Dict with ``wave1``, ``wave2`` keys containing per-chunk results.
        """
        results: dict[str, Any] = {}
        for wave in waves:
            results[f"wave{wave}"] = self.translate_wave(wave)
        return results

    def translate_wave(self, wave: int) -> dict[str, Any]:
        """Translate all pending/failed chunks for a single wave.

        Args:
            wave: 1 (initial translation) or 2 (refinement).

        Returns:
            Dict with ``chunks`` (per-chunk results) and ``total`` / ``success``.

        Raises:
            ValueError: If wave is not 1 or 2.
        """
        if wave not in (1, 2):
            raise ValueError(f"Invalid wave: {wave}. Must be 1 or 2.")

        manifest = self._load_manifest()
        chunks = manifest.get("chunks", [])
        foundation = _load_foundation(self.project_dir)

        results: dict[str, Any] = {"chunks": {}, "total": 0, "success": 0}
        status_key = f"wave{wave}_status"

        for chunk in chunks:
            chunk_id = chunk["id"]
            # Only process pending/failed chunks
            current_status = chunk.get(status_key, "pending")
            if current_status not in ("pending", "failed"):
                continue

            results["total"] += 1
            try:
                result = self.translate_chunk(chunk_id, wave=wave)
                results["chunks"][chunk_id] = {
                    "status": "completed",
                    "warnings": result.get("warnings", []),
                }
                results["success"] += 1
                self._mark_chunk_completed(chunk, wave)
            except Exception as exc:
                results["chunks"][chunk_id] = {
                    "status": "failed",
                    "error": str(exc),
                }
                self._mark_chunk_failed(chunk, wave, str(exc))

        if results["success"] > 0:
            self._mark_project_wave_metadata(manifest, wave)
        self._save_manifest(manifest)
        return results

    def translate_chunk(
        self,
        chunk_id: str,
        wave: int,
        *,
        remediation_notes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Translate a single chunk via delegate_task.

        Args:
            chunk_id: e.g. ``chunk_001``.
            wave: 1 (translation) or 2 (refinement/repair).
            remediation_notes: For wave 2 repair — specific issues to fix.

        Returns:
            Dict with ``chunk_id``, ``wave``, ``translation``, ``warnings``.

        Raises:
            ValueError: Invalid wave.
            RuntimeError: If wave 2 has no wave 1 draft.
            RuntimeError: Subagent failure or sanitizer issues.
        """
        if wave not in (1, 2):
            raise ValueError(f"Invalid wave: {wave}")

        # ── Load source ────────────────────────────────────────────────
        source_path = self.project_dir / _CHUNK_SOURCE_DIR / f"{chunk_id}.md"
        if not source_path.exists():
            raise FileNotFoundError(f"Source chunk not found: {source_path}")
        source_text = _read_text(source_path)
        source_body = _strip_frontmatter(source_text)

        # ── Load context ───────────────────────────────────────────────
        context_path = self.project_dir / _CHUNK_CONTEXT_DIR / f"{chunk_id}.context.md"
        context_text = _read_text(context_path) if context_path.exists() else ""

        # Parse context for previous/next
        previous_context = ""
        next_context = ""
        for line in context_text.splitlines():
            if line.startswith("## Previous"):
                continue
            if line.startswith("## Next"):
                continue
            if line.startswith("None."):
                continue

        # Simple context extraction
        if "Previous" in context_text and "Next" in context_text:
            parts = context_text.split("## Next")
            prev_part = parts[0]
            next_part = parts[1] if len(parts) > 1 else ""
            previous_context = _extract_context_after_header(prev_part, "Previous")
            next_context = _extract_context_after_header(next_part, "Next")

        # ── Load foundation ────────────────────────────────────────────
        foundation = _load_foundation(self.project_dir)

        # ── Load draft for wave 2 ──────────────────────────────────────
        draft_translation: str | None = None
        if wave == 2:
            if remediation_notes:
                # Repair mode: use wave2 (current) as draft
                draft_path = self.project_dir / _CHUNK_WAVE2_DIR / f"{chunk_id}.md"
            else:
                # Refinement mode: use wave1 as draft
                draft_path = self.project_dir / _CHUNK_WAVE1_DIR / f"{chunk_id}.md"

            if draft_path.exists():
                draft_text = _read_text(draft_path)
                draft_translation = _strip_frontmatter(draft_text)
            elif not remediation_notes:
                raise RuntimeError(
                    f"Wave 2 refinement requires wave 1 draft for {chunk_id}, "
                    f"but no draft found at {draft_path}. "
                    "Run wave 1 before wave 2."
                )

        # ── Build and validate prompt ──────────────────────────────────
        if remediation_notes:
            prompt = _build_prompt(
                "repair",
                source_chunk=source_body,
                draft_translation=draft_translation or "",
                remediation_notes="\n".join(f"- {n}" for n in remediation_notes),
            )
        elif wave == 1:
            prompt = _build_prompt(
                "wave1_translation",
                source_chunk=source_body,
                glossary=foundation.get("glossary", ""),
                style=foundation.get("style", ""),
                entities=foundation.get("entities", ""),
                previous_context=previous_context,
                next_context=next_context,
            )
        else:  # wave == 2, refinement
            if not draft_translation:
                raise RuntimeError(
                    f"Wave 2 refinement requires draft_translation for {chunk_id}"
                )
            prompt = _build_prompt(
                "wave2_refinement",
                source_chunk=source_body,
                draft_translation=draft_translation,
                glossary=foundation.get("glossary", ""),
                style=foundation.get("style", ""),
                entities=foundation.get("entities", ""),
                previous_context=previous_context,
                next_context=next_context,
            )

        # ── Call delegate_task ─────────────────────────────────────────
        goal_text = prompt  # Full prompt is the goal
        context = (
            f"Hermes Agent subagent translation task.\n"
            f"Project: {self.project_dir.name}\n"
            f"Chunk: {chunk_id}, Wave: {wave}\n"
            f"Translate/refine as instructed. Output ONLY the translation."
        )

        try:
            delegate_result = self._delegate(
                goal=goal_text,
                context=context,
            )
        except Exception as exc:
            raise RuntimeError(
                f"delegate_task failed for {chunk_id} wave {wave}: {exc}"
            ) from exc

        # ── Extract translation from result ────────────────────────────
        raw_output = self._extract_delegate_output(delegate_result)

        # ── Sanitize ───────────────────────────────────────────────────
        cleaned, warnings = sanitize_subagent_output(raw_output, chunk_id=chunk_id)

        # ── Write result ───────────────────────────────────────────────
        wave_dir = _CHUNK_WAVE2_DIR if wave == 2 else _CHUNK_WAVE1_DIR
        out_path = self.project_dir / wave_dir / f"{chunk_id}.md"
        frontmatter = (
            f"---\nchunk_id: {chunk_id}\n"
            f"wave: wave{wave}\n"
            f"backend: agent_orchestrated\n"
            f"model: subagent\n---\n\n"
        )
        _write_text(out_path, frontmatter + cleaned)

        return {
            "chunk_id": chunk_id,
            "wave": wave,
            "translation": cleaned,
            "warnings": warnings,
        }

    def repair_project(self) -> dict[str, Any]:
        """Repair chunks flagged by QA.

        Reads ``qa/remediation.json`` and re-translates affected chunks.

        - Chunks with ``gate6:`` notes (completeness/reference failures) use
          full retranslation from source via ``completeness_retranslation``
          prompt — NOT the repair prompt with the old wave2 draft.
        - Other chunks use the standard repair prompt.

        Returns:
            Dict with ``chunks`` (per-chunk results) and ``total`` / ``success``.
        """
        remediation_path = self.project_dir / _QA_DIR / "remediation.json"
        if not remediation_path.exists():
            return {"chunks": {}, "total": 0, "success": 0, "message": "No remediation needed"}

        remediation = _read_json(remediation_path)
        affected = remediation.get("chunks", {})

        # Load manifest to update chunk metadata
        manifest = self._load_manifest()
        chunks_map = {c["id"]: c for c in manifest.get("chunks", [])}

        results: dict[str, Any] = {"chunks": {}, "total": 0, "success": 0}

        for chunk_id, notes in affected.items():
            if not notes:
                continue
            results["total"] += 1
            try:
                # Gate6 notes = completeness/reference failure → full retranslation
                if any(note.startswith("gate6:") for note in notes):
                    result = self._retranslate_chunk_full(chunk_id, notes)
                else:
                    result = self.translate_chunk(
                        chunk_id,
                        wave=2,
                        remediation_notes=notes,
                    )
                results["chunks"][chunk_id] = {
                    "status": "completed",
                    "warnings": result.get("warnings", []),
                }
                results["success"] += 1
                # Update manifest chunk metadata
                chunk = chunks_map.get(chunk_id)
                if chunk is not None:
                    self._mark_chunk_completed(chunk, 2)
            except Exception as exc:
                results["chunks"][chunk_id] = {
                    "status": "failed",
                    "error": str(exc),
                }
                chunk = chunks_map.get(chunk_id)
                if chunk is not None:
                    self._mark_chunk_failed(chunk, 2, str(exc))

        if results["success"] > 0:
            self._mark_project_wave_metadata(manifest, 2)
        self._save_manifest(manifest)
        return results

    def _retranslate_chunk_full(self, chunk_id: str, notes: list[str]) -> dict[str, Any]:
        """Full retranslation from source for completeness gate failures.

        Uses ``completeness_retranslation`` prompt with strict citation and
        paragraph preservation rules. Does NOT use the existing wave2 draft.

        Args:
            chunk_id: e.g. ``chunk_001``.
            notes: Remediation notes to include as context.

        Returns:
            Dict with ``chunk_id``, ``wave``, ``translation``, ``warnings``.
        """
        # ── Load source only (no wave2 draft) ──────────────────────────
        source_path = self.project_dir / _CHUNK_SOURCE_DIR / f"{chunk_id}.md"
        if not source_path.exists():
            raise FileNotFoundError(f"Source chunk not found: {source_path}")
        source_text = _read_text(source_path)
        source_body = _strip_frontmatter(source_text)

        # ── Build completeness_retranslation prompt ────────────────────
        prompt = _build_prompt(
            "completeness_retranslation",
            source_chunk=source_body,
            remediation_notes="\n".join(f"- {n}" for n in notes),
        )

        # ── Call delegate_task ─────────────────────────────────────────
        goal_text = prompt
        context = (
            f"Hermes Agent subagent translation task.\n"
            f"Project: {self.project_dir.name}\n"
            f"Chunk: {chunk_id}, Wave: 2 (completeness retranslation)\n"
            f"Translate EVERY sentence and preserve EVERY citation from the source."
        )

        try:
            delegate_result = self._delegate(
                goal=goal_text,
                context=context,
            )
        except Exception as exc:
            raise RuntimeError(
                f"delegate_task failed for {chunk_id} completeness retranslation: {exc}"
            ) from exc

        # ── Extract translation from result ────────────────────────────
        raw_output = self._extract_delegate_output(delegate_result)

        # ── Sanitize ───────────────────────────────────────────────────
        cleaned, warnings = sanitize_subagent_output(raw_output, chunk_id=chunk_id)

        # ── Write to wave2 (overwrite) ─────────────────────────────────
        out_path = self.project_dir / _CHUNK_WAVE2_DIR / f"{chunk_id}.md"
        frontmatter = (
            f"---\nchunk_id: {chunk_id}\n"
            f"wave: wave2\n"
            f"backend: agent_orchestrated\n"
            f"model: subagent\n"
            f"note: completeness_retranslation\n---\n\n"
        )
        _write_text(out_path, frontmatter + cleaned)

        return {
            "chunk_id": chunk_id,
            "wave": 2,
            "translation": cleaned,
            "warnings": warnings,
        }

    # ── Internals ──────────────────────────────────────────────────────

    def _load_manifest(self) -> dict:
        path = self.project_dir / _MANIFEST_PATH
        if not path.exists():
            return {"chunks": [], "total_chunks": 0}
        return _read_json(path)

    def _save_manifest(self, manifest: dict):
        """Persist manifest to disk without injecting metadata — callers must update first."""
        path = self.project_dir / _MANIFEST_PATH
        _write_json(path, manifest)

    # ── Chunk-level metadata helpers ────────────────────────────────────

    def _mark_chunk_completed(self, chunk: dict, wave: int):
        """Update chunk metadata for successful translation."""
        status_key = f"wave{wave}_status"
        backend_key = f"wave{wave}_backend"
        model_key = f"wave{wave}_model"
        ts_key = f"wave{wave}_translated_at"
        error_key = f"wave{wave}_error"

        chunk[status_key] = "completed"
        chunk[backend_key] = "agent_orchestrated"
        chunk[model_key] = "subagent"
        chunk[ts_key] = _now_iso()
        chunk.pop(error_key, None)

    def _mark_chunk_failed(self, chunk: dict, wave: int, error: str):
        """Update chunk metadata for failed translation."""
        status_key = f"wave{wave}_status"
        backend_key = f"wave{wave}_backend"
        model_key = f"wave{wave}_model"
        ts_key = f"wave{wave}_translated_at"
        error_key = f"wave{wave}_error"

        chunk[status_key] = "failed"
        chunk[error_key] = error
        chunk.pop(backend_key, None)
        chunk.pop(model_key, None)
        chunk.pop(ts_key, None)

    # ── Project-level metadata helper ───────────────────────────────────

    def _mark_project_wave_metadata(self, manifest: dict, wave: int):
        """Record backend metadata at project level for a completed wave."""
        translation = manifest.setdefault("translation", {})
        translation[f"wave{wave}_backend"] = "agent_orchestrated"
        translation[f"wave{wave}_model"] = "subagent"
        translation[f"wave{wave}_updated_at"] = _now_iso()

    @staticmethod
    def _extract_delegate_output(delegate_result: Any) -> str:
        """Extract the translated text from a delegate_task result.

        Handles both dict and list return types.
        """
        # Case 1: dict result
        if isinstance(delegate_result, dict):
            # Direct summary field
            summary = delegate_result.get("summary")
            if summary and isinstance(summary, str):
                return summary

            # results array
            results = delegate_result.get("results")
            if isinstance(results, list) and len(results) > 0:
                first = results[0]
                if isinstance(first, dict):
                    s = first.get("summary")
                    if s and isinstance(s, str):
                        return s

        # Case 2: list of results
        if isinstance(delegate_result, list) and len(delegate_result) > 0:
            first = delegate_result[0]
            if isinstance(first, dict):
                s = first.get("summary")
                if s and isinstance(s, str):
                    return s

        # Fallback: stringify
        if isinstance(delegate_result, str):
            return delegate_result

        raise RuntimeError(
            f"Cannot extract translation from delegate_task result "
            f"(type: {type(delegate_result).__name__})"
        )


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract_context_after_header(text: str, header_name: str) -> str:
    """Extract context text after '## <name> context' header."""
    lines = text.splitlines()
    capture = False
    parts = []
    for line in lines:
        if line.strip().startswith("##") and header_name.lower() in line.lower():
            capture = True
            continue
        if capture:
            if line.strip().startswith("##"):
                break
            if line.strip() not in ("None.", "", "None"):
                parts.append(line)
    return " ".join(parts).strip()
