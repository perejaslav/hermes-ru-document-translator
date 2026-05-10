"""Tests for backend healthcheck gating and stale metadata cleanup."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from translator.orchestration.parallel_translator import ParallelTranslator, ChunkResult
from translator.backends.base import BackendResult, TranslationBackend


# ── Fake backends for healthcheck tests ───────────────────────────────────

class DeadBackend(TranslationBackend):
    """Backend whose healthcheck returns False."""
    name = "dead"

    def healthcheck(self) -> bool:
        return False

    def translate(self, prompt, *, metadata=None):
        raise AssertionError("translate() should not be called")

    def translate_chunk(self, chunk_text, chunk_id, wave, **kwargs):
        raise AssertionError("translate_chunk() should not be called")


class AliveBackend(TranslationBackend):
    """Backend whose healthcheck returns True."""
    name = "alive"

    def healthcheck(self) -> bool:
        return True

    def translate(self, prompt, *, metadata=None):
        return BackendResult(text="ok", backend_name="alive")

    def translate_chunk(self, chunk_text, chunk_id, wave, **kwargs):
        return BackendResult(text=f"translated {chunk_id}", backend_name="alive", model="test-v1")


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def project_dir():
    """Create a minimal project with one pending chunk and a source file."""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "translations" / "test_healthcheck"
        pdir.mkdir(parents=True)

        # Manifest
        (pdir / "chunks").mkdir(parents=True)
        manifest = {
            "project_slug": "test_healthcheck",
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
                    "wave1_status": "pending",
                }
            ],
        }
        with open(pdir / "chunks" / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Source chunk file
        (pdir / "chunks" / "source").mkdir()
        content = "---\nchunk_id: chunk_001\n---\n\nAncient Elamite text to translate."
        with open(pdir / "chunks" / "source" / "chunk_001.md", "w") as f:
            f.write(content)

        # State
        (pdir / "state").mkdir()
        stage_status = {
            "stages": {
                "translation_wave1": {"status": "in_progress", "translated": 0, "failed": 0, "total": 1},
            }
        }
        with open(pdir / "state" / "stage_status.json", "w") as f:
            json.dump(stage_status, f, indent=2)

        yield pdir


@pytest.fixture
def project_dir_with_stale_meta():
    """Create a project where chunk has stale wave2 metadata."""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "translations" / "test_stale_meta"
        pdir.mkdir(parents=True)

        (pdir / "chunks").mkdir(parents=True)
        manifest = {
            "project_slug": "test_stale_meta",
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
                    "wave2_status": "completed",
                    "wave2_backend": "minimax_api",
                    "wave2_model": "minimax-m2.5",
                    "wave2_translated_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
        with open(pdir / "chunks" / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        (pdir / "state").mkdir()
        stage_status = {
            "stages": {
                "translation_wave2": {"status": "in_progress", "translated": 1, "failed": 0, "total": 1},
            }
        }
        with open(pdir / "state" / "stage_status.json", "w") as f:
            json.dump(stage_status, f, indent=2)

        yield pdir


# ── Tests ────────────────────────────────────────────────────────────────

class TestHealthcheckGate:
    """Backend healthcheck must fail fast before any chunk work."""

    def test_dead_backend_raises_runtime_error(self, project_dir, monkeypatch):
        """translate_wave with dead backend raises RuntimeError."""
        monkeypatch.setattr(
            "translator.orchestration.parallel_translator.get_backend",
            lambda name: DeadBackend(),
        )

        translator = ParallelTranslator(project_dir)
        with pytest.raises(RuntimeError) as exc:
            translator.translate_wave(wave=1, backend_name="dead")

        assert "failed healthcheck" in str(exc.value).lower()

    def test_dead_backend_does_not_call_translate_chunk(self, project_dir, monkeypatch):
        """No chunk translation is attempted when healthcheck fails."""
        called = []

        class TrackingDeadBackend(TranslationBackend):
            name = "dead"
            def healthcheck(self) -> bool:
                return False
            def translate_chunk(self, *args, **kwargs):
                called.append(True)
                raise AssertionError("should not be reached")
            def translate(self, *args, **kwargs):
                called.append(True)
                raise AssertionError("should not be reached")

        monkeypatch.setattr(
            "translator.orchestration.parallel_translator.get_backend",
            lambda name: TrackingDeadBackend(),
        )

        translator = ParallelTranslator(project_dir)
        with pytest.raises(RuntimeError):
            translator.translate_wave(wave=1, backend_name="dead")

        assert len(called) == 0, "translate_chunk was called despite dead healthcheck"

    def test_alive_backend_proceeds(self, project_dir, monkeypatch):
        """Alive backend healthcheck passes and translation proceeds."""
        monkeypatch.setattr(
            "translator.orchestration.parallel_translator.get_backend",
            lambda name: AliveBackend(),
        )

        translator = ParallelTranslator(project_dir)
        results = translator.translate_wave(wave=1, backend_name="alive")

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result.backend_name == "alive"


class TestStaleMetadataCleanup:
    """Failed chunks must clear previous wave*_backend, wave*_model, wave*_translated_at."""

    def test_failed_chunk_clears_stale_metadata(self, project_dir_with_stale_meta):
        """Stale wave2_* metadata is removed when chunk fails."""
        pdir = project_dir_with_stale_meta
        translator = ParallelTranslator(pdir)

        # Simulate a failed persist for wave2
        results = [
            ChunkResult(
                chunk_id="chunk_001",
                wave=2,
                success=False,
                error="API timeout",
            )
        ]
        translator._persist_results(results, wave=2)

        with open(pdir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        chunk = manifest["chunks"][0]
        assert chunk["wave2_status"] == "failed"
        assert chunk["wave2_error"] == "API timeout"
        assert "wave2_backend" not in chunk
        assert "wave2_model" not in chunk
        assert "wave2_translated_at" not in chunk

    def test_success_does_not_clear_stale_on_fail_branch(self, project_dir_with_stale_meta):
        """A successful persist writes fresh metadata (should not interfere)."""
        pdir = project_dir_with_stale_meta
        translator = ParallelTranslator(pdir)

        results = [
            ChunkResult(
                chunk_id="chunk_001",
                wave=2,
                success=True,
                result=BackendResult(
                    text="new translation",
                    backend_name="sequential",
                    model="mock-v1",
                ),
            )
        ]
        translator._persist_results(results, wave=2)

        with open(pdir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        chunk = manifest["chunks"][0]
        assert chunk["wave2_status"] == "completed"
        assert chunk["wave2_backend"] == "sequential"
        assert chunk["wave2_model"] == "mock-v1"
        assert "wave2_translated_at" in chunk
        assert "wave2_error" not in chunk
