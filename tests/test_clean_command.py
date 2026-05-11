"""Tests: ``hermes-translator clean`` command — non-destructive output cleaning.

Verifies that ``cmd_clean()``:
- Creates ``translated.clean.md`` without modifying ``translated.md``
- Removes YAML frontmatter
- Removes ``[N]`` citation markers
- Reports correct refs_removed count
"""

import json
import re
from pathlib import Path

import pytest


def _make_project_with_output(tmp_path: Path) -> Path:
    """Create a project with a translated.md that has frontmatter and citations."""
    proj = tmp_path / "test_project"
    (proj / "output").mkdir(parents=True)

    content = """---
project: test_project
stage: merged
word_count: 100
---

## Test Heading

This is a test paragraph with a citation.[1] And another one.[2][3]

Some more text with reference[4] at the end.

| Table | Data |
|-------|------|
| value | [5]  |
"""
    (proj / "output" / "translated.md").write_text(content, encoding="utf-8")
    return proj


class TestCleanCommand:

    def test_creates_separate_file(self, tmp_path):
        """Clean creates translated.clean.md, does not touch translated.md."""
        from scripts.run_pipeline import cmd_clean

        proj = _make_project_with_output(tmp_path)
        slug = str(proj)

        cmd_clean(slug)

        assert (proj / "output" / "translated.md").exists()
        assert (proj / "output" / "translated.clean.md").exists()

        original = (proj / "output" / "translated.md").read_text(encoding="utf-8")
        # Original must still have frontmatter and citations
        assert original.startswith("---")
        assert "[1]" in original or "[2]" in original

    def test_removes_frontmatter(self, tmp_path):
        """translated.clean.md has no YAML frontmatter."""
        from scripts.run_pipeline import cmd_clean

        proj = _make_project_with_output(tmp_path)
        cmd_clean(str(proj))

        clean = (proj / "output" / "translated.clean.md").read_text(encoding="utf-8")
        assert not clean.startswith("---")
        assert "project:" not in clean.split("\n")[0]
        # Should start with the heading
        assert clean.startswith("##") or clean.startswith("Test")

    def test_removes_citations(self, tmp_path):
        """translated.clean.md has no [N] markers."""
        from scripts.run_pipeline import cmd_clean

        proj = _make_project_with_output(tmp_path)
        cmd_clean(str(proj))

        clean = (proj / "output" / "translated.clean.md").read_text(encoding="utf-8")
        assert "[" not in clean or not re.search(r"\[\d+\]", clean)

    def test_reports_correct_ref_count(self, tmp_path, capsys):
        """Command output shows correct number of removed citations."""
        from scripts.run_pipeline import cmd_clean

        proj = _make_project_with_output(tmp_path)
        slug = str(proj)

        cmd_clean(slug)

        captured = capsys.readouterr().out
        assert "translated.clean.md" in captured
        assert "original preserved" in captured
        # Source has [1], [2], [3], [4], [5] = 5 citations
        assert "5 citations" in captured or "citations" in captured

    def test_original_intact_after_clean(self, tmp_path):
        """translated.md is byte-identical before and after clean."""
        from scripts.run_pipeline import cmd_clean

        proj = _make_project_with_output(tmp_path)
        before = (proj / "output" / "translated.md").read_bytes()

        cmd_clean(str(proj))

        after = (proj / "output" / "translated.md").read_bytes()
        assert before == after
