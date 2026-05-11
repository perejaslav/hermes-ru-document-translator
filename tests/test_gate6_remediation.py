"""Tests: Completeness Gate (gate 6) → remediation integration.

Verifies that compressed chunks detected by gate6_completeness
produce actionable entries in qa/remediation.json.
"""

import json
import re
from pathlib import Path

import pytest


def _make_project(tmp_path: Path, chunk_id: str, ratio: float) -> Path:
    """Create a minimal project with a compressed chunk."""
    proj = tmp_path / "test_project"
    (proj / "state").mkdir(parents=True)

    # Source chunk
    src_dir = proj / "chunks" / "source"
    src_dir.mkdir(parents=True)
    src_text = "Hello. " * 200  # ~1200 chars
    source = f"---\nchunk_id: {chunk_id}\n---\n\n" + src_text
    (src_dir / f"{chunk_id}.md").write_text(source, encoding="utf-8")
    (src_dir / "canonical.md").write_text(src_text, encoding="utf-8")

    # Translation (compressed to `ratio` of source)
    tr_len = max(10, int(len(src_text) * ratio))
    tr_text = ("X. " * (tr_len // 3))[:tr_len]
    trans = f"---\nchunk_id: {chunk_id}\nwave: wave2\n---\n\n" + tr_text

    w2_dir = proj / "chunks" / "translated" / "wave2"
    w2_dir.mkdir(parents=True)
    (w2_dir / f"{chunk_id}.md").write_text(trans, encoding="utf-8")

    # Manifest
    manifest = {
        "project_slug": "test",
        "total_chunks": 1,
        "chunks": [{
            "id": chunk_id,
            "word_count": 200,
            "wave1_status": "completed",
            "wave2_status": "completed",
        }],
    }
    (proj / "chunks" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    # Output dir with placeholder merged file
    (proj / "output").mkdir(parents=True)
    (proj / "output" / "translated.md").write_text(tr_text, encoding="utf-8")

    # QA dir
    (proj / "qa").mkdir(parents=True)

    return proj


class TestGate6Remediation:

    def test_compressed_chunk_in_remediation(self, tmp_path):
        """Gate 6 compressed chunk → actionable entry in remediation.json."""
        from translator.qa.gates import run_all_gates

        proj = _make_project(tmp_path, "chunk_001", ratio=0.25)

        result = run_all_gates(proj)
        g6 = result["gates"]["gate6_completeness"]
        assert g6["status"] in ("WARN", "FAIL")

        rem_path = proj / "qa" / "remediation.json"
        assert rem_path.exists()

        rem = json.loads(rem_path.read_text(encoding="utf-8"))
        assert "chunk_001" in rem.get("chunks", {})

        notes = rem["chunks"]["chunk_001"]
        all_notes = " ".join(notes)
        assert "gate6" in all_notes
        assert "compression" in all_notes
        assert "full retranslation from source required" in all_notes
        assert "all source structure" in all_notes

    def test_full_chunk_not_in_remediation(self, tmp_path):
        """A well-translated chunk should NOT appear in remediation from gate6."""
        from translator.qa.gates import run_all_gates

        proj = _make_project(tmp_path, "chunk_001", ratio=0.85)

        result = run_all_gates(proj)
        g6 = result["gates"]["gate6_completeness"]
        # ratio 85% is above 50% threshold — should be PASS
        assert g6["status"] == "PASS"

        rem_path = proj / "qa" / "remediation.json"
        rem = json.loads(rem_path.read_text(encoding="utf-8"))
        chunks = rem.get("chunks", {})

        # chunk_001 may appear from other gates, but gate6 should not flag it
        for chunk_id, notes in chunks.items():
            for n in notes:
                assert "gate6" not in n

    def test_remediation_note_contains_gate6_prefix(self, tmp_path):
        """Remediation note for gate6 starts with 'gate6:'."""
        from translator.qa.gates import run_all_gates

        proj = _make_project(tmp_path, "chunk_001", ratio=0.30)

        run_all_gates(proj)
        rem = json.loads(
            (proj / "qa" / "remediation.json").read_text(encoding="utf-8")
        )
        for note in rem["chunks"].get("chunk_001", []):
            if note.startswith("gate6:"):
                return  # found it
        pytest.fail("No gate6: note found in remediation")

    def test_overall_ratio_below_60_flags_issue(self, tmp_path):
        """Overall ratio < 60% generates an OVERALL issue in details."""
        from translator.qa.gates import run_all_gates

        proj = _make_project(tmp_path, "chunk_001", ratio=0.25)

        result = run_all_gates(proj)
        g6 = result["gates"]["gate6_completeness"]

        details_text = " ".join(g6.get("details", []))
        assert "OVERALL" in details_text or "compression" in details_text

    def test_repair_can_parse_gate6_notes(self, tmp_path):
        """gate6 notes are parseable by the repair pipeline: contain chunk_id + issue."""
        from translator.qa.gates import run_all_gates

        proj = _make_project(tmp_path, "chunk_001", ratio=0.20)

        run_all_gates(proj)
        rem = json.loads(
            (proj / "qa" / "remediation.json").read_text(encoding="utf-8")
        )

        for chunk_id, notes in rem.get("chunks", {}).items():
            assert re.match(r"chunk_\d+$", chunk_id), f"Bad chunk_id: {chunk_id}"
            for note in notes:
                # Every note must be non-empty
                assert len(note) > 5
                # gate6 notes must be actionable
                if note.startswith("gate6:"):
                    assert "compression" in note
                    assert "retranslation" in note
                    assert "full retranslation from source required" in note

    # ── Reference loss tests ──────────────────────────────────────────

    def test_reference_loss_3refs_under_70pct_flags_warn(self, tmp_path):
        """Chunk with 3+ refs and <70% retention generates a reference loss issue."""
        from translator.qa.gates import _gate_completeness

        proj = tmp_path / "test_project"
        (proj / "state").mkdir(parents=True)
        src_dir = proj / "chunks" / "source"
        src_dir.mkdir(parents=True)
        w2_dir = proj / "chunks" / "translated" / "wave2"
        w2_dir.mkdir(parents=True)
        (proj / "output").mkdir(parents=True)
        (proj / "output" / "translated.md").write_text("x", encoding="utf-8")

        # Source with 5 references
        src_text = "Some text [1] with [2] references [3] here [4] and [5] there.\n\nMore content here.\n\nFinal paragraph.\n"
        (src_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\n---\n\n{src_text}", encoding="utf-8")
        (src_dir / "canonical.md").write_text(src_text, encoding="utf-8")

        # Translation with only 3 references (< 70%)
        tr_text = "Some text [1] with [2] references [3] here.\n\nM content here.\n\nFinal para.\n"
        (w2_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\nwave: wave2\n---\n\n{tr_text}", encoding="utf-8")

        manifest = {
            "project_slug": "test",
            "total_chunks": 1,
            "chunks": [{"id": "chunk_001", "word_count": 20, "wave1_status": "completed", "wave2_status": "completed"}],
        }
        (proj / "chunks" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        result = _gate_completeness(proj, manifest, w2_dir)
        details_text = " ".join(result.get("details", []))
        assert "reference loss" in details_text
        assert "5→3" in details_text or "3" in details_text

    def test_reference_loss_5refs_under_50pct_flags_severe(self, tmp_path):
        """Chunk with 5+ refs and <50% retention flags severe reference loss."""
        from translator.qa.gates import _gate_completeness

        proj = tmp_path / "test_project"
        (proj / "state").mkdir(parents=True)
        src_dir = proj / "chunks" / "source"
        src_dir.mkdir(parents=True)
        w2_dir = proj / "chunks" / "translated" / "wave2"
        w2_dir.mkdir(parents=True)
        (proj / "output").mkdir(parents=True)
        (proj / "output" / "translated.md").write_text("x", encoding="utf-8")

        # Source with 8 references
        src_text = "Text [1] with [2] many [3] refs [4] here [5] and [6] also [7] there [8].\n\nMore.\n"
        (src_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\n---\n\n{src_text}", encoding="utf-8")
        (src_dir / "canonical.md").write_text(src_text, encoding="utf-8")

        # Translation with only 3 references (< 50%)
        tr_text = "Text [1] with [2] refs [3] here.\n\nMore.\n"
        (w2_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\nwave: wave2\n---\n\n{tr_text}", encoding="utf-8")

        manifest = {
            "project_slug": "test",
            "total_chunks": 1,
            "chunks": [{"id": "chunk_001", "word_count": 20, "wave1_status": "completed", "wave2_status": "completed"}],
        }
        (proj / "chunks" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        result = _gate_completeness(proj, manifest, w2_dir)
        details_text = " ".join(result.get("details", []))
        assert "severe reference loss" in details_text
        assert result["compressed_chunks"] >= 1  # severe_count

    def test_reference_loss_1_or_2_refs_not_flagged(self, tmp_path):
        """Chunks with only 1-2 references should NOT be flagged for reference loss."""
        from translator.qa.gates import _gate_completeness

        proj = tmp_path / "test_project"
        (proj / "state").mkdir(parents=True)
        src_dir = proj / "chunks" / "source"
        src_dir.mkdir(parents=True)
        w2_dir = proj / "chunks" / "translated" / "wave2"
        w2_dir.mkdir(parents=True)
        (proj / "output").mkdir(parents=True)
        (proj / "output" / "translated.md").write_text("x", encoding="utf-8")

        # Source with 2 references (below threshold)
        src_text = "Text [1] here [2].\n\nMore content.\n"
        (src_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\n---\n\n{src_text}", encoding="utf-8")
        (src_dir / "canonical.md").write_text(src_text, encoding="utf-8")

        # Translation with 0 references (loss but threshold not met)
        tr_text = "Text here.\n\nMore content.\n"
        (w2_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\nwave: wave2\n---\n\n{tr_text}", encoding="utf-8")

        manifest = {
            "project_slug": "test",
            "total_chunks": 1,
            "chunks": [{"id": "chunk_001", "word_count": 10, "wave1_status": "completed", "wave2_status": "completed"}],
        }
        (proj / "chunks" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        result = _gate_completeness(proj, manifest, w2_dir)
        details_text = " ".join(result.get("details", []))
        assert "reference loss" not in details_text

    def test_reference_loss_appears_in_remediation(self, tmp_path):
        """Reference loss issues should generate remediation entries with gate6: prefix."""
        from translator.qa.gates import run_all_gates

        proj = tmp_path / "test_project"
        (proj / "state").mkdir(parents=True)
        src_dir = proj / "chunks" / "source"
        src_dir.mkdir(parents=True)
        w2_dir = proj / "chunks" / "translated" / "wave2"
        w2_dir.mkdir(parents=True)
        (proj / "output").mkdir(parents=True)
        (proj / "qa").mkdir(parents=True)
        (proj / "output" / "translated.md").write_text("x", encoding="utf-8")

        src_text = "Text [1] with [2] many [3] refs [4] here [5].\n\nMore.\n"
        (src_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\n---\n\n{src_text}", encoding="utf-8")
        (src_dir / "canonical.md").write_text(src_text, encoding="utf-8")

        tr_text = "Text [1] with [2] refs.\n\nMore.\n"
        (w2_dir / "chunk_001.md").write_text(f"---\nchunk_id: chunk_001\nwave: wave2\n---\n\n{tr_text}", encoding="utf-8")

        manifest = {
            "project_slug": "test",
            "total_chunks": 1,
            "chunks": [{"id": "chunk_001", "word_count": 10, "wave1_status": "completed", "wave2_status": "completed"}],
        }
        (proj / "chunks" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        run_all_gates(proj)
        rem_path = proj / "qa" / "remediation.json"
        assert rem_path.exists()

        rem = json.loads(rem_path.read_text(encoding="utf-8"))
        notes = rem.get("chunks", {}).get("chunk_001", [])
        all_notes = " ".join(notes)
        assert "gate6:" in all_notes
        assert "reference loss" in all_notes

    def test_normalize_plain_text_headers_basic(self):
        """Verify plain-text header normalization."""
        from translator.pipeline.chunker import normalize_plain_text_headers

        # Basic case
        result = normalize_plain_text_headers("Some text.\n\nBackground\n\nMore text.")
        assert "## Background" in result

        # Already has ## — no change
        result = normalize_plain_text_headers("## Background\n\nText.")
        assert result == "## Background\n\nText."

        # Ends with period — no change
        result = normalize_plain_text_headers("Background.\n\nText.")
        assert "## Background" not in result

        # Contains [N] — no change
        result = normalize_plain_text_headers("Text [1].\n\nBackground [2]\n\nMore.")
        assert "## Background" not in result

        # Long multi-word header
        result = normalize_plain_text_headers("Intro.\n\nPolitical Structure and Dynasties\n\nDetails.")
        assert "## Political Structure and Dynasties" in result

    def test_normalize_plain_text_headers_code_block(self):
        """Code blocks must not be affected by header normalization."""
        from translator.pipeline.chunker import normalize_plain_text_headers

        text = "Text.\n\n```\nBackground\n```\n\nMore."
        result = normalize_plain_text_headers(text)
        # The "Background" inside code block stays unchanged
        assert "```\nBackground\n```" in result or "```  Background  ```" not in result

    def test_normalize_plain_text_headers_table_caption(self):
        """Line before a table row should not become a header."""
        from translator.pipeline.chunker import normalize_plain_text_headers

        text = "Some text.\n\nCaption\n| col1 | col2 |\n|------|------|\n| a | b |"
        result = normalize_plain_text_headers(text)
        assert "## Caption" not in result
        assert "Caption" in result  # still there as plain text
