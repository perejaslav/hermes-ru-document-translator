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
        assert "retranslate without summarization" in all_notes
        assert "citations and structure" in all_notes

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
                    assert "retranslate" in note
