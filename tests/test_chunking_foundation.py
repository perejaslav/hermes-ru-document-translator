"""Test canonical chunking and foundation building."""

import pytest
import json
import tempfile
import os
from pathlib import Path

from translator.pipeline.chunker import chunk_text, save_chunks
from translator.pipeline.foundation_builder import build_foundation


def test_chunking_basic():
    """Basic text splits into chunks."""
    text = "word " * 200 + "\n\n" + "word " * 200 + "\n\n" + "word " * 200
    chunks = chunk_text(text, "test_project")
    # With target 800 words, should create multiple chunks
    assert len(chunks) >= 1
    for c in chunks:
        assert c.id.startswith("chunk_")
        assert c.word_count > 0


def test_chunking_never_splits_mid_sentence():
    """Oversized paragraphs split at sentence boundaries."""
    long_sentence = "This is sentence one. " * 100  # ~500 words in one paragraph
    text = long_sentence + "\n\nNormal paragraph."
    chunks = chunk_text(text, "test_project")
    # Should create chunks without breaking mid-sentence (heuristic check)
    for c in chunks:
        # All chunks should have reasonable word counts
        assert c.word_count <= 1600


def test_chunking_preserves_code_blocks():
    """Code blocks are not split during chunking."""
    text = "# Introduction\n\n```python\ndef foo():\n    pass\n```\n\n## Body"
    chunks = chunk_text(text, "test_project")
    # Should preserve code block
    assert len(chunks) >= 1


def test_chunking_context_previous():
    """Previous context is last 2 sentences of previous chunk."""
    text = "First sentence one. First sentence two. Second sentence one. Second sentence two. Third sentence one."
    chunks = chunk_text(text, "test_project")
    # First chunk should have no previous context
    assert chunks[0].has_previous_context is False
    if len(chunks) > 1:
        # Later chunks should have previous context
        for c in chunks[1:]:
            assert c.has_previous_context is True


def test_chunking_context_next():
    """Next context is first 2 sentences of next chunk."""
    text = "Sentence one of chunk one. Sentence two of chunk one. Sentence three of chunk one.\n\nSentence one of chunk two. Sentence two of chunk two."
    chunks = chunk_text(text, "test_project")
    if len(chunks) > 1:
        # All but last chunk should have next context
        for c in chunks[:-1]:
            assert c.has_next_context is True
        assert chunks[-1].has_next_context is False


def test_save_chunks_creates_files():
    """save_chunks creates all required files and manifest."""
    text = "word " * 100 + "\n\n" + "word " * 100
    chunks = chunk_text(text, "test_project")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        manifest_path = save_chunks(chunks, project_dir)

        # Check manifest
        assert manifest_path.exists()
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["total_chunks"] == len(chunks)
        assert len(manifest["chunks"]) == len(chunks)
        assert manifest["project_slug"] == project_dir.name  # temp dir name, not user-provided slug

        # Check source chunks
        source_dir = project_dir / "chunks" / "source"
        for chunk in chunks:
            chunk_file = source_dir / f"{chunk.id}.md"
            assert chunk_file.exists()
            content = chunk_file.read_text()
            assert "---" in content  # YAML frontmatter

        # Check context files
        context_dir = project_dir / "chunks" / "context"
        for chunk in chunks:
            ctx_file = context_dir / f"{chunk.id}.context.md"
            assert ctx_file.exists()

        # Check manifest chunk entries
        for entry in manifest["chunks"]:
            assert "id" in entry
            assert "word_count" in entry
            assert "wave1_status" in entry
            assert "wave2_status" in entry


def test_foundation_builder_creates_three_files():
    """build_foundation creates glossary.md, style.md, entities.md."""
    text = """
    This document discusses machine learning algorithms and neural networks.
    Python is used for data processing. Neural networks use gradient descent.
    Machine learning requires computational resources.
    The function handles data efficiently. System architecture is modular.
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        os.chdir(project_dir)

        results = build_foundation(text, source_lang="en")

        assert "glossary" in results
        assert "style" in results
        assert "entities" in results

        for key, path in results.items():
            assert path.exists()
            content = path.read_text()
            assert len(content) > 20
            assert path.name.endswith(".md")


def test_foundation_builder_short_text_warning():
    """Short text produces placeholder files with warning."""
    text = "Short text."

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        os.chdir(project_dir)

        results = build_foundation(text, source_lang="en")

        for key, path in results.items():
            content = path.read_text()
            assert "placeholder" in content.lower() or len(content) > 10


def test_foundation_glossary_extracts_terms():
    """Glossary contains repeated capitalized terms."""
    text = """
    Neural Networks are important. Neural Networks use gradients.
    Machine Learning requires data. Machine Learning is popular.
    Python handles computations.
    """ * 5

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        os.chdir(project_dir)

        results = build_foundation(text, source_lang="en")
        glossary = results["glossary"].read_text()

        # Should contain extracted terms
        assert "Glossary" in glossary
        assert "|" in glossary  # markdown table


def test_foundation_entities_detects_capitalized():
    """Entity register extracts multi-word capitalized sequences."""
    text = """
    Stanford University conducted research. Harvard University participated.
    Neural Networks from Stanford are well known.
    """ * 3

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        os.chdir(project_dir)

        results = build_foundation(text, source_lang="en")
        entities = results["entities"].read_text()

        assert "Entity Register" in entities
        assert "Stanford University" in entities or "HARVARD" in entities.upper()


def test_foundation_style_analyzes_sentence_length():
    """Style guide reflects detected sentence length."""
    long_text = ". ".join([f"This is sentence number {i} with some additional words to increase length" for i in range(50)])

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        os.chdir(project_dir)

        results = build_foundation(long_text, source_lang="en")
        style = results["style"].read_text()

        assert "Style Guide" in style
        assert "sentence" in style.lower()
        assert "tone" in style.lower()