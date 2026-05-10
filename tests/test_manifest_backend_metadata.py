"""Tests for manifest backend metadata persistence."""

import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from translator.orchestration.parallel_translator import ParallelTranslator
from translator.backends.base import BackendResult


@pytest.fixture
def project_dir():
    """Create a minimal project with a manifest that has no backend metadata."""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "translations" / "test_backend_meta"
        pdir.mkdir(parents=True)

        # Create minimal manifest
        (pdir / "chunks").mkdir(parents=True)
        manifest = {
            "project_slug": "test_backend_meta",
            "total_chunks": 2,
            "chunks": [
                {
                    "id": "chunk_001",
                    "word_count": 100,
                    "char_start": 0,
                    "char_end": 500,
                    "source_hash": "abc",
                    "has_previous_context": False,
                    "has_next_context": True,
                    "wave1_status": "pending",
                    "wave2_status": "pending",
                },
                {
                    "id": "chunk_002",
                    "word_count": 80,
                    "char_start": 501,
                    "char_end": 1000,
                    "source_hash": "def",
                    "has_previous_context": True,
                    "has_next_context": False,
                    "wave1_status": "pending",
                    "wave2_status": "pending",
                },
            ],
        }
        with open(pdir / "chunks" / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create minimal stage_status.json
        (pdir / "state").mkdir()
        stage_status = {
            "stages": {
                "translation_wave1": {"status": "in_progress", "translated": 0, "failed": 0, "total": 2},
                "translation_wave2": {"status": "pending"},
            }
        }
        with open(pdir / "state" / "stage_status.json", "w") as f:
            json.dump(stage_status, f, indent=2)

        yield pdir


def make_chunk_result(chunk_id, wave, success=True, backend="minimax_api", model="minimax-m2.5", error=None):
    """Helper to create a ChunkResult."""
    from translator.orchestration.parallel_translator import ChunkResult
    result = None
    if success:
        result = BackendResult(
            text=f"translated {chunk_id}",
            backend_name=backend,
            model=model,
        )
    return ChunkResult(
        chunk_id=chunk_id,
        wave=wave,
        success=success,
        result=result,
        error=error,
    )


class TestPersistBackendMetadata:
    """Tests for _persist_results metadata recording."""

    def test_success_stores_chunk_backend_and_model(self, project_dir):
        """Successfully completed chunks get wave*_backend, wave*_model, wave*_translated_at."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=2, backend="minimax_api", model="minimax-m2.5"),
            make_chunk_result("chunk_002", wave=2, backend="minimax_api", model="minimax-m2.5"),
        ]
        translator._persist_results(results, wave=2)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        for chunk in manifest["chunks"]:
            assert chunk["wave2_status"] == "completed"
            assert chunk["wave2_backend"] == "minimax_api"
            assert chunk["wave2_model"] == "minimax-m2.5"
            assert "wave2_translated_at" in chunk
            assert chunk["wave2_translated_at"].endswith("Z")
            # Should NOT have wave2_error
            assert "wave2_error" not in chunk

    def test_failed_chunk_stores_error(self, project_dir):
        """Failed chunks get wave*_error and status=failed, no backend metadata."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=1, success=False, error="API timeout"),
            make_chunk_result("chunk_002", wave=1, success=False, error="Invalid response"),
        ]
        translator._persist_results(results, wave=1)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        for chunk in manifest["chunks"]:
            assert chunk["wave1_status"] == "failed"
            assert chunk["wave1_error"] in ("API timeout", "Invalid response")
            assert "wave1_backend" not in chunk
            assert "wave1_model" not in chunk

    def test_mixed_success_failure(self, project_dir):
        """Mixed results: successful chunks get metadata, failed ones don't."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=1, backend="mock", model=None),
            make_chunk_result("chunk_002", wave=1, success=False, error="timeout"),
        ]
        translator._persist_results(results, wave=1)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        # Successful chunk
        c1 = [c for c in manifest["chunks"] if c["id"] == "chunk_001"][0]
        assert c1["wave1_status"] == "completed"
        assert c1["wave1_backend"] == "mock"
        assert "wave1_model" not in c1  # model was None → skip
        assert "wave1_translated_at" in c1

        # Failed chunk
        c2 = [c for c in manifest["chunks"] if c["id"] == "chunk_002"][0]
        assert c2["wave1_status"] == "failed"
        assert c2["wave1_error"] == "timeout"

    def test_project_level_metadata(self, project_dir):
        """manifest.translation.wave*_backend and wave*_model are set."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=2, backend="sequential", model="mock-v1"),
            make_chunk_result("chunk_002", wave=2, backend="sequential", model="mock-v1"),
        ]
        translator._persist_results(results, wave=2)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        translation = manifest.get("translation", {})
        assert translation["wave2_backend"] == "sequential"
        assert translation["wave2_model"] == "mock-v1"
        assert "wave2_updated_at" in translation
        assert translation["wave2_updated_at"].endswith("Z")

    def test_project_level_not_written_on_all_fail(self, project_dir):
        """No project-level translation block when all chunks fail."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=1, success=False, error="err1"),
            make_chunk_result("chunk_002", wave=1, success=False, error="err2"),
        ]
        translator._persist_results(results, wave=1)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        assert "translation" not in manifest

    def test_partial_failure_still_writes_project_meta(self, project_dir):
        """If at least one chunk succeeds, project-level metadata is written."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=1, backend="minimax_api", model="m2.5"),
            make_chunk_result("chunk_002", wave=1, success=False, error="err"),
        ]
        translator._persist_results(results, wave=1)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        translation = manifest.get("translation", {})
        assert translation["wave1_backend"] == "minimax_api"
        assert translation["wave1_model"] == "m2.5"

    def test_model_none_not_written_to_chunk(self, project_dir):
        """When model is None, wave*_model key is not added to chunk."""
        translator = ParallelTranslator(project_dir)
        results = [
            make_chunk_result("chunk_001", wave=1, backend="mock", model=None),
        ]
        translator._persist_results(results, wave=1)

        with open(project_dir / "chunks" / "manifest.json") as f:
            manifest = json.load(f)

        c1 = [c for c in manifest["chunks"] if c["id"] == "chunk_001"][0]
        assert c1["wave1_status"] == "completed"
        assert c1["wave1_backend"] == "mock"
        assert "wave1_model" not in c1  # None → skip
        # But project level should store None (JSON null)
        assert manifest["translation"]["wave1_model"] is None
