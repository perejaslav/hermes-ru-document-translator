"""Markdown structure QA check."""
import re
from pathlib import Path


def check_markdown_structure(md_content: str) -> dict:
    """Check Markdown structure integrity."""
    issues = []

    lines = md_content.split('\n')
    in_code_block = False
    header_levels = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Header hierarchy check
        header_match = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if header_match:
            level = len(header_match.group(1))
            header_levels.append(level)

            # Check for jumps > 1 (H1 -> H4 is a jump)
            if len(header_levels) > 1:
                prev = header_levels[-2]
                if level > prev + 1:
                    issues.append({
                        "line": i,
                        "type": "header_jump",
                        "message": f"Header jump from H{prev} to H{level}"
                    })

        # Unclosed formatting
        bold_count = line.count('**') + line.count('__')
        if bold_count % 2 != 0:
            issues.append({
                "line": i,
                "type": "unclosed_bold",
                "message": "Unclosed bold/italic marker"
            })

        code_count = line.count('`')
        if code_count % 2 != 0 and '``' not in line:
            issues.append({
                "line": i,
                "type": "unclosed_code",
                "message": "Unclosed inline code marker"
            })

    # Check code blocks are closed
    if in_code_block:
        issues.append({
            "type": "unclosed_code_block",
            "message": "Code block not closed at end of document"
        })

    return {
        "status": "completed",
        "issues_count": len(issues),
        "issues": issues,
        "valid": len(issues) == 0
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        with open(Path(sys.argv[1]), 'r') as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    result = check_markdown_structure(content)
    print(result)