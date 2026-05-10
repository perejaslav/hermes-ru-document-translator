"""Tests for repair backend safety logic."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root so we can import from scripts.run_pipeline
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# Import the helper directly from run_pipeline
from run_pipeline import _infer_repair_backend  # noqa: E402


class TestInferRepairBackend:
    """Tests for _infer_repair_backend."""

    def test_returns_none_when_no_backend_metadata(self):
        """Should return None when manifest has no backend info."""
        manifest = {
            "project_slug": "test",
            "chunks": [
                {"id": "chunk_001", "wave1_status": "completed"},
                {"id": "chunk_002", "wave1_status": "completed"},
            ],
        }
        result = _infer_repair_backend(manifest, ["chunk_001"])
        assert result is None

    def test_returns_chunk_level_backend(self):
        """Should return backend from chunk metadata."""
        manifest = {
            "project_slug": "test",
            "chunks": [
                {"id": "chunk_001", "wave1_status": "completed", "wave2_backend": "minimax_api"},
                {"id": "chunk_002", "wave1_status": "completed"},
            ],
        }
        result = _infer_repair_backend(manifest, ["chunk_001"])
        assert result == "minimax_api"

    def test_returns_none_when_flagged_chunk_has_no_backend(self):
        """Should return None when only un-flagged chunks have backend."""
        manifest = {
            "project_slug": "test",
            "chunks": [
                {"id": "chunk_001", "wave1_status": "completed", "wave2_backend": "mock"},
                {"id": "chunk_002", "wave1_status": "completed"},
            ],
        }
        result = _infer_repair_backend(manifest, ["chunk_002"])
        assert result is None

    def test_returns_manifest_level_backend(self):
        """manifest-level translation.wave2_backend takes priority."""
        manifest = {
            "project_slug": "test",
            "translation": {"wave2_backend": "hermes_delegate"},
            "chunks": [
                {"id": "chunk_001", "wave1_status": "completed", "wave2_backend": "minimax_api"},
            ],
        }
        result = _infer_repair_backend(manifest, ["chunk_001"])
        assert result == "hermes_delegate"

    def test_returns_first_flagged_chunk_backend(self):
        """Should find backend from any flagged chunk."""
        manifest = {
            "project_slug": "test",
            "chunks": [
                {"id": "chunk_001", "wave1_status": "completed"},
                {"id": "chunk_002", "wave1_status": "completed", "wave2_backend": "sequential"},
                {"id": "chunk_003", "wave1_status": "completed"},
            ],
        }
        result = _infer_repair_backend(manifest, ["chunk_001", "chunk_002"])
        assert result == "sequential"

    def test_returns_none_for_empty_manifest_chunks(self):
        """Should handle empty chunks list gracefully."""
        manifest = {"project_slug": "test", "chunks": []}
        result = _infer_repair_backend(manifest, ["chunk_001"])
        assert result is None


class TestRepairCommandSafety:
    """Tests for cmd_repair backend safety (exit behavior)."""

    PROJECT_TEMPLATE = {
        "project_slug": "test_repair_safety",
        "chunks": [
            {
                "id": "chunk_001",
                "word_count": 100,
                "wave1_status": "completed",
                "wave2_status": "completed",
            }
        ],
        "total_chunks": 1,
    }

    @pytest.fixture
    def temp_project(self):
        """Create a minimal project directory with manifest and remediation."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "translations" / "test_repair_safety"
            project_dir.mkdir(parents=True)

            # Write manifest.json
            (project_dir / "chunks").mkdir(parents=True)
            with open(project_dir / "chunks" / "manifest.json", "w") as f:
                json.dump(self.PROJECT_TEMPLATE, f, indent=2)

            # Write remediation.json
            (project_dir / "qa").mkdir()
            remediation = {
                "chunks": {"chunk_001": ["g4f"]},
                "gates": {"gate4_fluency": {"status": "WARN"}},
            }
            with open(project_dir / "qa" / "remediation.json", "w") as f:
                json.dump(remediation, f, indent=2)

            yield project_dir

    @pytest.fixture
    def temp_project_no_manifest(self):
        """Create a minimal project WITHOUT manifest.json to test missing manifest path."""
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "translations" / "test_no_manifest"
            project_dir.mkdir(parents=True)
            (project_dir / "qa").mkdir()
            remediation = {"chunks": {"chunk_001": ["g4f"]}, "gates": {}}
            with open(project_dir / "qa" / "remediation.json", "w") as f:
                json.dump(remediation, f, indent=2)
            yield project_dir

    def _call_repair(self, project_dir: Path, backend=None):
        """Call cmd_repair and return exit code or exception."""
        from run_pipeline import cmd_repair

        # Patch _project_dir to return our temp dir
        with patch("run_pipeline._project_dir", return_value=project_dir):
            try:
                cmd_repair(str(project_dir), backend=backend)
                return 0  # exited normally
            except SystemExit as e:
                return e.code

    def test_repair_no_backend_no_metadata_exits_error(self, temp_project):
        """repair without --backend and without metadata should exit(1)."""
        code = self._call_repair(temp_project, backend=None)
        assert code == 1

    def test_repair_explicit_mock_allowed(self, temp_project):
        """repair --backend mock should work (explicit override)."""
        code = self._call_repair(temp_project, backend="mock")
        # If it reaches ParallelTranslator it may fail because there's no
        # source chunk file — but it should NOT exit with code 1.
        # We just check it doesn't hit the safety check.
        # Since there's no real chunk source, the translate_wave will fail
        # with a file error, but that's expected.
        # The important thing: it should NOT sys.exit(1) from safety.
        assert code != 1, "Explicit --backend mock should not be rejected"

    def test_repair_no_backend_with_chunk_metadata_works(self, temp_project):
        """repair without --backend should infer from chunk metadata."""
        # Add backend metadata to manifest
        manifest_path = temp_project / "chunks" / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest["chunks"][0]["wave2_backend"] = "minimax_api"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        code = self._call_repair(temp_project, backend=None)
        # Should pass safety check (not exit 1), then fail on ParallelTranslator
        # because source chunks don't exist — that's expected.
        assert code != 1, "Inferred backend should pass safety check"
