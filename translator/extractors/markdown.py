"""Markdown extractor and normalizer."""
import re
from pathlib import Path


def extract(md_path: Path) -> str:
    """
    Extract content from Markdown file.

    Args:
        md_path: Path to .md or .markdown file

    Returns:
        Markdown content as string
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return content


def normalize(md_content: str) -> str:
    """
    Normalize Markdown structure.

    - Standardize header syntax (# to #)
    - Fix list syntax
    - Normalize code block markers
    - Remove excessive blank lines
    - Standardize links

    Args:
        md_content: Raw markdown content

    Returns:
        Normalized markdown
    """
    lines = md_content.split('\n')
    normalized = []
    prev_blank = False

    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()

        # Collapse multiple blank lines (keep max 2)
        if not line:
            if prev_blank:
                continue
            prev_blank = True
            normalized.append('')
        else:
            prev_blank = False

            # Standardize ATX headers (### -> ###)
            match = re.match(r'^(#{1,6})\s+(.*)', line)
            if match:
                hashes, text = match.groups()
                normalized.append(f"{hashes} {text}")
            else:
                normalized.append(line)

    # Remove leading/trailing blank lines
    while normalized and not normalized[0]:
        normalized.pop(0)
    while normalized and not normalized[-1]:
        normalized.pop()

    return '\n'.join(normalized)


def detect_language(md_content: str) -> str:
    """Detect document language from Markdown content."""
    # Check frontmatter
    if md_content.startswith('---'):
        end = md_content.find('---', 3)
        if end > 0:
            frontmatter = md_content[3:end]
            lang_match = re.search(r'^\s*lang(?:uage)?:\s*["\']?(\w+)', frontmatter, re.M)
            if lang_match:
                return lang_match.group(1)

    # Detect from content
    import re
    cyrillic = len(re.findall(r'[\u0400-\u04FF]', md_content))
    latin = len(re.findall(r'[a-zA-Z]', md_content))
    total_chars = len(md_content)

    if total_chars == 0:
        return 'unknown'

    if cyrillic / total_chars > 0.3:
        return 'ru'
    elif latin / total_chars > 0.5:
        return 'en'
    return 'unknown'


# For compatibility with pipeline
def run(workspace: Path, **kwargs) -> dict:
    """Stub compatible with pipeline stage interface."""
    return {"status": "stub", "stage": "extract_markdown"}