"""HTML extractor using BeautifulSoup4."""
from pathlib import Path
import re


def extract(html_path: Path) -> str:
    """
    Extract text content from HTML file and convert to Markdown.

    Args:
        html_path: Path to .html file

    Returns:
        Extracted content as Markdown string
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("beautifulsoup4 not installed. Run: uv pip install beautifulsoup4")

    with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    # Remove script and style elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()

    parts = []

    def process_element(elem):
        """Recursively process HTML elements to Markdown."""
        text_parts = []

        for child in elem.children:
            if hasattr(child, 'name') and child.name:
                name = child.name.lower()
                text = child.get_text(strip=True)

                if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                    level = int(name[1])
                    text_parts.append(f"\n{'#' * level} {text}\n")
                elif name == 'p':
                    text_parts.append(f"{text}\n")
                elif name == 'br':
                    text_parts.append('\n')
                elif name in ('ul', 'ol'):
                    for li in child.find_all('li', recursive=False):
                        marker = '-' if name == 'ul' else '1.'
                        text_parts.append(f"{marker} {li.get_text(strip=True)}\n")
                elif name == 'li':
                    pass  # handled by parent ul/ol
                elif name == 'blockquote':
                    lines = text.split('\n')
                    text_parts.append('> ' + '\n> '.join(lines) + '\n')
                elif name == 'code':
                    inline = child.string or ''
                    if '\n' in inline:
                        text_parts.append(f"\n```\n{inline}\n```\n")
                    else:
                        text_parts.append(f"`{inline}`")
                elif name == 'pre':
                    code = child.find('code')
                    if code:
                        text_parts.append(f"\n```\n{code.get_text()}\n```\n")
                    else:
                        text_parts.append(f"\n```\n{text}\n```\n")
                elif name == 'a':
                    href = child.get('href', '')
                    text = child.get_text(strip=True)
                    if href and text:
                        text_parts.append(f"[{text}]({href})")
                    else:
                        text_parts.append(text)
                elif name == 'strong' or name == 'b':
                    text_parts.append(f"**{text}**")
                elif name == 'em' or name == 'i':
                    text_parts.append(f"*{text}*")
                elif name == 'hr':
                    text_parts.append('\n---\n')
                elif name == 'table':
                    # Simple table handling
                    rows = child.find_all('tr')
                    if rows:
                        # Header row
                        header = rows[0]
                        headers = [th.get_text(strip=True) for th in header.find_all(['th', 'td'])]
                        text_parts.append('| ' + ' | '.join(headers) + ' |\n')
                        text_parts.append('| ' + ' | '.join(['---'] * len(headers)) + ' |\n')
                        # Data rows
                        for row in rows[1:]:
                            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                            text_parts.append('| ' + ' | '.join(cells) + ' |\n')
                else:
                    # Recursively process other elements
                    text_parts.append(process_element(child))
            else:
                # Text node
                text = str(child)
                if text.strip():
                    text_parts.append(text)

        return ''.join(text_parts)

    # Process body or main content
    body = soup.find('body') or soup.find('main') or soup
    result = process_element(body)

    # Clean up excessive whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()


def get_language(html_path: Path) -> str:
    """Detect language from HTML content."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return 'unknown'

    with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    text = soup.get_text()
    cyrillic = len(re.findall(r'[\u0400-\u04FF]', text))
    latin = len(re.findall(r'[a-zA-Z]', text))
    total = len(text)
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
    return {"status": "stub", "stage": "extract_html"}