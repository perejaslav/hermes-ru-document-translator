"""Tests stub for extraction."""
import pytest
from pathlib import Path


def test_txt_extractor_basic():
    """Test basic text extraction."""
    from translator.extractors.txt import extract
    # Will add when we have test fixtures
    pass


def test_markdown_extractor_basic():
    """Test basic markdown extraction."""
    from translator.extractors.markdown import extract, normalize
    pass


def test_docx_extractor_basic():
    """Test basic docx extraction."""
    from translator.extractors.docx import extract
    pass


def test_html_extractor_basic():
    """Test basic html extraction."""
    from translator.extractors.html import extract
    pass


def test_pdf_extractor_basic():
    """Test basic pdf extraction."""
    from translator.extractors.pdf import extract
    pass