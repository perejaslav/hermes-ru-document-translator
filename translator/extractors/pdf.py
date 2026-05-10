"""PDF extractor using PyMuPDF (fitz)."""
from pathlib import Path
import re


def extract(pdf_path: Path) -> str:
    """
    Extract text content from text-based PDF.

    Args:
        pdf_path: Path to .pdf file

    Returns:
        Extracted text as string (Markdown-like structure preserved)
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF not installed. Run: uv pip install PyMuPDF")

    doc = fitz.open(str(pdf_path))
    parts = []
    prev_pos_y = 0
    line_threshold = 15  # pixels, threshold for new block detection

    for page_num, page in enumerate(doc):
        # Extract text with position information
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            block_texts = []
            for line in block["lines"]:
                line_text = ""
                for span in line["spans"]:
                    line_text += span["text"]
                block_texts.append(line_text)

            block_content = " ".join(block_texts)

            if not block_content.strip():
                continue

            # Determine if this is a heading based on font size/position
            is_heading = False
            if block["lines"] and block["lines"][0]["spans"]:
                font_size = block["lines"][0]["spans"][0].get("size", 12)
                if font_size >= 14:
                    is_heading = True

            if is_heading:
                parts.append(f"\n## {block_content.strip()}\n")
            else:
                parts.append(block_content.strip() + "\n")

    doc.close()

    result = "\n".join(parts)
    # Clean up
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


def extract_pages(pdf_path: Path) -> list[str]:
    """
    Extract PDF content page by page.

    Args:
        pdf_path: Path to .pdf file

    Returns:
        List of strings, one per page
    """
    try:
        import fitz
    except ImportError:
        raise ImportError("PyMuPDF not installed")

    doc = fitz.open(str(pdf_path))
    pages = []

    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())

    doc.close()
    return pages


def get_language(pdf_path: Path) -> str:
    """Detect language from PDF content."""
    content = extract(pdf_path)
    cyrillic = len(re.findall(r'[\u0400-\u04FF]', content))
    latin = len(re.findall(r'[a-zA-Z]', content))
    total = len(content)
    if total == 0:
        return 'unknown'
    if cyrillic / total > 0.3:
        return 'ru'
    elif latin / total > 0.5:
        return 'en'
    return 'unknown'


# For compatibility with pipeline
def run(workspace: Path, **kwargs) -> dict:
    """Stub compatible with pipeline stage interface."""
    return {"status": "stub", "stage": "extract_pdf"}