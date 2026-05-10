"""HTML exporter."""
from pathlib import Path
import re


def export(md_content: str, output_path: Path) -> dict:
    """
    Export Markdown content to HTML format.

    Args:
        md_content: Markdown content string
        output_path: Target file path

    Returns:
        Result dict with status and info
    """
    try:
        import markdown_it
    except ImportError:
        # Fallback to basic regex-based conversion
        html = basic_md_to_html(md_content)
    else:
        md = markdown_it.MarkdownIt()
        html = md.render(md_content)

    # Wrap in basic HTML template
    full_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Translated Document</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }}
        h1, h2, h3 {{ margin-top: 1.5em; }}
        code {{ background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1em; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #ddd; margin-left: 0; padding-left: 1em; color: #666; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    return {
        "format": "html",
        "status": "success",
        "path": str(output_path),
        "size": len(full_html)
    }


def basic_md_to_html(md: str) -> str:
    """Basic Markdown-to-HTML fallback conversion."""
    html = md

    # Headers
    html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)
    html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)

    # Code
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

    # Links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r'^[-*_]{3,}$', '<hr>', html, flags=re.MULTILINE)

    # Paragraphs (simple)
    paragraphs = []
    for para in html.split('\n\n'):
        para = para.strip()
        if para and not para.startswith('<') and not para.endswith('>'):
            if not re.match(r'^<(h[1-6]|ul|ol|li|blockquote|hr|code|pre)', para):
                para = f'<p>{para}</p>'
        paragraphs.append(para)

    return '\n'.join(paragraphs)