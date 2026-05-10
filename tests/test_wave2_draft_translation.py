"""Tests for wave2 draft_translation propagation."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from translator.orchestration.parallel_translator import ParallelTranslator
from translator.backends.base import BackendResult
from translator.backends.hermes_delegate import HermesDelegateBackend


# ── Fake backend that captures draft_translation ─────────────────────────

class CaptureDraftBackend:
    """Fake backend that records the draft_translation it receives."""

    name = "capture"
    received_draft = None

    def healthcheck(self):
        return True

    def translate_chunk(
        self,
        chunk_text,
        chunk_id,
        wave,
        *,
        glossary=None,
        style=None,
        entities=None,
        previous_context=None,
        next_context=None,
        draft_translation=None,
    ):
        self.__class__.received_draft = draft_translation
        return BackendResult(
            text=f"refined {chunk_id}",
            backend_name=self.name,
            model="test",
        )

    def translate(self, prompt, *, metadata=None):
        return BackendResult(text=prompt, backend_name=self.name, model="test")


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def project_dir():
    """Create a project with wave1 already completed for one chunk."""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "translations" / "test_draft_propagation"
        pdir.mkdir(parents=True)

        # Manifest
        (pdir / "chunks").mkdir(parents=True)
        manifest = {
            "project_slug": "test_draft",
            "total_chunks": 1,
            "chunks": [
                {
                    "id": "chunk_001",
                    "word_count": 50,
                    "char_start": 0,
                    "char_end": 300,
                    "source_hash": "abc",
                    "has_previous_context": False,
                    "has_next_context": False,
                    "wave1_status": "completed",
                    "wave2_status": "pending",
                }
            ],
        }
        with open(pdir / "chunks" / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Source chunk
        (pdir / "chunks" / "source").mkdir()
        source = "---\nchunk_id: chunk_001\n---\n\nOriginal English source text."
        with open(pdir / "chunks" / "source" / "chunk_001.md", "w") as f:
            f.write(source)

        # Wave1 output (draft translation)
        (pdir / "chunks" / "translated").mkdir()
        (pdir / "chunks" / "translated" / "wave1").mkdir()
        wave1 = "---\nchunk_id: chunk_001\nwave: 1\nbackend: mock\n---\n\nЧерновой перевод текста"
        with open(pdir / "chunks" / "translated" / "wave1" / "chunk_001.md", "w") as f:
            f.write(wave1)

        # State
        (pdir / "state").mkdir()
        stage_status = {
            "stages": {
                "translation_wave2": {"status": "in_progress", "translated": 0, "failed": 0, "total": 1},
            }
        }
        with open(pdir / "state" / "stage_status.json", "w") as f:
            json.dump(stage_status, f, indent=2)

        yield pdir


# ── Tests ────────────────────────────────────────────────────────────────

class TestWave2DraftTranslation:
    """ParallelTranslator must pass wave1 output as draft_translation to backend."""

    def test_parallel_translator_passes_draft(self, project_dir, monkeypatch):
        """translate_wave(wave=2) reads wave1 file and passes it as draft_translation."""
        capture_backend = CaptureDraftBackend()

        monkeypatch.setattr(
            "translator.orchestration.parallel_translator.get_backend",
            lambda name: capture_backend,
        )

        # Clear captured state
        CaptureDraftBackend.received_draft = None

        translator = ParallelTranslator(project_dir)
        results = translator.translate_wave(wave=2, backend_name="capture")

        assert len(results) == 1
        assert results[0].success is True
        assert CaptureDraftBackend.received_draft == "Черновой перевод текста"

    def test_no_wave1_file_passes_none(self, project_dir, monkeypatch):
        """If wave1 file doesn't exist, draft_translation is None."""
        # Remove wave1 file
        import os
        os.remove(project_dir / "chunks" / "translated" / "wave1" / "chunk_001.md")

        capture_backend = CaptureDraftBackend()
        monkeypatch.setattr(
            "translator.orchestration.parallel_translator.get_backend",
            lambda name: capture_backend,
        )

        CaptureDraftBackend.received_draft = None
        translator = ParallelTranslator(project_dir)
        translator.translate_wave(wave=2, backend_name="capture")

        assert CaptureDraftBackend.received_draft is None

    def test_hermes_delegate_fail_fast_without_draft(self, monkeypatch):
        """HermesDelegateBackend raises RuntimeError when wave2 called without draft."""
        from translator.backends import hermes_delegate as hd
        monkeypatch.setattr(hd, "is_hermes_runtime_available", lambda: True)

        backend = HermesDelegateBackend()
        with pytest.raises(RuntimeError) as exc:
            backend.translate_chunk("text", "c1", wave=2)
        msg = str(exc.value)
        assert "draft_translation" in msg
        assert "c1" in msg

    def test_hermes_delegate_prompt_contains_draft(self, monkeypatch):
        """draft_translation text appears in the subagent prompt."""
        from translator.backends import hermes_delegate as hd
        import builtins

        monkeypatch.setattr(hd, "is_hermes_runtime_available", lambda: True)

        prompt_texts = []

        def fake_delegate(*args, **kwargs):
            prompt_texts.append(kwargs.get("goal", ""))
            return "refined text"

        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == "hermes_tools":
                class FakeHT:
                    delegate_task = staticmethod(fake_delegate)
                return FakeHT
            return original_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)

        backend = HermesDelegateBackend()
        backend.translate_chunk(
            "source text",
            "c1",
            wave=2,
            draft_translation="Черновой перевод",
        )

        assert len(prompt_texts) == 1
        assert "Черновой перевод" in prompt_texts[0]
        assert "source text" in prompt_texts[0]
