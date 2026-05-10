"""Plain text extractor."""
import chardet
from pathlib import Path


def extract(text_path: Path) -> str:
    """
    Extract plain text from .txt file.

    Args:
        text_path: Path to .txt file

    Returns:
        Extracted text content as string
    """
    # Detect encoding
    with open(text_path, 'rb') as f:
        raw = f.read()
    result = chardet.detect(raw)
    encoding = result.get('encoding', 'utf-8')

    # Read with detected encoding
    try:
        content = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        # Fallback to UTF-8 with error handling
        content = raw.decode('utf-8', errors='replace')

    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    return content


def get_language(text: str) -> str:
    """Simple language detection based on character ranges."""
    # Basic heuristic: check for Cyrillic, CJK, Latin
    import re
    cyrillic = len(re.findall(r'[\u0400-\u04FF]', text))
    latin = len(re.findall(r'[a-zA-Z]', text))
    cjk = len(re.findall(r'[\u4E00-\u9FFF\u3040-\u30FF]', text))

    if cyrillic > len(text) * 0.3:
        return 'ru'
    elif cjk > len(text) * 0.2:
        return 'zh'
    elif latin > len(text) * 0.3:
        return 'en'
    return 'unknown'


# For compatibility with pipeline
def run(workspace: Path, **kwargs) -> dict:
    """Stub compatible with pipeline stage interface."""
    return {"status": "stub", "stage": "extract_txt"}