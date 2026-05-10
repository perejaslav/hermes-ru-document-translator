"""TXT exporter — convert Markdown to plain text preserving code blocks."""
from pathlib import Path
import re


def export(md_content: str, output_path: Path) -> dict:
    """
    Convert Markdown to plain text and export.

    Fenced code blocks are converted to indented plain text blocks
    (with 4-space indentation) so code structure is preserved.

    Args:
        md_content: Markdown content string
        output_path: Target file path

    Returns:
        Result dict with status and info
    """
    text = md_content

    # ============================================================
    # Step 1: Handle fenced code blocks FIRST
    # Convert ```language ... ``` to indented plain text
    # ============================================================
    def fenced_to_indented(m):
        code = m.group(1)
        # Remove language tag from first line if present
        lines = code.split('\n')
        if lines and re.match(r'^[a-zA-Z0-9]+$', lines[0].strip()):
            lines = lines[1:]
        # Indent each line with 4 spaces
        indented = '\n'.join('    ' + ln for ln in lines if ln != '')
        return indented

    text = re.sub(r'```[^\n]*\n([\s\S]*?)```', fenced_to_indented, text)

    # ============================================================
    # Step 2: Remove other Markdown formatting
    # ============================================================
    # Headers (keep as text, remove #)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Bold/Italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Inline code (keep content, remove backticks)
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Links [text](url) -> text
    text = re.sub(r'\[(.+?)\]\([^)]+\)', r'\1', text)
    # Images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Blockquotes
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    # List markers: keep bullet character but normalize
    text = re.sub(r'^(\s*)([-*+])\s+', r'\1\2 ', text, flags=re.MULTILINE)
    text = re.sub(r'^(\s*)(\d+)\.\s+', r'\1\2. ', text, flags=re.MULTILINE)

    # Clean up extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text.strip())

    return {
        "format": "txt",
        "status": "success",
        "path": str(output_path),
        "size": len(text)
    }