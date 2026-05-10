"""Language check QA — verify target contains Russian/Cyrillic."""
import re
from pathlib import Path


def check_language(md_content: str, min_cyrillic_ratio: float = 0.1) -> dict:
    """Check that content contains Cyrillic characters (Russian translation)."""
    total_chars = len(md_content.replace(' ', '').replace('\n', ''))
    if total_chars == 0:
        return {
            "status": "failed",
            "message": "Empty content"
        }

    cyrillic_count = len(re.findall(r'[\u0400-\u04FF]', md_content))
    latin_count = len(re.findall(r'[a-zA-Z]', md_content))

    cyrillic_ratio = cyrillic_count / total_chars if total_chars > 0 else 0

    return {
        "status": "completed",
        "total_chars": total_chars,
        "cyrillic_count": cyrillic_count,
        "cyrillic_ratio": round(cyrillic_ratio, 4),
        "latin_count": latin_count,
        "contains_russian": cyrillic_ratio >= min_cyrillic_ratio,
        "message": f"Cyrillic ratio: {cyrillic_ratio:.2%} (min: {min_cyrillic_ratio:.0%})"
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        with open(Path(sys.argv[1]), 'r') as f:
            content = f.read()
    else:
        content = sys.stdin.read()

    result = check_language(content)
    print(result)